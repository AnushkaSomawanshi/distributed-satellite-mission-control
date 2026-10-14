"""
Constellation status board - the AP side of the CAP demo (self-study: trade-offs in distributed databases).

A small replicated key-value store held by every satellite:
- A write is ALWAYS accepted locally, even during a partition (availability), then pushed to every
  reachable satellite; anti-entropy (each satellite pushes its whole store to a random peer every few
  seconds) spreads it further once links return.
- Every stored version carries a VECTOR CLOCK. On merge, a version dominated by another is dropped;
  versions that are CONCURRENT (written on both sides of a partition) are both kept as siblings:
  a detected conflict, never a silent overwrite.
- A conflict is resolved by writing a new value whose vector clock dominates all siblings.
This replaces the earlier Mission-Control-only "partition reconciliation" that only merged clocks.
"""

import asyncio
import logging
import random
import time
from typing import Any, Dict, List

from .clocks import VectorClock
from .transport import PeerUnreachable

logger = logging.getLogger("dsync.board")

ANTI_ENTROPY_EVERY = 4.0


class StatusBoard:
    def __init__(self, node: Any):
        self.node = node
        self.store: Dict[str, List[Dict[str, Any]]] = {}
        self.conflicts_detected = 0
        t = node.transport
        t.on("BOARD_PUT", self._on_put)
        t.on("BOARD_SYNC", self._on_sync)

    # ------------------------------------------------------------ merge rule
    def _merge(self, key: str, incoming: Dict[str, Any]) -> str:
        versions = self.store.setdefault(key, [])
        keep = []
        for v in versions:
            rel = VectorClock.compare(v["vclock"], incoming["vclock"])
            if rel == "EQUAL":
                return "DUPLICATE"
            if rel == "AFTER":            # we already have something newer
                return "STALE"
            if rel == "CONCURRENT":
                keep.append(v)
            # BEFORE: incoming supersedes v -> drop v
        was_conflict = len(versions) > 1
        keep.append(incoming)
        self.store[key] = keep
        if len(keep) > 1 and not was_conflict:
            self.conflicts_detected += 1
            self.node.transport.local_event("BOARD_CONFLICT", algo="board", detail={
                "key": key, "siblings": [{"value": v["value"], "writer": v["writer"], "vclock": v["vclock"]} for v in keep]})
        return "CONFLICT" if len(keep) > 1 else "APPLIED"

    # ------------------------------------------------------------ writes
    async def put(self, key: str, value: Any, resolves: bool = False) -> Dict[str, Any]:
        me = self.node.node_id
        clock: Dict[str, int] = {}
        for v in self.store.get(key, []):           # the new version supersedes everything we have seen
            for k, n in v["vclock"].items():
                clock[k] = max(clock.get(k, 0), n)
        clock[me] = clock.get(me, 0) + 1
        version = {"value": value, "vclock": clock, "writer": me, "written_at": time.time(), "resolution": resolves}
        self.store[key] = [version]
        self.node.transport.local_event("BOARD_WRITE", algo="board", detail={"key": key, "value": value, "vclock": clock,
                                                                          "resolves_conflict": resolves})
        reached, missed = [], []
        for p in self.node.directory.live_ids():
            try:
                await self.node.transport.send(p, "BOARD_PUT", {"key": key, "version": version}, algo="board")
                reached.append(p)
            except PeerUnreachable:
                missed.append(p)
        return {"accepted": True, "by": me, "key": key, "version": version, "replicated_to": reached,
                "not_reached": missed, "consistency": "eventual (AP)"}

    async def resolve(self, key: str, strategy: str = "lww") -> Dict[str, Any]:
        siblings = self.store.get(key, [])
        if len(siblings) < 2:
            return {"resolved": False, "reason": "no conflict on this key"}
        if strategy == "merge":
            value = " | ".join(sorted({str(v["value"]) for v in siblings}))
        else:  # last writer wins on the writer's timestamp, satellite ID breaks ties
            value = max(siblings, key=lambda v: (v["written_at"], v["writer"]))["value"]
        out = await self.put(key, value, resolves=True)
        out["resolved_from"] = [{"value": v["value"], "writer": v["writer"]} for v in siblings]
        out["strategy"] = strategy
        return out

    async def _on_put(self, env: Dict[str, Any]) -> None:
        self._merge(env["payload"]["key"], env["payload"]["version"])
        return None

    # ------------------------------------------------------------ anti-entropy
    async def _on_sync(self, env: Dict[str, Any]) -> None:
        for key, versions in env["payload"].get("store", {}).items():
            for v in versions:
                self._merge(key, v)
        return None

    async def push_to(self, peer: str) -> bool:
        try:
            await self.node.transport.send(peer, "BOARD_SYNC", {"store": self.store}, algo="board")
            return True
        except PeerUnreachable:
            return False

    async def run(self) -> None:
        while True:
            await asyncio.sleep(ANTI_ENTROPY_EVERY)
            try:
                peers = [p for p in self.node.directory.live_ids() if p not in self.node.transport.blocked]
                if self.store and peers and not self.node.transport.silent:
                    await self.push_to(random.choice(peers))
            except asyncio.CancelledError:
                break
            except Exception as exc:  # pragma: no cover
                logger.warning("anti-entropy error: %s", exc)

    def to_dict(self) -> Dict[str, Any]:
        return {"keys": {k: [{"value": v["value"], "writer": v["writer"], "vclock": v["vclock"],
                              "written_at": v["written_at"], "resolution": v.get("resolution", False)} for v in vs]
                         for k, vs in sorted(self.store.items())},
                "conflicts_detected": self.conflicts_detected}
