"""
USP-20: MISSION TASK DEPENDENCY GRAPH ENGINE

Maps task dependencies ($T_{001} \rightarrow T_{002} \rightarrow T_{003} \rightarrow \{T_{004}, T_{005}\}$) and evaluates downstream objective risk when upstream tasks or satellites fail.
"""

import time
import logging
from typing import Dict, Any, List, Optional
from backend.services.task_manager import global_task_manager

logger = logging.getLogger("DependencyGraph")

TASK_DEPENDENCIES = {
    "T-047": [], # Root task (Earth observation)
    "T-048": ["T-047"], # Thermal scan depends on observation
    "T-049": ["T-047"], # Data relay depends on observation
    "T-050": ["T-048", "T-049"], # Orbital compute depends on thermal & relay
    "T-051": ["T-050"] # Atmospheric aggregation depends on compute
}

class DependencyGraphEngine:
    def get_dependency_tree(self) -> Dict[str, Any]:
        tasks = global_task_manager.list_tasks()
        task_dict = {t["task_id"]: t for t in tasks}

        tree = []
        for t_id, parent_ids in TASK_DEPENDENCIES.items():
            t_obj = task_dict.get(t_id, {"task_id": t_id, "status": "UNKNOWN", "current_owner": "UNKNOWN"})
            tree.append({
                "task_id": t_id,
                "parents": parent_ids,
                "status": t_obj.get("status", "UNKNOWN"),
                "current_owner": t_obj.get("current_owner", "UNKNOWN"),
                "priority": t_obj.get("priority", "MEDIUM")
            })

        return {
            "dependencies": TASK_DEPENDENCIES,
            "dependency_tree": tree,
            "timestamp": time.time()
        }

    def evaluate_downstream_impact(self, failed_task_id: str) -> Dict[str, Any]:
        downstream = []
        queue = [failed_task_id]

        while queue:
            curr = queue.pop(0)
            for t_id, parents in TASK_DEPENDENCIES.items():
                if curr in parents and t_id not in downstream:
                    downstream.append(t_id)
                    queue.append(t_id)

        return {
            "failed_task_id": failed_task_id,
            "downstream_impacted_tasks": downstream,
            "impacted_task_count": len(downstream),
            "mission_objective_risk": "CRITICAL" if len(downstream) >= 2 else "HIGH"
        }

global_dependency_graph = DependencyGraphEngine()
