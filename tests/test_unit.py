import pytest
from backend.services.health_engine import HealthEngine
from backend.registry.service_registry import SatelliteRegistry

def test_health_engine_calculation():
    # Test nominal parameters -> HEALTHY
    score, status, breakdown = HealthEngine.calculate_health(
        battery=95.0, temperature=25.0, cpu_usage=15.0, memory_usage=30.0, signal_strength=95.0, is_online=True
    )
    assert score >= 90.0
    assert status == "HEALTHY"
    assert breakdown["total_score"] == score

def test_health_engine_critical():
    # Test high temperature and low battery -> CRITICAL
    score, status, breakdown = HealthEngine.calculate_health(
        battery=10.0, temperature=85.0, cpu_usage=90.0, memory_usage=90.0, signal_strength=20.0, is_online=True
    )
    assert score < 70.0
    assert status == "CRITICAL"

def test_registry_registration_and_lookup():
    reg = SatelliteRegistry(heartbeat_ttl_seconds=5.0)
    reg.register(
        satellite_id="SAT-99", node_id="NODE-99", hostname="sat99.local",
        address="127.0.0.1", grpc_port=5099, p2p_port=6099
    )
    
    found = reg.lookup("SAT-99")
    assert found is not None
    assert found.satellite_id == "SAT-99"
    assert found.grpc_port == 5099
    assert found.status == "HEALTHY"

def test_registry_heartbeat_timeout():
    reg = SatelliteRegistry(heartbeat_ttl_seconds=0.1)
    reg.register("SAT-88", "NODE-88", "sat88.local", "127.0.0.1", 5088, 6088)
    
    # Fast forward time
    import time
    time.sleep(0.2)
    failed = reg.sweep_failures()
    assert "SAT-88" in failed.get("disconnected", [])
    assert reg.lookup("SAT-88").status in ["DISCONNECTED", "OFFLINE"]

def test_physical_clock_synchronization():
    from backend.services.distributed_clocks import PhysicalClock
    pclock = PhysicalClock("SAT-01", initial_drift_ms=150.0)
    ref_time = 1000.0
    rec = pclock.synchronize(reference_time=ref_time, round_trip_delay_ms=20.0)
    assert rec["rtt_ms"] == 20.0
    assert "calculated_offset_ms" in rec
    assert rec["residual_error_ms"] == 10.0

def test_lamport_and_vector_clocks():
    from backend.services.distributed_clocks import LamportClock, VectorClock
    l1 = LamportClock(10)
    assert l1.increment() == 11
    assert l1.update(15) == 16

    v1 = VectorClock(["SAT-01", "SAT-02", "SAT-03"])
    v1.increment("SAT-01")
    v2 = VectorClock(["SAT-01", "SAT-02", "SAT-03"])
    v2.increment("SAT-02")

    comp = VectorClock.compare(v1.to_dict(), v2.to_dict())
    assert comp == "CONCURRENT"

def test_task_reallocation_suitability_scoring():
    from backend.services.reallocation_engine import global_reallocation_engine
    task = {
        "task_id": "T-TEST",
        "required_capabilities": ["CAMERA", "COMPUTE"]
    }
    score = global_reallocation_engine.calculate_candidate_score("SAT-01", task)
    assert score["eligible"] is True
    assert score["total_score"] > 50.0

def test_chandy_lamport_snapshot():
    from backend.services.snapshot_manager import global_snapshot_manager
    snap = global_snapshot_manager.take_snapshot("SAT-01")
    assert snap["snapshot_id"].startswith("SNAP-")
    assert "satellites" in snap["global_state"]
    assert "tasks" in snap["global_state"]

def test_resilience_scorecard():
    from backend.services.resilience_engine import global_resilience_engine
    scorecard = global_resilience_engine.calculate_resilience_metrics()
    assert "mission_continuity_pct" in scorecard
    assert scorecard["mission_continuity_pct"] >= 0.0

