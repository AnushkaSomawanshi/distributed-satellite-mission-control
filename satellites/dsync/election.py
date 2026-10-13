"""
Leader election on the satellites (Unit 3). One implementation, two algorithms, one leader + term.

Priority = (health bucket, satellite ID): health is rounded down to tens so small telemetry
wobbles do not reorder satellites, and a low-battery / overheating satellite never wins against a
healthy one. The ID breaks ties, so priorities are unique.

Bully (Garcia-Molina):
  1. P sends ELECTION(priority) to every live satellite it believes has a higher priority.
  2. A higher satellite answers OK and starts its own election.
  3. If nobody answers OK within the timeout, P becomes leader and broadcasts COORDINATOR(term).
  4. If someone answered but no COORDINATOR arrives in time, P starts again.

Ring (Chang-Roberts style, over the ring of live satellites sorted by ID):
  1. The initiator sends RING_ELECTION with a candidate list to its successor; dead successors are
     skipped. Each satellite adds (ID, priority) and forwards.
  2. When the token returns to the initiator, the highest priority wins; a RING_COORDINATOR token
     carries (leader, term) once around the ring.

The leader is the constellation coordinator: Berkeley time daemon and centralised-mutex coordinator.
A satellite whose beacons show the leader DEAD starts an election by itself (no Mission Control).
"""

import asyncio
import itertools
import logging
from typing import Any, Callable, Dict, List, Optional

from .transport import PeerUnreachable

logger = logging.getLogger("dsync.election")


def _key(priority: Any) -> tuple:
    return tuple(priority) if priority is not None else (-1, "")


