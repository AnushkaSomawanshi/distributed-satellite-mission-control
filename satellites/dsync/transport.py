"""
Satellite-to-satellite message transport for all FA-2 algorithms.

Every tracked message is stamped with the sender's Lamport clock, vector clock and physical clock,
and both ends record an event (SEND / RECV). Faults are enforced HERE, on the satellites:
- partition: a satellite refuses to send to, or accept from, satellites outside its group;
- crash (silent mode): the satellite neither sends nor accepts anything.

Two delivery styles:
- send(): one-way message; the receiver's handler result is ignored.
- request(): the receiver's handler returns a reply payload, which travels back as a stamped
  REPLY message (its own SEND/RECV events), in the HTTP response.
"""

import itertools
import logging
import time
from typing import Any, Awaitable, Callable, Dict, Iterable, List, Optional

from .clocks import LamportClock, PhysicalClock, VectorClock
from .events import EventReporter

logger = logging.getLogger("dsync.transport")

Handler = Callable[[Dict[str, Any]], Awaitable[Optional[Dict[str, Any]]]]

# Peer liveness thresholds (seconds without a beacon)
SUSPECT_AFTER = 3.0   # > 1 missed beacon (beacons every 2 s)
DEAD_AFTER = 5.0      # > 2 missed beacons


class PeerUnreachable(Exception):
    pass


class PeerDirectory:
    """Who the other satellites are, where to reach them, and whether they look alive (from beacons)."""

    def __init__(self, self_id: str, clock: Callable[[], float] = time.monotonic,
                 suspect_after: float = SUSPECT_AFTER, dead_after: float = DEAD_AFTER):
        self.self_id = self_id
        self.entries: Dict[str, Dict[str, Any]] = {}
        self._clock = clock
        self.suspect_after = suspect_after
        self.dead_after = dead_after

    def upsert(self, peer_id: str, address: Optional[str] = None, p2p_port: Optional[int] = None, **fields: Any) -> Dict[str, Any]:
        if peer_id == self.self_id:
            return {}
        entry = self.entries.setdefault(peer_id, {
            "address": address, "p2p_port": p2p_port, "status": "UNKNOWN",
            "state": "UNKNOWN", "last_beacon": None,
        })
        if address:
            entry["address"] = address
        if p2p_port:
            entry["p2p_port"] = int(p2p_port)
        entry.update(fields)
        return entry

    def merge_registry(self, satellites: Iterable[Dict[str, Any]]) -> None:
        for sat in satellites:
            sid = sat.get("satellite_id")
            if sid and sid != self.self_id and sat.get("address") and sat.get("p2p_port"):
                self.upsert(sid, sat["address"], sat["p2p_port"], status=sat.get("status", "UNKNOWN"))

    def get(self, peer_id: str) -> Optional[Dict[str, Any]]:
        return self.entries.get(peer_id)

    def mark_beacon(self, peer_id: str, **fields: Any) -> str:
        """Record a beacon; returns the previous liveness state."""
        entry = self.upsert(peer_id, fields.pop("address", None), fields.pop("p2p_port", None), **fields)
        previous = entry.get("state", "UNKNOWN")
        entry["last_beacon"] = self._clock()
        entry["state"] = "ALIVE"
        return previous

    def silence(self, peer_id: str) -> Optional[float]:
        entry = self.entries.get(peer_id)
        if not entry or entry.get("last_beacon") is None:
            return None
        return self._clock() - entry["last_beacon"]

    def evaluate(self) -> List[Dict[str, Any]]:
        """Move peers to SUSPECTED / DEAD when their beacons stop. Returns the transitions."""
        transitions = []
        for pid, entry in self.entries.items():
            silence = self.silence(pid)
            if silence is None:
                continue
            old = entry.get("state", "UNKNOWN")
            new = "DEAD" if silence > self.dead_after else "SUSPECTED" if silence > self.suspect_after else "ALIVE"
            if new != old:
                entry["state"] = new
                transitions.append({"peer": pid, "from": old, "to": new, "silence_s": round(silence, 3)})
        return transitions

    def live_ids(self) -> List[str]:
        """Peers that are not (yet) declared dead and have been heard at least once."""
        return sorted(pid for pid, e in self.entries.items() if e.get("state") in ("ALIVE", "SUSPECTED"))

    def known_ids(self) -> List[str]:
        return sorted(self.entries)

    def snapshot(self) -> Dict[str, Dict[str, Any]]:
        out = {}
        for pid, e in self.entries.items():
            item = {k: v for k, v in e.items() if k != "last_beacon"}
            silence = self.silence(pid)
            item["silence_s"] = None if silence is None else round(silence, 2)
            out[pid] = item
        return out


