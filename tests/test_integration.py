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
    assert registry.lookup("SAT-01").status == "OFFLINE"
    
    # Clear faults -> RECOVER
    fault_sim.clear_faults("SAT-01")
    assert registry.lookup("SAT-01").status == "HEALTHY"