class ElectionService:
    ALGORITHMS = ("bully", "ring")

    def __init__(self, node: Any, default_algorithm: str = "bully",
                 ok_timeout: float = 1.0, coordinator_timeout: float = 4.0, ring_timeout: float = 8.0):
        self.node = node
        self.default_algorithm = default_algorithm
        self.ok_timeout = ok_timeout
        self.coordinator_timeout = coordinator_timeout
        self.ring_timeout = ring_timeout
        self.leader: Optional[str] = None
        self.term = 0
        self.running = False
        self.running_algorithm: Optional[str] = None
        self._coordinator_seen: Optional[asyncio.Event] = None
        self._auto_ids = itertools.count(1)
        self.listeners: List[Callable[[Optional[str], int], None]] = []
        t = node.transport
        t.on("ELECTION", self._on_election)
        t.on("COORDINATOR", self._on_coordinator)
        t.on("RING_ELECTION", self._on_ring_election)
        t.on("RING_COORDINATOR", self._on_ring_coordinator)

    # ------------------------------------------------------------------ state
    def priority(self) -> List[Any]:
        health = float(self.node.info().get("health", 0.0))
        return [int(health // 10), self.node.node_id]

    def leader_alive(self) -> bool:
        if self.leader is None:
            return False
        if self.leader == self.node.node_id:
            return True
        entry = self.node.directory.get(self.leader)
        return bool(entry and entry.get("state") in ("ALIVE", "SUSPECTED"))

    def to_dict(self) -> Dict[str, Any]:
        return {"leader": self.leader, "term": self.term, "running": self.running,
                "running_algorithm": self.running_algorithm, "default_algorithm": self.default_algorithm,
                "priority": self.priority()}

    def _accept(self, leader: str, term: int, run_id: Optional[str], algo: str, source: str) -> bool:
        if term < self.term:
            self.node.transport.local_event("STALE_LEADER_IGNORED", algo=algo, run_id=run_id,
                                            detail={"leader": leader, "term": term, "current_term": self.term})
            return False
        if term == self.term and self.leader and leader != self.leader and leader < self.leader:
            return False  # same term, two claims: the higher ID wins deterministically
        changed = (leader, term) != (self.leader, self.term)
        self.leader, self.term = leader, term
        if changed:
            label = "LEADER_ELECTED" if leader == self.node.node_id else "LEADER_ACCEPTED"
            self.node.transport.local_event(label, algo=algo, run_id=run_id,
                                            detail={"leader": leader, "term": term, "via": source})
            logger.info("[%s ELECTION] leader=%s term=%s (%s, %s)", self.node.node_id, leader, term, algo, source)
            for cb in self.listeners:
                try:
                    cb(leader, term)
                except Exception:  # pragma: no cover
                    pass
        if self._coordinator_seen is not None:
            self._coordinator_seen.set()
        return True

    # ------------------------------------------------------------------ triggers
    def auto_run_id(self) -> str:
        return f"auto-{self.node.node_id}-{next(self._auto_ids)}"

    async def start(self, algorithm: Optional[str] = None, run_id: Optional[str] = None, reason: str = "MANUAL") -> None:
        algorithm = (algorithm or self.default_algorithm).lower()
        if algorithm not in self.ALGORITHMS:
            raise ValueError(f"unknown election algorithm {algorithm}")
        if self.node.transport.silent:
            return
        run_id = run_id or self.auto_run_id()
        if algorithm == "bully":
            await self._bully(run_id, reason)
        else:
            await self._ring_start(run_id, reason)

    async def on_peer_dead(self, peer: str) -> None:
        if peer == self.leader:
            self.node.transport.local_event("LEADER_LOST", algo=self.default_algorithm, detail={"leader": peer, "term": self.term})
            self.leader = None
            await self.start(self.default_algorithm, reason="LEADER_DEAD")

    async def ensure_leader(self) -> None:
        """Start an election if no live leader is known (used at start-up and after partitions heal)."""
        if not self.running and not self.leader_alive() and not self.node.transport.silent:
            await self.start(self.default_algorithm, reason="NO_LEADER")

    async def observe_beacon(self, src: str, payload: Dict[str, Any]) -> None:
        term, leader = payload.get("term") or 0, payload.get("leader")
        if leader and term > self.term:
            self._accept(leader, term, None, self.default_algorithm, f"beacon from {src}")

    # ------------------------------------------------------------------ bully
    async def _ask(self, peer: str, mine: List[Any], run_id: str) -> bool:
        try:
            reply = await self.node.transport.request(peer, "ELECTION", {"priority": mine}, algo="bully",
                                                      run_id=run_id, timeout=self.ok_timeout)
            return bool(reply and reply.get("ok"))
        except PeerUnreachable:
            return False

    async def _bully(self, run_id: str, reason: str, attempt: int = 1) -> None:
        if self.running:
            return
        self.running, self.running_algorithm = True, "bully"
        restart = False
        try:
            mine = self.priority()
            self.node.transport.local_event("ELECTION_START", algo="bully", run_id=run_id,
                                            detail={"reason": reason, "priority": mine, "attempt": attempt})
            higher = [pid for pid in self.node.directory.live_ids()
                      if _key(self.node.directory.get(pid).get("priority")) > _key(mine)
                      or self.node.directory.get(pid).get("priority") is None]
            self._coordinator_seen = asyncio.Event()
            answers = await asyncio.gather(*(self._ask(pid, mine, run_id) for pid in higher))
            if not any(answers):
                await self._become_leader("bully", run_id)
                return
            self.node.transport.local_event("ELECTION_WAIT", algo="bully", run_id=run_id,
                                            detail={"higher_answered": [p for p, a in zip(higher, answers) if a]})
            try:
                await asyncio.wait_for(self._coordinator_seen.wait(), self.coordinator_timeout)
            except asyncio.TimeoutError:
                restart = attempt < 3
        finally:
            self.running, self.running_algorithm = False, None
        if restart:
            await self._bully(run_id, "NO_COORDINATOR", attempt + 1)

    async def _become_leader(self, algo: str, run_id: str) -> None:
        known = [int(e.get("term") or 0) for e in self.node.directory.entries.values()]
        term = max([self.term] + known) + 1
        self._accept(self.node.node_id, term, run_id, algo, "won election")

        async def announce(pid: str) -> None:
            try:
                await self.node.transport.send(pid, "COORDINATOR", {"leader": self.node.node_id, "term": term},
                                               algo=algo, run_id=run_id)
            except PeerUnreachable:
                pass
        await asyncio.gather(*(announce(p) for p in self.node.directory.live_ids()))

    async def _on_election(self, env: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        sender = env.get("payload", {}).get("priority")
        if _key(self.priority()) > _key(sender):
            if not self.running:
                asyncio.create_task(self._bully(env.get("run_id") or self.auto_run_id(), f"BULLIED_BY_{env['src']}"))
            return {"ok": True, "_reply_type": "OK"}
        return None  # lower priority: stay silent, as in the classic algorithm

    async def _on_coordinator(self, env: Dict[str, Any]) -> None:
        p = env.get("payload", {})
        self._accept(p["leader"], int(p["term"]), env.get("run_id"), env.get("algo") or "bully", f"COORDINATOR from {env['src']}")
        return None

    # ------------------------------------------------------------------ ring
    def ring_order(self) -> List[str]:
        return sorted(set(self.node.directory.live_ids()) | {self.node.node_id})

    def _successors(self) -> List[str]:
        order = self.ring_order()
        i = order.index(self.node.node_id)
        return order[i + 1:] + order[:i]

    async def _ring_forward(self, msg_type: str, token: Dict[str, Any], run_id: str) -> Optional[str]:
        for nxt in self._successors():
            try:
                await self.node.transport.send(nxt, msg_type, token, algo="ring", run_id=run_id)
                return nxt
            except PeerUnreachable:
                self.node.transport.local_event("RING_SKIP", algo="ring", run_id=run_id, detail={"skipped": nxt})
        return None

    async def _ring_start(self, run_id: str, reason: str) -> None:
        if self.running:
            return
        self.running, self.running_algorithm = True, "ring"
        me = self.node.node_id
        self.node.transport.local_event("ELECTION_START", algo="ring", run_id=run_id,
                                        detail={"reason": reason, "priority": self.priority(), "ring": self.ring_order()})
        token = {"initiator": me, "candidates": {me: self.priority()}, "max_term": self.term}
        if await self._ring_forward("RING_ELECTION", token, run_id) is None:
            await self._ring_finish(token, run_id)
        asyncio.create_task(self._ring_watchdog(run_id))

    async def _ring_watchdog(self, run_id: str) -> None:
        await asyncio.sleep(self.ring_timeout)
        if self.running and self.running_algorithm == "ring":
            self.running, self.running_algorithm = False, None
            self.node.transport.local_event("RING_TIMEOUT", algo="ring", run_id=run_id)

    async def _ring_finish(self, token: Dict[str, Any], run_id: str) -> None:
        winner = max(token["candidates"].items(), key=lambda kv: _key(kv[1]))[0]
        term = max(int(token.get("max_term") or 0), self.term) + 1
        self._accept(winner, term, run_id, "ring", "ring election result")
        coord = {"initiator": self.node.node_id, "leader": winner, "term": term}
        if await self._ring_forward("RING_COORDINATOR", coord, run_id) is None:
            self.running, self.running_algorithm = False, None

    async def _on_ring_election(self, env: Dict[str, Any]) -> None:
        token, run_id, me = dict(env.get("payload", {})), env.get("run_id"), self.node.node_id
        if token.get("initiator") == me:
            asyncio.create_task(self._ring_finish(token, run_id))
            return None
        token["candidates"] = {**token.get("candidates", {}), me: self.priority()}
        token["max_term"] = max(int(token.get("max_term") or 0), self.term)
        asyncio.create_task(self._ring_forward("RING_ELECTION", token, run_id))
        return None

    async def _on_ring_coordinator(self, env: Dict[str, Any]) -> None:
        tok, run_id, me = env.get("payload", {}), env.get("run_id"), self.node.node_id
        if tok.get("initiator") == me:
            self.running, self.running_algorithm = False, None
            self.node.transport.local_event("RING_COMPLETE", algo="ring", run_id=run_id,
                                            detail={"leader": tok.get("leader"), "term": tok.get("term")})
            return None
        self._accept(tok["leader"], int(tok["term"]), run_id, "ring", f"RING_COORDINATOR from {env['src']}")
        asyncio.create_task(self._ring_forward("RING_COORDINATOR", tok, run_id))
        return None
