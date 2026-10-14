"""
AUTONOMOUS TASK REALLOCATION ENGINE

Calculates transparent deterministic candidate suitability scores when a satellite fails:
Suitability Score =
    30% Health Score
  + 25% Capability Match Score
  + 20% Available Compute/Battery Capacity Score
  + 15% Communication Quality Score
  + 10% Mission Priority Compatibility Score

Used only for PREDICTIVE "what if" simulation in Mission Control. The real reassignment is decided
on board by the leader satellite (satellites/dsync/tasks.py, scoring in fa2_extensions/catalog.py).
"""

import time
import asyncio
import logging
from typing import Dict, Any, List, Optional
from backend.registry.service_registry import global_registry
from backend.services.task_manager import global_task_manager, SATELLITE_CAPABILITIES
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

global_reallocation_engine = TaskReallocationEngine()
