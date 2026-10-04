import pytest
import asyncio
from backend.registry.service_registry import SatelliteRegistry
from backend.faults.fault_simulator import FaultSimulator

def test_fault_injection_and_recovery():
    registry = SatelliteRegistry()
    registry.register("SAT-01", "NODE-01", "sat01.local", "127.0.0.1", 5001, 6001)
    
    fault_sim = FaultSimulator(registry)
    
    # Inject stop fault
    fault_sim.inject_fault("STOP_NODE", "SAT-01")
    assert registry.lookup("SAT-01").status in ["DISCONNECTED", "OFFLINE"]
    
    # Clear faults -> RECOVER
    fault_sim.clear_faults("SAT-01")
    assert registry.lookup("SAT-01").status == "HEALTHY"

@pytest.mark.asyncio
async def test_end_to_end_coordinator_failure_and_task_recovery():
    from backend.registry.service_registry import global_registry
    from backend.services.election_manager import global_election_manager
    from backend.services.reallocation_engine import global_reallocation_engine
    from backend.services.simulation_engine import global_simulation_engine

    # Seed satellites
    for i in range(1, 6):
        sat_id = f"SAT-0{i}"
        global_registry.register(sat_id, f"NODE-{sat_id}", f"{sat_id.lower()}.local", "127.0.0.1", 5000+i, 6000+i)

    # Initial leader is SAT-05
    global_registry.current_leader = "SAT-05"

    # Execute coordinator failure scenario on SAT-05
    res = await global_simulation_engine.execute_scenario("SAT-05", "COORDINATOR_FAILURE")

    assert res["mode"] == "SCENARIO_EXECUTED"
    assert res["target_node"] == "SAT-05"
    assert res["election_result"]["new_leader"] == "SAT-04"
    assert res["task_reallocation_result"]["tasks_reassigned_count"] >= 0

