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
async def test_end_to_end_coordinator_failure_and_task_recovery(monkeypatch):
    from backend.registry.service_registry import global_registry
    from backend.services.simulation_engine import global_simulation_engine
    from backend.fa2 import router as fa2

    # The satellites (not Mission Control) elect the new leader. Here the satellite side is stubbed:
    # the crash is "delivered" and the survivors are reported to agree on SAT-04.
    crashed = []

    async def fake_push(fault, params, targets=None):
        crashed.append((fault, targets))
        return {t: "APPLIED" for t in targets or []}

    async def fake_agreement(min_term, exclude=(), timeout=12.0):
        assert "SAT-05" in exclude
        return {"leader": "SAT-04", "term": 2, "agreed_by": ["SAT-01", "SAT-02", "SAT-03", "SAT-04"]}

    async def fake_reassignment(target, since, timeout=20.0):
        return {"failed_node": target, "tasks_reassigned_count": 1, "decided_by": "leader satellite",
                "reallocation_results": [{"task_id": "T-050", "previous_owner": target, "new_owner": "SAT-01"}]}

    import backend.services.simulation_engine as sim
    monkeypatch.setattr(fa2, "push_fault", fake_push)
    monkeypatch.setattr(fa2, "_wait_agreement", fake_agreement)
    monkeypatch.setattr(sim, "_wait_for_reassignment", fake_reassignment)

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
    assert ("CRASH", ["SAT-05"]) in crashed
    assert res["election_result"]["new_leader"] == "SAT-04"
    assert res["election_result"]["decided_by"].startswith("satellites")
    assert res["task_reallocation_result"]["decided_by"] == "leader satellite"

