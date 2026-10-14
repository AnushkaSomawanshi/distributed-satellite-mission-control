"""
Distributed deadlock detection: Chandy-Misra-Haas edge-chasing (AND model).

Resources: every satellite owns one relay transponder. To relay data through a neighbour, a
satellite keeps its own transponder and also needs the neighbour's. Requests that cannot be granted
are queued at the owner, and the requester WAITS FOR the current holder (a wait-for-graph edge).

Detection (Knapp's classification: edge-chasing):
  a satellite blocked for longer than PROBE_AFTER sends PROBE(initiator, path) to the satellite it
  waits for. A blocked receiver forwards the probe along its own wait-for edge (once per initiator);
  an unblocked receiver drops it. If a probe returns to its initiator, the path is a cycle: deadlock.

Resolution: the victim is the cycle member with the youngest request (largest Lamport timestamp,
ID breaks ties). It cancels its pending request and releases what it holds, so the others proceed.
Every initiator picks the same victim; aborting twice is harmless.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple

from .transport import PeerUnreachable

logger = logging.getLogger("dsync.deadlock")

PROBE_AFTER = 1.0


class DeadlockService:
    def __init__(self, node: Any, probe_after: float = PROBE_AFTER, wait_timeout: float = 15.0):
        self.node = node
        self.probe_after = probe_after
        self.wait_timeout = wait_timeout
        # my transponder (I am its owner / resource manager)
        self.holder: Optional[str] = None
        self.queue: List[Tuple[str, int, Optional[str]]] = []
        # my outstanding request
        self.wanted: Optional[str] = None
        self.waiting_for: Optional[str] = None
        self.req_ts: Optional[int] = None
        self.run_id: Optional[str] = None
        self.held_remote: set = set()
        self.granted: Optional[asyncio.Event] = None
        self.aborted = False
        self.forwarded: set = set()
        self.detections: List[Dict[str, Any]] = []
        t = node.transport
        for msg, fn in {"RELAY_REQUEST": self._on_request, "RELAY_GRANT": self._on_grant,
                        "RELAY_RELEASE": self._on_release, "RELAY_CANCEL": self._on_cancel,
                        "CMH_PROBE": self._on_probe, "CMH_ABORT": self._on_abort}.items():
            t.on(msg, fn)

    def to_dict(self) -> Dict[str, Any]:
        return {"transponder_holder": self.holder, "queue": [q[0] for q in self.queue],
                "wants": self.wanted, "waiting_for": self.waiting_for, "request_lamport": self.req_ts,
                "holds_remote": sorted(self.held_remote), "recent_detections": self.detections[-5:]}

    def _ev(self, label: str, **detail: Any) -> Dict[str, Any]:
        return self.node.transport.local_event(label, algo="deadlock", run_id=self.run_id, detail=detail or None)

    async def _send(self, dest: str, msg: str, payload: Dict[str, Any]) -> bool:
        try:
            await self.node.transport.send(dest, msg, payload, algo="deadlock", run_id=self.run_id)
            return True
        except PeerUnreachable:
            return False

    # ---------------------------------------------------------------- resource manager (my transponder)
    def _grant_local_or_remote(self, who: str) -> None:
        self.holder = who
        if who == self.node.node_id:
            if self.granted:
                self.granted.set()
        else:
            asyncio.ensure_future(self._send(who, "RELAY_GRANT", {"owner": self.node.node_id}))

    def _release_mine(self, by: str) -> None:
        if self.holder != by:
            return
        self.holder = None
        if self.queue:
            nxt, _, _ = self.queue.pop(0)
            self._grant_local_or_remote(nxt)

    async def _on_request(self, env: Dict[str, Any]) -> Dict[str, Any]:
        src = env["src"]
        if self.holder is None:
            self.holder = src
            return {"granted": True, "_reply_type": "RELAY_REPLY"}
        self.queue.append((src, int(env["payload"]["ts"]), env.get("run_id")))
        return {"granted": False, "holder": self.holder, "_reply_type": "RELAY_REPLY"}

    async def _on_release(self, env: Dict[str, Any]) -> None:
        self._release_mine(env["src"])

    async def _on_cancel(self, env: Dict[str, Any]) -> None:
        self.queue = [q for q in self.queue if q[0] != env["src"]]

    async def _on_grant(self, env: Dict[str, Any]) -> None:
        owner = env["payload"]["owner"]
        if self.wanted == owner and not self.aborted:
            self.held_remote.add(owner)
            if self.granted:
                self.granted.set()
        else:  # granted after we gave up: hand it straight back
            asyncio.ensure_future(self._send(owner, "RELAY_RELEASE", {}))

    # ---------------------------------------------------------------- requesting
    async def _request(self, owner: str) -> bool:
        me = self.node.node_id
        req = self._ev("RELAY_REQUESTED", owner=owner)
        self.wanted, self.req_ts, self.aborted = owner, req["lamport"], False
        self.granted = asyncio.Event()
        if owner == me:
            if self.holder is None:
                self.holder = me
                return True
            self.queue.append((me, self.req_ts, self.run_id))
            blocker = self.holder
        else:
            try:
                reply = await self.node.transport.request(owner, "RELAY_REQUEST", {"ts": self.req_ts},
                                                          algo="deadlock", run_id=self.run_id)
            except PeerUnreachable:
                return False
            if reply.get("granted"):
                self.held_remote.add(owner)
                return True
            blocker = reply.get("holder")
        self.waiting_for = blocker
        self._ev("WAIT_FOR", waits_for=blocker, resource=f"{owner} transponder", request_lamport=self.req_ts)
        probe = asyncio.ensure_future(self._probe_later())
        try:
            await asyncio.wait_for(self.granted.wait(), self.wait_timeout)
        except asyncio.TimeoutError:
            self._ev("WAIT_TIMEOUT", owner=owner)
            await self._abort("timeout")
        finally:
            probe.cancel()
            self.waiting_for = None
        return not self.aborted and (owner in self.held_remote or self.holder == me)

    async def _probe_later(self) -> None:
        await asyncio.sleep(self.probe_after)
        if self.waiting_for and not self.aborted:
            path = [[self.node.node_id, self.req_ts]]
            self._ev("PROBE_INITIATED", to=self.waiting_for)
            asyncio.ensure_future(self._send(self.waiting_for, "CMH_PROBE", {"initiator": self.node.node_id, "path": path}))

    async def _on_probe(self, env: Dict[str, Any]) -> None:
        p = env["payload"]
        initiator, path = p["initiator"], p["path"]
        me = self.node.node_id
        if initiator == me:
            if self.waiting_for and not self.aborted:
                await self._detected(path)
            return None
        if self.waiting_for and not self.aborted and (initiator, self.req_ts) not in self.forwarded:
            self.forwarded.add((initiator, self.req_ts))
            self._ev("PROBE_FORWARDED", initiator=initiator, to=self.waiting_for)
            asyncio.ensure_future(self._send(self.waiting_for, "CMH_PROBE",
                                             {"initiator": initiator, "path": path + [[me, self.req_ts]]}))
        elif not self.waiting_for:
            self._ev("PROBE_DROPPED", initiator=initiator, reason="not blocked: no deadlock through here")
        return None

    async def _detected(self, path: List[List[Any]]) -> None:
        cycle = [n for n, _ in path]
        victim, victim_ts = max(path, key=lambda x: (x[1], x[0]))
        record = {"cycle": cycle, "victim": victim, "victim_request_lamport": victim_ts, "detected_by": self.node.node_id}
        self.detections.append(record)
        self._ev("DEADLOCK_DETECTED", **record)
        if victim == self.node.node_id:
            await self._abort("deadlock victim")
        else:
            asyncio.ensure_future(self._send(victim, "CMH_ABORT", {"cycle": cycle}))

    async def _on_abort(self, env: Dict[str, Any]) -> None:
        if self.waiting_for and not self.aborted:
            await self._abort("deadlock victim")
        return None

    async def _abort(self, reason: str) -> None:
        if self.aborted:
            return
        self.aborted = True
        owner = self.wanted
        if owner and owner != self.node.node_id and owner not in self.held_remote:
            await self._send(owner, "RELAY_CANCEL", {})
        self._ev("REQUEST_ABORTED", reason=reason, released_own_transponder=self.holder == self.node.node_id)
        await self.release_all()
        if self.granted:
            self.granted.set()

    async def release_all(self) -> None:
        for owner in sorted(self.held_remote):
            await self._send(owner, "RELAY_RELEASE", {})
        self.held_remote.clear()
        self.wanted = None
        self._release_mine(self.node.node_id)

    # ---------------------------------------------------------------- scenario
    async def run_scenario(self, target: Optional[str], hold_ms: float, run_id: str, settle: float = 0.4) -> Dict[str, Any]:
        """Keep my own transponder, then (optionally) ask for target's transponder, use both, release."""
        self.run_id, self.forwarded = run_id, set()
        if not await self._request(self.node.node_id):
            return {"node": self.node.node_id, "status": "COULD_NOT_GET_OWN_TRANSPONDER"}
        self._ev("RELAY_ACQUIRED", owner=self.node.node_id)
        await asyncio.sleep(settle)                      # everyone holds their own first
        status = "COMPLETED"
        if target:
            ok = await self._request(target)
            if not ok:
                return {"node": self.node.node_id, "target": target,
                        "status": "ABORTED_AS_VICTIM" if self.aborted else "FAILED"}
            self._ev("RELAY_PATH_ESTABLISHED", via=target)
        await asyncio.sleep(hold_ms / 1000.0)
        await self.release_all()
        self._ev("RELAY_DONE")
        return {"node": self.node.node_id, "target": target, "status": status}
