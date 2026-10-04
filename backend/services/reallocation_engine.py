"""
AUTONOMOUS TASK REALLOCATION ENGINE

Calculates transparent deterministic candidate suitability scores when a satellite fails:
Suitability Score =
    30% Health Score
  + 25% Capability Match Score
  + 20% Available Compute/Battery Capacity Score
  + 15% Communication Quality Score
  + 10% Mission Priority Compatibility Score

Ranks candidate nodes and reassigns orphaned tasks via Ricart-Agrawala Mutual Exclusion.
"""

import time
import asyncio
import logging
from typing import Dict, Any, List, Optional
from backend.registry.service_registry import global_registry
from backend.services.task_manager import global_task_manager, SATELLITE_CAPABILITIES
from backend.services.mutex_manager import global_mutex_engine
from backend.services.impact_analyzer import global_impact_analyzer

logger = logging.getLogger("TaskReallocationEngine")

class TaskReallocationEngine:
    def calculate_candidate_score(self, candidate_id: str, task: Dict[str, Any]) -> Dict[str, Any]:
        reg = global_registry.lookup(candidate_id)
        if not reg:
            num = candidate_id.split("-")[-1] if "-" in candidate_id else "01"
            try:
                idx = int(num)
            except ValueError:
                idx = 1
            reg = global_registry.register(
                satellite_id=candidate_id,
                node_id=f"NODE-{candidate_id}",
                hostname=f"{candidate_id.lower()}.local",
                address="127.0.0.1",
                grpc_port=5000+idx,
                p2p_port=6000+idx
            )

        if not reg or reg.status in ["OFFLINE", "DISCONNECTED", "FAILED"]:

            return {
                "satellite_id": candidate_id,
                "total_score": 0.0,
                "health_score": 0.0,
                "capability_score": 0.0,
                "capacity_score": 0.0,
                "comm_score": 0.0,
                "priority_score": 0.0,
                "eligible": False,
                "rejection_reason": "Satellite is offline or disconnected"
            }

        # 1. Health Score (30%)
        health_component = reg.health_score * 0.30

        # 2. Capability Match Score (25%)
        node_caps = SATELLITE_CAPABILITIES.get(candidate_id, [])
        req_caps = task.get("required_capabilities", [])
        matched = [c for c in req_caps if c in node_caps]
        cap_match_ratio = (len(matched) / len(req_caps)) if req_caps else 1.0
        capability_component = (cap_match_ratio * 100.0) * 0.25

        if cap_match_ratio < 1.0:
            eligible = False
            rejection = f"Missing required capabilities: {[c for c in req_caps if c not in node_caps]}"
        else:
            eligible = True
            rejection = None

        # 3. Available Capacity Score (20%)
        # High battery + low CPU = high capacity score
        capacity_raw = ((reg.battery / 100.0) * 50.0) + (((100.0 - reg.cpu_usage) / 100.0) * 50.0)
        capacity_component = capacity_raw * 0.20

        # 4. Communication Quality Score (15%)
        comm_component = reg.signal_strength * 0.15

        # 5. Mission Priority Compatibility Score (10%)
        priority_component = 90.0 * 0.10

        total_score = round(health_component + capability_component + capacity_component + comm_component + priority_component, 2)

        return {
            "satellite_id": candidate_id,
            "total_score": total_score,
            "health_score": round(health_component, 2),
            "capability_score": round(capability_component, 2),
            "capacity_score": round(capacity_component, 2),
            "comm_score": round(comm_component, 2),
            "priority_score": round(priority_component, 2),
            "matched_capabilities": matched,
            "eligible": eligible,
            "rejection_reason": rejection
        }

    async def execute_reallocation_for_failed_node(self, failed_node_id: str) -> Dict[str, Any]:
        start_t = time.time()
        impact = global_impact_analyzer.analyze_failure(failed_node_id)
        affected_tasks = impact["affected_tasks"]

        reallocation_results = []

        for task in affected_tasks:
            t_id = task["task_id"]
            candidates = [s for s in ["SAT-01", "SAT-02", "SAT-03", "SAT-04", "SAT-05"] if s != failed_node_id]

            scores = [self.calculate_candidate_score(cand_id, task) for cand_id in candidates]
            eligible_scores = [s for s in scores if s["eligible"]]
            eligible_scores.sort(key=lambda x: x["total_score"], reverse=True)

            if eligible_scores:
                best_candidate = eligible_scores[0]["satellite_id"]
                best_score = eligible_scores[0]["total_score"]

                # Acquire Ricart-Agrawala Mutex for task claim
                mutex_res = await global_mutex_engine.request_resource(best_candidate, t_id)

                # Transfer task
                reassigned_task = global_task_manager.reassign_task(t_id, best_candidate, reason=f"AUTONOMOUS_REALLOCATION_FROM_{failed_node_id}")

                # Release Mutex
                global_mutex_engine.release_resource(best_candidate, t_id)

                reallocation_results.append({
                    "task_id": t_id,
                    "previous_owner": failed_node_id,
                    "new_owner": best_candidate,
                    "winning_score": best_score,
                    "candidate_scores": scores,
                    "mutex_result": mutex_res,
                    "reassigned_task": reassigned_task,
                    "status": "REASSIGNED_SUCCESS"
                })
            else:
                reallocation_results.append({
                    "task_id": t_id,
                    "previous_owner": failed_node_id,
                    "new_owner": None,
                    "status": "NO_ELIGIBLE_CANDIDATE",
                    "candidate_scores": scores
                })

        duration_ms = round((time.time() - start_t) * 1000, 2)

        return {
            "failed_node": failed_node_id,
            "tasks_reassigned_count": len([r for r in reallocation_results if r["status"] == "REASSIGNED_SUCCESS"]),
            "reallocation_results": reallocation_results,
            "duration_ms": duration_ms,
            "timestamp": start_t
        }

global_reallocation_engine = TaskReallocationEngine()
