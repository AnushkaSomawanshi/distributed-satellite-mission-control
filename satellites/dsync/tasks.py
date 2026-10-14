"""
Mission tasks are OWNED by satellites (Phase 3: autonomous task redistribution).

- Every task lives on exactly one satellite and carries a version number.
- Handoff traffic (optional, like a target region passing from one satellite's footprint to the
  next): an owner hands a task to another capable satellite. The task leaves the sender before it
  reaches the receiver, so it is "in the channel" meanwhile - which Chandy-Lamport snapshots record.
- The elected leader keeps an ownership view from beacons (each beacon lists the sender's tasks).
  When a satellite is declared DEAD, the leader reassigns its tasks to the best capable live
  satellite (score from backend/fa2_extensions/catalog.py) with version + 1.
- Fencing: a satellite that comes back still holding an old version is told to drop it
  (TASK_REVOKE), so no task ends up running twice.
"""

import asyncio
import logging
import random
from typing import Any, Dict, List, Optional

from backend.fa2_extensions.catalog import MISSION_TASKS, TASKS_BY_ID, capable, suitability

from .transport import PeerUnreachable

logger = logging.getLogger("dsync.tasks")


class TaskService:
    def __init__(self, node: Any, handoff_every=(0.8, 2.0), link_delay=(0.3, 1.2)):
        self.node = node
        self.handoff_every = handoff_every
        self.link_delay = link_delay
        me = node.node_id
        self.owned: Dict[str, Dict[str, Any]] = {
            t["task_id"]: self._task_record(t["task_id"], me, 1) for t in MISSION_TASKS if t["initial_owner"] == me
        }
        self.known: Dict[str, Dict[str, Any]] = {}   # leader's ownership view: task_id -> {owner, version}
        self.traffic = False
        self.reassignments: List[Dict[str, Any]] = []
        t = node.transport
        t.on("TASK_HANDOFF", self._on_handoff)
        t.on("TASK_ASSIGN", self._on_assign)
        t.on("TASK_REVOKE", self._on_revoke)

    @staticmethod
    def _task_record(task_id: str, owner: str, version: int) -> Dict[str, Any]:
        base = TASKS_BY_ID[task_id]
        return {"task_id": task_id, "owner": owner, "version": version, "priority": base["priority"],
                "required_capabilities": base["required_capabilities"], "task_type": base["task_type"]}

    # ---------------------------------------------------------------- views
    def summary(self) -> List[Dict[str, Any]]:
        return [{"task_id": t["task_id"], "version": t["version"]} for t in self.owned.values()]

    def to_dict(self) -> Dict[str, Any]:
        return {"owned": sorted(self.owned.values(), key=lambda t: t["task_id"]), "traffic": self.traffic,
                "ownership_view": self.known if self.is_leader() else None,
                "recent_reassignments": self.reassignments[-10:]}

    def is_leader(self) -> bool:
        return self.node.election.leader == self.node.node_id

    def _note(self, task_id: str, owner: str, version: int) -> None:
        cur = self.known.get(task_id)
        if cur is None or version >= cur["version"]:
            self.known[task_id] = {"owner": owner, "version": version}

    def observe_beacon(self, src: str, payload: Dict[str, Any]) -> None:
        for t in payload.get("tasks") or []:
            tid, ver = t["task_id"], int(t["version"])
            cur = self.known.get(tid)
            if cur and cur["owner"] != src and ver < cur["version"] and self.is_leader():
                # src holds an outdated copy (e.g. it was declared dead and came back): fence it off
                asyncio.ensure_future(self._revoke(src, tid, cur["version"], reason="STALE_COPY"))
                continue
            self._note(tid, src, ver)
        for t in self.owned.values():
            self._note(t["task_id"], self.node.node_id, t["version"])

    # ---------------------------------------------------------------- handoff traffic
    async def run(self) -> None:
        while True:
            await asyncio.sleep(random.uniform(*self.handoff_every))
            try:
                if self.traffic and not self.node.transport.silent and self.owned:
                    await self.handoff_once()
            except asyncio.CancelledError:
                break
            except Exception as exc:  # pragma: no cover
                logger.warning("handoff loop error: %s", exc)

    async def handoff_once(self, run_id: Optional[str] = None) -> Optional[str]:
        tid = random.choice(sorted(self.owned))
        task = self.owned[tid]
        targets = [p for p in self.node.directory.live_ids() if capable(p, TASKS_BY_ID[tid])
                   and p not in self.node.transport.blocked]
        if not targets:
            return None
        dest = random.choice(targets)
        moved = {**task, "owner": dest, "version": task["version"] + 1}
        del self.owned[tid]                       # leaves the sender now: in the channel until delivered
        self.node.transport.local_event("TASK_HANDOFF_SENT", algo="tasks", run_id=run_id,
                                        detail={"task_id": tid, "to": dest, "version": moved["version"]})
        try:
            await self.node.transport.send(dest, "TASK_HANDOFF", {"task": moved}, algo="tasks", run_id=run_id,
                                           link_delay=random.uniform(*self.link_delay), timeout=4.0)
            self._note(tid, dest, moved["version"])
            return dest
        except PeerUnreachable:
            self.owned[tid] = task                 # not delivered: the task never left
            self.node.transport.local_event("TASK_HANDOFF_FAILED", algo="tasks", run_id=run_id,
                                            detail={"task_id": tid, "to": dest})
            return None

    async def _on_handoff(self, env: Dict[str, Any]) -> None:
        task = dict(env["payload"]["task"])
        task["owner"] = self.node.node_id
        self.owned[task["task_id"]] = task
        self._note(task["task_id"], self.node.node_id, task["version"])
        self.node.transport.local_event("TASK_RECEIVED", algo="tasks", run_id=env.get("run_id"),
                                        detail={"task_id": task["task_id"], "from": env["src"], "version": task["version"]})
        return None

    # ---------------------------------------------------------------- leader: redistribution
    def _candidate_stats(self, sid: str) -> Dict[str, float]:
        if sid == self.node.node_id:
            info = self.node.info()
            return {"health": info.get("health", 0), "battery": info.get("battery", 0), "signal": info.get("signal", 0)}
        e = self.node.directory.get(sid) or {}
        return {"health": e.get("health") or 0, "battery": e.get("battery") or 0, "signal": e.get("signal") or 0}

    def _load(self, sid: str) -> int:
        return sum(1 for k in self.known.values() if k["owner"] == sid)

    async def reassign(self, task_id: str, reason: str, run_id: Optional[str] = None,
                       exclude: tuple = ()) -> Dict[str, Any]:
        task_def = TASKS_BY_ID[task_id]
        prev = self.known.get(task_id, {"owner": None, "version": 1})
        candidates = [s for s in set(self.node.directory.live_ids()) | {self.node.node_id}
                      if s not in exclude and s not in self.node.transport.blocked]
        scores = sorted((suitability(s, task_def, load=self._load(s), **self._candidate_stats(s)) for s in candidates),
                        key=lambda x: x["total_score"], reverse=True)
        eligible = [s for s in scores if s["eligible"]]
        result = {"task_id": task_id, "from": prev["owner"], "reason": reason, "scores": scores}
        if not eligible:
            result["status"] = "NO_CAPABLE_SATELLITE"
            self.node.transport.local_event("TASK_UNASSIGNED", algo="tasks", run_id=run_id, detail=result)
            return result
        best = eligible[0]["satellite_id"]
        version = prev["version"] + 1
        record = self._task_record(task_id, best, version)
        if best == self.node.node_id:
            self.owned[task_id] = record
        else:
            try:
                await self.node.transport.send(best, "TASK_ASSIGN", {"task": record, "reason": reason},
                                               algo="tasks", run_id=run_id)
            except PeerUnreachable:
                result["status"] = "TARGET_UNREACHABLE"
                return result
        self._note(task_id, best, version)
        result.update({"to": best, "version": version, "status": "REASSIGNED"})
        self.reassignments.append({k: v for k, v in result.items() if k != "scores"})
        self.node.transport.local_event("TASK_REASSIGNED", algo="tasks", run_id=run_id,
                                        detail={"task_id": task_id, "from": prev["owner"], "to": best,
                                                "version": version, "reason": reason,
                                                "winning_score": eligible[0]["total_score"]})
        return result

    async def on_peer_dead(self, peer: str) -> None:
        if not self.is_leader():
            return
        for tid, k in sorted(self.known.items()):
            if k["owner"] == peer:
                await self.reassign(tid, reason=f"OWNER_{peer}_DEAD", exclude=(peer,))

    async def reconcile(self) -> List[Dict[str, Any]]:
        """New leader: take over any task whose last known owner is not alive."""
        await asyncio.sleep(self.node.beacons.interval * 1.5)  # let one beacon round refresh the view
        if not self.is_leader():
            return []
        live = set(self.node.directory.live_ids()) | {self.node.node_id}
        out = []
        for tid, k in sorted(self.known.items()):
            if k["owner"] not in live:
                out.append(await self.reassign(tid, reason=f"OWNER_{k['owner']}_NOT_ALIVE"))
        return out

    def on_leader_change(self, leader: Optional[str], term: int) -> None:
        if leader == self.node.node_id:
            asyncio.ensure_future(self.reconcile())

    async def operator_assign(self, task_id: str, owner: str) -> Dict[str, Any]:
        """Operator request routed through the leader: move a task to a chosen capable satellite."""
        if not self.is_leader():
            raise RuntimeError("only the leader assigns tasks")
        if task_id not in TASKS_BY_ID:
            raise ValueError(f"unknown task {task_id}")
        if not capable(owner, TASKS_BY_ID[task_id]):
            raise ValueError(f"{owner} lacks the capabilities {TASKS_BY_ID[task_id]['required_capabilities']}")
        prev = self.known.get(task_id, {"owner": None, "version": 1})
        version = prev["version"] + 1
        record = self._task_record(task_id, owner, version)
        if owner == self.node.node_id:
            self.owned[task_id] = record
        else:
            await self.node.transport.send(owner, "TASK_ASSIGN", {"task": record, "reason": "OPERATOR"}, algo="tasks")
        if prev["owner"] and prev["owner"] != owner:
            await self._revoke(prev["owner"], task_id, version, reason="OPERATOR_REASSIGN")
        self._note(task_id, owner, version)
        self.node.transport.local_event("TASK_REASSIGNED", algo="tasks", detail={
            "task_id": task_id, "from": prev["owner"], "to": owner, "version": version, "reason": "OPERATOR"})
        return {"task_id": task_id, "from": prev["owner"], "to": owner, "version": version}

    async def _revoke(self, sid: str, task_id: str, version: int, reason: str) -> None:
        if sid == self.node.node_id:
            cur = self.owned.get(task_id)
            if cur and cur["version"] < version:
                del self.owned[task_id]
            return
        try:
            await self.node.transport.send(sid, "TASK_REVOKE", {"task_id": task_id, "version": version, "reason": reason},
                                           algo="tasks")
        except PeerUnreachable:
            pass

    async def _on_assign(self, env: Dict[str, Any]) -> None:
        task = dict(env["payload"]["task"])
        cur = self.owned.get(task["task_id"])
        if cur and cur["version"] >= task["version"]:
            return None
        self.owned[task["task_id"]] = task
        self._note(task["task_id"], self.node.node_id, task["version"])
        self.node.transport.local_event("TASK_ASSIGNED", algo="tasks", run_id=env.get("run_id"),
                                        detail={"task_id": task["task_id"], "version": task["version"],
                                                "by": env["src"], "reason": env["payload"].get("reason")})
        return None

    async def _on_revoke(self, env: Dict[str, Any]) -> None:
        p = env["payload"]
        cur = self.owned.get(p["task_id"])
        if cur and cur["version"] < int(p["version"]):
            del self.owned[p["task_id"]]
            self.node.transport.local_event("TASK_REVOKED", algo="tasks", run_id=env.get("run_id"),
                                            detail={"task_id": p["task_id"], "stale_version": cur["version"],
                                                    "current_version": p["version"], "reason": p.get("reason")})
        return None
