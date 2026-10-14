"""
Chandy-Lamport global snapshot on the satellites (Unit 3: global state).

Channels between satellites are FIFO (see transport.py). For snapshot S:
- The initiator records its own state, then sends MARKER(S) on every outgoing channel.
- When a satellite receives MARKER(S) on channel c for the FIRST time, it records its own state,
  records c as empty, and sends MARKER(S) on all its outgoing channels.
- After recording its state, a satellite records every message that arrives on channel c until
  MARKER(S) arrives on c. Those messages were "in transit" at snapshot time.
- A satellite is done when a marker has arrived on every incoming channel. It reports its piece
  (local state + channel states) as a SNAPSHOT_LOCAL_DONE event; Mission Control assembles the
  pieces and checks the invariant: every mission task appears exactly once, either on a satellite
  or in a channel.
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

from .transport import PeerUnreachable

logger = logging.getLogger("dsync.snapshot")

SNAPSHOT_TIMEOUT = 10.0


class SnapshotService:
    def __init__(self, node: Any):
        self.node = node
        self.snaps: Dict[str, Dict[str, Any]] = {}
        node.transport.on("SNAP_MARKER", self._on_marker)
        node.transport.receive_listeners.append(self._record_in_transit)

    def _local_state(self) -> Dict[str, Any]:
        t = self.node.transport
        return {
            "tasks": [dict(x) for x in sorted(self.node.tasks.owned.values(), key=lambda x: x["task_id"])],
            "lamport": t.lamport.value,
            "vector": t.vector.to_dict(),
            "leader": self.node.election.leader,
            "term": self.node.election.term,
            "clock_skew_ms": round(self.node.physical.skew_ms(), 3),
            "in_critical_section": self.node.mutex.in_cs,
            "health": self.node.info().get("health"),
        }

    def _begin(self, snap_id: str, initiator: str, first_from: Optional[str]) -> Dict[str, Any]:
        peers = [p for p in self.node.directory.live_ids() if p not in self.node.transport.blocked]
        snap = {
            "snapshot_id": snap_id, "initiator": initiator, "node": self.node.node_id,
            "state": self._local_state(), "recorded_at": time.time(),
            "channels": {p: [] for p in peers},          # incoming channel p -> messages recorded
            "open": set(p for p in peers if p != first_from),
            "done": False,
        }
        self.snaps[snap_id] = snap
        self.node.transport.local_event("SNAPSHOT_STATE_RECORDED", algo="snapshot", run_id=snap_id,
                                        detail={"initiator": initiator, "first_marker_from": first_from,
                                                "tasks": [x["task_id"] for x in snap["state"]["tasks"]]})
        asyncio.ensure_future(self._send_markers(snap_id, initiator, peers))
        asyncio.ensure_future(self._watchdog(snap_id))
        self._maybe_done(snap_id)
        return snap

    async def _send_markers(self, snap_id: str, initiator: str, peers: List[str]) -> None:
        async def one(p: str) -> None:
            try:
                await self.node.transport.send(p, "SNAP_MARKER", {"snapshot_id": snap_id, "initiator": initiator},
                                               algo="snapshot", run_id=snap_id)
            except PeerUnreachable:
                snap = self.snaps.get(snap_id)
                if snap:   # a dead peer will never send its marker back either
                    snap["open"].discard(p)
                    self._maybe_done(snap_id)
        await asyncio.gather(*(one(p) for p in peers))

    async def start(self, snap_id: str) -> Dict[str, Any]:
        snap = self._begin(snap_id, self.node.node_id, None)
        return {"snapshot_id": snap_id, "initiator": self.node.node_id, "peers": sorted(snap["channels"])}

    def _record_in_transit(self, env: Dict[str, Any]) -> None:
        if env.get("msg_type") == "SNAP_MARKER":
            return
        src = env.get("src")
        for snap in self.snaps.values():
            if not snap["done"] and src in snap["open"]:
                snap["channels"][src].append({"msg_type": env["msg_type"], "msg_id": env["msg_id"],
                                              "payload": env.get("payload"), "lamport": env.get("lamport")})

    async def _on_marker(self, env: Dict[str, Any]) -> None:
        snap_id, src = env["payload"]["snapshot_id"], env["src"]
        snap = self.snaps.get(snap_id)
        if snap is None:
            self._begin(snap_id, env["payload"].get("initiator", src), src)
        else:
            snap["open"].discard(src)
            self._maybe_done(snap_id)
        return None

    def _maybe_done(self, snap_id: str) -> None:
        snap = self.snaps.get(snap_id)
        if not snap or snap["done"] or snap["open"]:
            return
        snap["done"] = True
        piece = self.piece(snap_id)
        self.node.transport.local_event("SNAPSHOT_LOCAL_DONE", algo="snapshot", run_id=snap_id, detail=piece)

    async def _watchdog(self, snap_id: str) -> None:
        await asyncio.sleep(SNAPSHOT_TIMEOUT)
        snap = self.snaps.get(snap_id)
        if snap and not snap["done"]:
            snap["done"] = True
            piece = self.piece(snap_id)
            piece["incomplete_channels"] = sorted(snap["open"])
            self.node.transport.local_event("SNAPSHOT_LOCAL_TIMEOUT", algo="snapshot", run_id=snap_id, detail=piece)

    def piece(self, snap_id: str) -> Dict[str, Any]:
        snap = self.snaps[snap_id]
        return {"snapshot_id": snap_id, "node": self.node.node_id, "state": snap["state"],
                "channels": {k: v for k, v in snap["channels"].items()},
                "recorded_at": snap["recorded_at"], "complete": not snap["open"]}

    def recent(self) -> List[Dict[str, Any]]:
        return [self.piece(s) for s in list(self.snaps)[-5:]]
