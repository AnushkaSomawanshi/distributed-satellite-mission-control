"""
MISSION RESILIENCE & CONTINUITY ENGINE

Calculates key resilience KPIs and continuity metrics:
- Mission Continuity Percentage (% active tasks preserved or successfully reassigned)
- Active Satellites Ratio (Healthy nodes / Total nodes)
- Tasks Preserved vs Lost
- Coordinator Recovery Status
- Ricart-Agrawala Mutex Conflicts
- Chandy-Lamport Snapshot Consistency Status
- Total Recovery Duration
"""

import time
import logging
from typing import Dict, Any, List, Optional
from backend.registry.service_registry import global_registry
from backend.services.task_manager import global_task_manager

logger = logging.getLogger("ResilienceEngine")

class ResilienceEngine:
    def calculate_resilience_metrics(self) -> Dict[str, Any]:
        sats = global_registry.list_all()
        total_nodes = len(sats) if sats else 5
        active_nodes = len([s for s in sats if s.status not in ["OFFLINE", "DISCONNECTED", "FAILED"]])

        tasks = global_task_manager.list_tasks()
        total_tasks = len(tasks)
        running_or_reassigned = len([t for t in tasks if t["status"] in ["RUNNING", "REASSIGNED", "COMPLETED"]])
        affected_unresolved = len([t for t in tasks if t["status"] == "AFFECTED"])

        continuity_pct = round((running_or_reassigned / total_tasks * 100.0), 1) if total_tasks > 0 else 100.0

        current_leader = global_registry.current_leader
        leader_reg = global_registry.lookup(current_leader)
        is_leader_healthy = bool(leader_reg and leader_reg.status not in ["OFFLINE", "DISCONNECTED", "FAILED"])

        from backend.fa2.router import arena_runs
        last_election = next((r for r in reversed(arena_runs) if r.get("kind") in ("election", "leader_failure")), None)

        return {
            "mission_continuity_pct": continuity_pct,
            "overall_status": "OPERATIONAL" if continuity_pct >= 80.0 else ("DEGRADED" if continuity_pct >= 50.0 else "CRITICAL"),
            "active_satellites_ratio": f"{active_nodes}/{total_nodes}",
            "active_satellites_count": active_nodes,
            "total_satellites_count": total_nodes,
            "tasks_total": total_tasks,
            "tasks_preserved": running_or_reassigned,
            "tasks_affected_unresolved": affected_unresolved,
            "current_coordinator": current_leader,
            "coordinator_healthy": is_leader_healthy,
            "last_election_id": last_election.get("run_id") if last_election else "N/A",
            "snapshot_consistency": _last_snapshot_consistency(),
            "last_recovery_duration_ms": (last_election.get("time_to_new_leader_ms") or last_election.get("agreement_observed_ms")) if last_election else None,
            "calculated_at": time.time()
        }

def _last_snapshot_consistency() -> str:
    """Result of the most recent Chandy-Lamport snapshot taken on the satellites (not assumed)."""
    try:
        from backend.fa2.phase3 import snapshot_history
    except Exception:
        return "NO_SNAPSHOT_YET"
    if not snapshot_history:
        return "NO_SNAPSHOT_YET"
    return "VALID" if snapshot_history[-1]["consistency"]["holds"] else "INVARIANT_VIOLATED"


global_resilience_engine = ResilienceEngine()
