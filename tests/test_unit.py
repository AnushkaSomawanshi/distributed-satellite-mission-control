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
    assert "SAT-88" in failed
    assert reg.lookup("SAT-88").status == "OFFLINE"
