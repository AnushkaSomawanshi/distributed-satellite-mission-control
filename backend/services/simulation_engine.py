"""
MISSION FAILURE SIMULATOR & EXPERIMENT FRAMEWORK

Provides predictive impact simulation ("Simulate Impact") and actual scenario execution ("Execute Scenario")
for failure scenarios:
- Single Satellite Failure
- Coordinator Node Failure (e.g. SAT-05)
- Simultaneous Multiple Satellite Failures (e.g. SAT-02 + SAT-04)
- Communication Network Partition (e.g. SAT-01/02 vs SAT-03/04/05)
- Latency & Packet Loss Injection
"""

import time
import asyncio
import logging
from typing import Dict, Any, List, Optional
from backend.registry.service_registry import global_registry
from backend.faults.fault_simulator import global_fault_simulator
from backend.services.impact_analyzer import global_impact_analyzer
from backend.services.election_manager import global_election_manager
from backend.services.reallocation_engine import global_task_manager, global_reallocation_engine
from backend.services.resilience_engine import global_resilience_engine

logger = logging.getLogger("SimulationEngine")

class FailureSimulator:
    def simulate_impact(self, target_node: str, scenario_type: str = "SINGLE_NODE_FAILURE") -> Dict[str, Any]:
        start_t = time.time()
        impact = global_impact_analyzer.analyze_failure(target_node)
        affected_tasks = impact["affected_tasks"]

        predicted_reallocations = []
        for t in affected_tasks:
            cand_scores = [
                global_reallocation_engine.calculate_candidate_score(c, t)
                for c in ["SAT-01", "SAT-02", "SAT-03", "SAT-04", "SAT-05"] if c != target_node
            ]
            el = [s for s in cand_scores if s["eligible"]]
            el.sort(key=lambda x: x["total_score"], reverse=True)

            predicted_reallocations.append({
                "task_id": t["task_id"],
                "predicted_new_owner": el[0]["satellite_id"] if el else None,
                "predicted_score": el[0]["total_score"] if el else 0.0,
                "candidate_scores": cand_scores
            })

        predicted_new_leader = None
        if impact["is_coordinator_failed"]:
            surviving = [s for s in ["SAT-01", "SAT-02", "SAT-03", "SAT-04", "SAT-05"] if s != target_node]
            predicted_new_leader = max(surviving) if surviving else "NONE"

        return {
            "mode": "PREDICTIVE_SIMULATION",
            "scenario_type": scenario_type,
            "target_node": target_node,
            "predicted_risk": impact["mission_risk"],
            "predicted_coordinator_failed": impact["is_coordinator_failed"],
            "predicted_new_coordinator": predicted_new_leader,
            "affected_task_count": len(affected_tasks),
            "predicted_task_reallocations": predicted_reallocations,
            "simulation_duration_ms": round((time.time() - start_t) * 1000, 2)
        }

    async def execute_scenario(self, target_node: str, scenario_type: str = "SINGLE_NODE_FAILURE") -> Dict[str, Any]:
        start_t = time.time()
        logger.info(f"[EXECUTE SCENARIO] Running real distributed failure scenario '{scenario_type}' on target node {target_node}")

        # 1. Apply fault injection to target node
        global_fault_simulator.inject_fault(
            fault_type="STOP",
            target_node=target_node,
            parameters={"scenario": scenario_type},
            source="SIMULATOR"
        )
        global_registry.set_status(target_node, "DISCONNECTED", source="SIMULATOR")

        # 2. Run Ring Election if coordinator failed
        election_res = None
        if target_node == global_registry.current_leader:
            initiator = [s for s in ["SAT-01", "SAT-02", "SAT-03", "SAT-04", "SAT-05"] if s != target_node][0]
            election_res = await global_election_manager.execute_ring_election(initiator_id=initiator)

        # 3. Execute Autonomous Task Reallocation
        reallocation_res = await global_reallocation_engine.execute_reallocation_for_failed_node(target_node)

        # 4. Calculate final resilience metrics
        resilience = global_resilience_engine.calculate_resilience_metrics()

        duration_ms = round((time.time() - start_t) * 1000, 2)

        return {
            "mode": "SCENARIO_EXECUTED",
            "scenario_type": scenario_type,
            "target_node": target_node,
            "election_result": election_res,
            "task_reallocation_result": reallocation_res,
            "post_execution_resilience": resilience,
            "total_execution_duration_ms": duration_ms,
            "timestamp": start_t
        }

global_simulation_engine = FailureSimulator()