class HttpNetwork:
    """Real network: HTTP POST to the peer's P2P port."""

    def __init__(self):
        self._client = None

    async def post(self, address: str, port: int, path: str, body: Dict[str, Any], timeout: float) -> Dict[str, Any]:
        import httpx
        if self._client is None:
            self._client = httpx.AsyncClient()
        resp = await self._client.post(f"http://{address}:{port}{path}", json=body, timeout=timeout)
        resp.raise_for_status()
        return resp.json()


class Transport:
    def __init__(self, node_id: str, directory: PeerDirectory, network: Any, reporter: EventReporter,
                 physical: PhysicalClock, all_nodes: Iterable[str] = ()):
        self.node_id = node_id
        self.directory = directory
        self.network = network
        self.reporter = reporter
        self.physical = physical
        self.lamport = LamportClock()
        self.vector = VectorClock(node_id, all_nodes)
        self.handlers: Dict[str, Handler] = {}
        self.blocked: set = set()     # satellites on the other side of a partition
        self.silent = False           # simulated crash
        self._ids = itertools.count(1)
        self.sent: Dict[str, int] = {}
        self.received: Dict[str, int] = {}
        self.failed: Dict[str, int] = {}

    # ---------------------------------------------------------------- helpers
    def on(self, msg_type: str, handler: Handler) -> None:
        self.handlers[msg_type] = handler

    def _bump(self, table: Dict[str, int], key: str) -> None:
        table[key] = table.get(key, 0) + 1

    def _event(self, kind: str, **fields: Any) -> Dict[str, Any]:
        event = {
            "kind": kind,
            "lamport": self.lamport.value,
            "vector": self.vector.to_dict(),
            "phys_ts": self.physical.now(),
            "true_ts": time.time(),
        }
        event.update({k: v for k, v in fields.items() if v is not None})
        return self.reporter.record(event)

    def local_event(self, label: str, algo: Optional[str] = None, run_id: Optional[str] = None,
                    detail: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """An internal event (decision, critical-section entry, ...): ticks both logical clocks."""
        self.lamport.increment()
        self.vector.increment()
        return self._event("LOCAL", label=label, algo=algo, run_id=run_id, detail=detail)

    def _new_envelope(self, dest: str, msg_type: str, payload: Optional[Dict[str, Any]], algo: Optional[str],
                      run_id: Optional[str], expects_reply: bool, tracked: bool) -> Dict[str, Any]:
        env = {
            "msg_id": f"{self.node_id}-m{next(self._ids)}",
            "msg_type": msg_type,
            "src": self.node_id,
            "dst": dest,
            "payload": payload or {},
            "algo": algo,
            "run_id": run_id,
            "expects_reply": expects_reply,
            "tracked": tracked,
        }
        if tracked:
            env["lamport"] = self.lamport.increment()
            env["vector"] = self.vector.increment()
            env["phys_ts"] = self.physical.now()
        return env

    def _absorb(self, env: Dict[str, Any]) -> None:
        """Receive rule for logical clocks + RECV event."""
        self._bump(self.received, env["msg_type"])
        if not env.get("tracked"):
            return
        self.lamport.update(env.get("lamport", 0))
        self.vector.merge(env.get("vector", {}))
        self.vector.increment()
        self._event("RECV", msg_id=env["msg_id"], msg_type=env["msg_type"], peer=env["src"],
                    algo=env.get("algo"), run_id=env.get("run_id"),
                    send_lamport=env.get("lamport"), send_phys_ts=env.get("phys_ts"))

    # ---------------------------------------------------------------- sending
    async def send(self, dest: str, msg_type: str, payload: Optional[Dict[str, Any]] = None, *,
                   algo: Optional[str] = None, run_id: Optional[str] = None, expect_reply: bool = False,
                   timeout: float = 2.0, tracked: bool = True) -> Optional[Dict[str, Any]]:
        if self.silent:
            raise PeerUnreachable(f"{self.node_id} is silent (simulated crash)")
        peer = self.directory.get(dest)
        if not peer or not peer.get("address") or not peer.get("p2p_port"):
            raise PeerUnreachable(f"no address known for {dest}")

        env = self._new_envelope(dest, msg_type, payload, algo, run_id, expect_reply, tracked)
        send_fields = dict(msg_id=env["msg_id"], msg_type=msg_type, peer=dest, algo=algo, run_id=run_id)
        stamp = {"lamport": env.get("lamport"), "vector": env.get("vector"), "phys_ts": env.get("phys_ts"), "true_ts": time.time()}

        def record_send(delivered: bool, reason: Optional[str] = None) -> None:
            if not tracked:
                return
            event = {"kind": "SEND", "delivered": delivered, "reason": reason, **send_fields, **stamp}
            self.reporter.record({k: v for k, v in event.items() if v is not None})

        if dest in self.blocked:
            self._bump(self.failed, msg_type)
            record_send(False, "partitioned")
            raise PeerUnreachable(f"{dest} is on the other side of a network partition")
        try:
            resp = await self.network.post(peer["address"], peer["p2p_port"], "/dsync/msg", env, timeout)
        except Exception as exc:
            self._bump(self.failed, msg_type)
            record_send(False, exc.__class__.__name__)
            raise PeerUnreachable(f"{dest} unreachable: {exc.__class__.__name__}") from exc
        if not resp.get("ok"):
            self._bump(self.failed, msg_type)
            record_send(False, resp.get("reason", "rejected"))
            raise PeerUnreachable(f"{dest} rejected the message: {resp.get('reason')}")

        self._bump(self.sent, msg_type)
        record_send(True)
        reply = resp.get("reply")
        if reply:
            self._absorb(reply)
            return reply.get("payload") or {}
        return None

    async def request(self, dest: str, msg_type: str, payload: Optional[Dict[str, Any]] = None, **kw: Any) -> Optional[Dict[str, Any]]:
        return await self.send(dest, msg_type, payload, expect_reply=True, **kw)

    # ---------------------------------------------------------------- receiving
    async def receive(self, env: Dict[str, Any]) -> Dict[str, Any]:
        if self.silent:
            return {"ok": False, "reason": "silent"}
        if env.get("src") in self.blocked:
            return {"ok": False, "reason": "partitioned"}
        self._absorb(env)
        handler = self.handlers.get(env["msg_type"])
        if handler is None:
            return {"ok": True, "unhandled": True}
        result = await handler(env)
        if env.get("expects_reply") and result is not None:
            reply_type = result.pop("_reply_type", f"{env['msg_type']}_REPLY")
            reply = self._new_envelope(env["src"], reply_type, result, env.get("algo"), env.get("run_id"),
                                       False, bool(env.get("tracked")))
            self._bump(self.sent, reply_type)
            if reply.get("tracked"):
                self._event("SEND", msg_id=reply["msg_id"], msg_type=reply_type, peer=env["src"],
                            algo=env.get("algo"), run_id=env.get("run_id"), delivered=True)
            return {"ok": True, "reply": reply}
        return {"ok": True}

    def stats(self) -> Dict[str, Any]:
        return {"sent": dict(self.sent), "received": dict(self.received), "failed": dict(self.failed)}
