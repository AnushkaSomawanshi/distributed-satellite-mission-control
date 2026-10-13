"""
Distributed mutual exclusion on the satellites (Unit 3). Shared resource: the ground-station downlink
(only one satellite may downlink at a time). Four algorithms over the same transport, so the
Algorithm Arena can compare them on equal terms.

centralised          the elected leader keeps a FIFO queue: REQUEST -> GRANT -> RELEASE (3 msgs/entry,
                     0 when the requester is the leader).
ricart_agrawala      REQUEST(ts) to all; a site replies at once unless it holds the CS or its own
                     pending request has a smaller (Lamport, ID); deferred replies are sent on exit.
                     2(N-1) messages per entry.
token_ring           a single TOKEN circulates the ring of live satellites; only the holder may enter.
                     Messages per entry depend on load (idle circulation is counted).
lodha_kshemkalyani   fair algorithm with Local Request Queues (LRQ). REQUEST(ts) to all; an idle site
                     REPLYs, a requesting site only queues the request (a REQUEST itself serves as the
                     answer). A site enters when it has heard (REPLY, REQUEST or FLUSH) from every
                     participant since its own request AND no earlier request remains in its LRQ.
                     On exit it sends FLUSH(ts) to the concurrent requesters in its LRQ instead of
                     REPLYing to them. Between N-1 and 2(N-1) messages per entry; entries are served
                     in timestamp order. (Implementation note: FLUSH goes to every concurrent requester
                     in the LRQ, which keeps the entry condition simple and safe.)

Every request, entry and exit is a stamped local event (CS_REQUEST / CS_ENTER / CS_EXIT), so
Mission Control can verify safety (no overlapping CS intervals) and fairness from the event log.
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Set, Tuple

from .transport import PeerUnreachable

logger = logging.getLogger("dsync.mutex")

ALGORITHMS = ("centralised", "ricart_agrawala", "token_ring", "lodha_kshemkalyani")
TS = Tuple[int, str]


class MutexError(Exception):
    pass


class MutexService:
    def __init__(self, node: Any, acquire_timeout: float = 20.0, token_hop_delay: float = 0.03):
        self.node = node
        self.acquire_timeout = acquire_timeout
        self.token_hop_delay = token_hop_delay
        self.busy = False
        self.in_cs = False
        self.current_algo: Optional[str] = None
        self.entries = 0
        # centralised (state used when this satellite is the coordinator)
        self.c_holder: Optional[str] = None
        self.c_queue: List[Tuple[str, Optional[str]]] = []
        self.c_granted: Optional[asyncio.Event] = None
        # Ricart-Agrawala
        self.ra_state = "RELEASED"
        self.ra_ts: Optional[TS] = None
        self.ra_pending: Set[str] = set()
        self.ra_deferred: List[Tuple[str, Optional[str]]] = []
        self.ra_done: Optional[asyncio.Event] = None
        # token ring
        self.tk_have = False
        self.tk_token: Optional[Dict[str, Any]] = None
        self.tk_wants = False
        self.tk_stop = True
        self.tk_ready: Optional[asyncio.Event] = None
        self.tk_passing = False
        # Lodha-Kshemkalyani
        self.lk_requesting = False
        self.lk_ts: Optional[TS] = None
        self.lk_lrq: Dict[str, TS] = {}
        self.lk_heard: Set[str] = set()
        self.lk_participants: Set[str] = set()
        self.lk_ready: Optional[asyncio.Event] = None

        t = node.transport
        for msg, fn in {
            "MUTEX_REQUEST": self._c_on_request, "MUTEX_GRANT": self._c_on_grant, "MUTEX_RELEASE": self._c_on_release,
            "RA_REQUEST": self._ra_on_request, "RA_REPLY": self._ra_on_reply,
            "TOKEN": self._tk_on_token,
            "LK_REQUEST": self._lk_on_request, "LK_REPLY": self._lk_on_reply, "LK_FLUSH": self._lk_on_flush,
        }.items():
            t.on(msg, fn)

    # ================================================================= common
    def to_dict(self) -> Dict[str, Any]:
        return {
            "busy": self.busy, "in_cs": self.in_cs, "algorithm": self.current_algo, "entries": self.entries,
            "centralised": {"holder": self.c_holder, "queue": [s for s, _ in self.c_queue]},
            "ricart_agrawala": {"state": self.ra_state, "ts": self.ra_ts, "pending": sorted(self.ra_pending),
                                "deferred": [s for s, _ in self.ra_deferred]},
            "token_ring": {"have_token": self.tk_have, "wants": self.tk_wants, "stopped": self.tk_stop,
                           "ring": (self.tk_token or {}).get("ring")},
            "lodha_kshemkalyani": {"requesting": self.lk_requesting, "ts": self.lk_ts,
                                   "lrq": {k: list(v) for k, v in self.lk_lrq.items()},
                                   "heard": sorted(self.lk_heard), "participants": sorted(self.lk_participants)},
        }

    def _event(self, label: str, algo: str, run_id: Optional[str], **detail: Any) -> Dict[str, Any]:
        return self.node.transport.local_event(label, algo=algo, run_id=run_id, detail=detail or None)

    async def _send(self, dest: str, msg: str, payload: Dict[str, Any], algo: str, run_id: Optional[str]) -> bool:
        try:
            await self.node.transport.send(dest, msg, payload, algo=algo, run_id=run_id)
            return True
        except PeerUnreachable:
            return False

    async def _wait(self, event: asyncio.Event, algo: str) -> None:
        try:
            await asyncio.wait_for(event.wait(), self.acquire_timeout)
        except asyncio.TimeoutError as exc:
            raise MutexError(f"{algo}: no permission after {self.acquire_timeout:.0f}s") from exc

    async def acquire(self, algo: str, run_id: Optional[str] = None) -> Dict[str, Any]:
        if algo not in ALGORITHMS:
            raise MutexError(f"unknown algorithm {algo}")
        if self.busy:
            raise MutexError("this satellite already has an outstanding request")
        if self.node.transport.silent:
            raise MutexError("satellite is silent")
        self.busy, self.current_algo = True, algo
        req = self._event("CS_REQUEST", algo, run_id, resource="downlink")
        my_ts: TS = (req["lamport"], self.node.node_id)
        started = time.time()
        try:
            await getattr(self, f"_acquire_{algo}")(my_ts, run_id)
        except Exception:
            self.busy, self.current_algo = False, None
            self._reset_after_failure(algo)
            self._event("CS_ABORTED", algo, run_id, request_lamport=my_ts[0])
            raise
        self.in_cs = True
        self.entries += 1
        wait_ms = round((time.time() - started) * 1000, 3)
        self._event("CS_ENTER", algo, run_id, request_lamport=my_ts[0], wait_ms=wait_ms, resource="downlink")
        return {"request_lamport": my_ts[0], "wait_ms": wait_ms}

    async def release(self, run_id: Optional[str] = None) -> None:
        algo = self.current_algo
        if not self.in_cs or algo is None:
            raise MutexError("not in the critical section")
        self._event("CS_EXIT", algo, run_id, resource="downlink")
        self.in_cs = False
        try:
            await getattr(self, f"_release_{algo}")(run_id)
        finally:
            self.busy, self.current_algo = False, None

    def _reset_after_failure(self, algo: str) -> None:
        if algo == "ricart_agrawala":
            self.ra_state, self.ra_pending = "RELEASED", set()
            for dest, rid in self.ra_deferred:
                asyncio.create_task(self._send(dest, "RA_REPLY", {}, "ricart_agrawala", rid))
            self.ra_deferred = []
        elif algo == "lodha_kshemkalyani":
            self.lk_requesting = False
            self.lk_lrq.clear()
            self.lk_heard.clear()
        elif algo == "token_ring":
            self.tk_wants = False

    async def run_rounds(self, algo: str, run_id: str, rounds: int, hold_ms: float,
                         start_at: Optional[float] = None, gap_ms: float = 20.0) -> List[Dict[str, Any]]:
        if start_at:
            await asyncio.sleep(max(0.0, start_at - time.time()))
        results = []
        for r in range(1, rounds + 1):
            try:
                info = await self.acquire(algo, run_id)
            except MutexError as exc:
                results.append({"round": r, "error": str(exc)})
                break
            await asyncio.sleep(hold_ms / 1000.0)
            await self.release(run_id)
            results.append({"round": r, **info})
            await asyncio.sleep(gap_ms / 1000.0)
        return results

    async def on_peer_dead(self, peer: str) -> None:
        if peer in self.ra_pending:
            self.ra_pending.discard(peer)
            if not self.ra_pending and self.ra_done:
                self.ra_done.set()
        if peer in self.lk_participants:
            self.lk_participants.discard(peer)
            self.lk_lrq.pop(peer, None)
            self._lk_check()

    # ================================================================= centralised
    async def _acquire_centralised(self, my_ts: TS, run_id: Optional[str]) -> None:
        leader = self.node.election.leader
        if not leader or not self.node.election.leader_alive():
            raise MutexError("centralised mutex needs a live leader (run an election first)")
        self.c_granted = asyncio.Event()
        if leader == self.node.node_id:
            self._c_enqueue(self.node.node_id, run_id)
        elif not await self._send(leader, "MUTEX_REQUEST", {"ts": my_ts[0]}, "centralised", run_id):
            raise MutexError(f"coordinator {leader} unreachable")
        await self._wait(self.c_granted, "centralised")

    async def _release_centralised(self, run_id: Optional[str]) -> None:
        leader = self.node.election.leader
        if leader == self.node.node_id:
            self._c_release(self.node.node_id)
        elif leader:
            await self._send(leader, "MUTEX_RELEASE", {}, "centralised", run_id)

    def _c_grant(self, dest: str, run_id: Optional[str]) -> None:
        if dest == self.node.node_id:
            if self.c_granted:
                self.c_granted.set()
        else:
            asyncio.create_task(self._send(dest, "MUTEX_GRANT", {}, "centralised", run_id))

    def _c_enqueue(self, src: str, run_id: Optional[str]) -> None:
        if self.c_holder is None:
            self.c_holder = src
            self._c_grant(src, run_id)
        else:
            self.c_queue.append((src, run_id))

    def _c_release(self, src: str) -> None:
        if self.c_holder != src:
            return
        self.c_holder = None
        if self.c_queue:
            nxt, rid = self.c_queue.pop(0)
            self.c_holder = nxt
            self._c_grant(nxt, rid)

    async def _c_on_request(self, env: Dict[str, Any]) -> None:
        self._c_enqueue(env["src"], env.get("run_id"))

    async def _c_on_grant(self, env: Dict[str, Any]) -> None:
        if self.c_granted:
            self.c_granted.set()

    async def _c_on_release(self, env: Dict[str, Any]) -> None:
        self._c_release(env["src"])

    # ================================================================= Ricart-Agrawala
    async def _acquire_ricart_agrawala(self, my_ts: TS, run_id: Optional[str]) -> None:
        self.ra_state, self.ra_ts = "WANTED", my_ts
        participants = self.node.directory.live_ids()
        self.ra_pending = set(participants)
        self.ra_done = asyncio.Event()
        if not self.ra_pending:
            self.ra_done.set()

        async def ask(peer: str) -> None:
            if not await self._send(peer, "RA_REQUEST", {"ts": my_ts[0]}, "ricart_agrawala", run_id):
                self.ra_pending.discard(peer)  # unreachable peer cannot answer; treat as failed
                if not self.ra_pending:
                    self.ra_done.set()
        await asyncio.gather(*(ask(p) for p in participants))
        await self._wait(self.ra_done, "ricart_agrawala")
        self.ra_state = "HELD"

    async def _release_ricart_agrawala(self, run_id: Optional[str]) -> None:
        self.ra_state, self.ra_ts = "RELEASED", None
        deferred, self.ra_deferred = self.ra_deferred, []
        await asyncio.gather(*(self._send(d, "RA_REPLY", {}, "ricart_agrawala", rid) for d, rid in deferred))

    async def _ra_on_request(self, env: Dict[str, Any]) -> None:
        theirs: TS = (int(env["payload"]["ts"]), env["src"])
        if self.ra_state == "HELD" or (self.ra_state == "WANTED" and self.ra_ts < theirs):
            self.ra_deferred.append((env["src"], env.get("run_id")))
        else:
            asyncio.create_task(self._send(env["src"], "RA_REPLY", {}, "ricart_agrawala", env.get("run_id")))

    async def _ra_on_reply(self, env: Dict[str, Any]) -> None:
        self.ra_pending.discard(env["src"])
        if not self.ra_pending and self.ra_done:
            self.ra_done.set()

    # ================================================================= token ring
    def token_control(self, action: str, run_id: Optional[str] = None, ring: Optional[List[str]] = None,
                      create: bool = False) -> Dict[str, Any]:
        if action == "start":
            self.tk_stop = False
            if create and not self.tk_have:
                self.tk_have = True
                self.tk_token = {"ring": ring, "run_id": run_id, "hops": 0}
                self._event("TOKEN_CREATED", "token_ring", run_id, ring=ring)
            if self.tk_have:
                self.tk_token = {**(self.tk_token or {}), "ring": ring or (self.tk_token or {}).get("ring"), "run_id": run_id}
                asyncio.create_task(self._tk_after_receive())
        elif action == "stop":
            self.tk_stop = True
        return {"have_token": self.tk_have, "stopped": self.tk_stop}

    async def _tk_after_receive(self) -> None:
        if self.tk_wants and self.tk_ready:
            self.tk_ready.set()
        else:
            await self._tk_pass()

    async def _tk_pass(self) -> None:
        # Only one hand-off may be in flight per satellite; a second one would duplicate the token.
        if not self.tk_have or self.tk_passing:
            return
        if self.tk_stop:
            self._event("TOKEN_PARKED", "token_ring", (self.tk_token or {}).get("run_id"))
            return
        self.tk_passing = True
        try:
            await self._tk_pass_once()
        finally:
            self.tk_passing = False

    async def _tk_pass_once(self) -> None:
        await asyncio.sleep(self.token_hop_delay)
        if not self.tk_have or self.in_cs:
            return
        if self.tk_wants and self.tk_ready:
            self.tk_ready.set()
            return
        if self.tk_stop:
            self._event("TOKEN_PARKED", "token_ring", (self.tk_token or {}).get("run_id"))
            return
        token = dict(self.tk_token or {})
        ring = token.get("ring") or sorted(set(self.node.directory.live_ids()) | {self.node.node_id})
        me = self.node.node_id
        i = ring.index(me) if me in ring else -1
        for nxt in ring[i + 1:] + ring[:max(i, 0)]:
            if nxt == me:
                continue
            token["hops"] = int(token.get("hops", 0)) + 1
            self.tk_have = False
            if await self._send(nxt, "TOKEN", token, "token_ring", token.get("run_id")):
                return
            self.tk_have = True
        # nobody reachable: keep the token and try again shortly
        asyncio.get_running_loop().call_later(0.5, lambda: asyncio.ensure_future(self._tk_pass()))

    async def _tk_on_token(self, env: Dict[str, Any]) -> None:
        self.tk_have = True
        self.tk_token = dict(env.get("payload") or {})
        asyncio.create_task(self._tk_after_receive())

    async def _acquire_token_ring(self, my_ts: TS, run_id: Optional[str]) -> None:
        if self.tk_stop and not self.tk_have:
            raise MutexError("token ring is not running (start a token-ring run first)")
        self.tk_ready = asyncio.Event()
        self.tk_wants = True
        if self.tk_have:
            self.tk_ready.set()
        await self._wait(self.tk_ready, "token_ring")

    async def _release_token_ring(self, run_id: Optional[str]) -> None:
        self.tk_wants = False
        asyncio.create_task(self._tk_pass())

    # ================================================================= Lodha-Kshemkalyani
    def _lk_check(self) -> None:
        if not self.lk_requesting or self.lk_ready is None or self.in_cs:
            return
        heard_all = self.lk_participants <= self.lk_heard
        earlier = [s for s, ts in self.lk_lrq.items() if ts < self.lk_ts]
        if heard_all and not earlier:
            self.lk_ready.set()

    async def _acquire_lodha_kshemkalyani(self, my_ts: TS, run_id: Optional[str]) -> None:
        self.lk_ts = my_ts
        self.lk_lrq, self.lk_heard = {}, set()
        self.lk_participants = set(self.node.directory.live_ids())
        self.lk_ready = asyncio.Event()
        self.lk_requesting = True

        async def ask(peer: str) -> None:
            if not await self._send(peer, "LK_REQUEST", {"ts": my_ts[0]}, "lodha_kshemkalyani", run_id):
                self.lk_participants.discard(peer)
                self._lk_check()
        await asyncio.gather(*(ask(p) for p in sorted(self.lk_participants)))
        self._lk_check()
        await self._wait(self.lk_ready, "lodha_kshemkalyani")

    async def _release_lodha_kshemkalyani(self, run_id: Optional[str]) -> None:
        my_ts = self.lk_ts
        later = sorted(self.lk_lrq)
        self.lk_requesting = False
        self.lk_lrq, self.lk_heard = {}, set()
        await asyncio.gather(*(self._send(s, "LK_FLUSH", {"ts": my_ts[0]}, "lodha_kshemkalyani", run_id) for s in later))

    async def _lk_on_request(self, env: Dict[str, Any]) -> None:
        src = env["src"]
        if self.lk_requesting:
            self.lk_lrq[src] = (int(env["payload"]["ts"]), src)
            self.lk_heard.add(src)
            self._lk_check()
        else:
            asyncio.create_task(self._send(src, "LK_REPLY", {}, "lodha_kshemkalyani", env.get("run_id")))

    async def _lk_on_reply(self, env: Dict[str, Any]) -> None:
        if self.lk_requesting:
            self.lk_heard.add(env["src"])
            self._lk_check()

    async def _lk_on_flush(self, env: Dict[str, Any]) -> None:
        src = env["src"]
        if not self.lk_requesting:
            return
        self.lk_heard.add(src)
        flushed: TS = (int(env["payload"]["ts"]), src)
        if src in self.lk_lrq and self.lk_lrq[src] <= flushed:
            del self.lk_lrq[src]
        self._lk_check()
