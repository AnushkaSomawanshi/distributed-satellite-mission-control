import time
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class FaultSimulator:
    """
    Simulates distributed design issues & faults:
    - Node stopping / crash
    - Node restart / re-registration
    - Network latency injection
    - Packet / message loss simulation
    - Metric spikes (Temperature, Battery drain, CPU overload)
    """
    def __init__(self, registry):
        self.registry = registry
        self.active_faults: Dict[str, Dict[str, Any]] = {}
        self.fault_history: List[Dict[str, Any]] = []

    def inject_fault(
        self,
        fault_type: str,
        target_node: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        fault_id = f"fault-{fault_type}-{target_node}-{int(time.time())}"
        params = parameters or {}
        
        fault_record = {
            "fault_id": fault_id,
            "fault_type": fault_type,
            "target_node": target_node,
            "parameters": params,
            "applied_at": time.time(),
            "is_active": True
        }

        self.active_faults[fault_id] = fault_record
        self.fault_history.append(fault_record)

        # Apply specific fault mechanics
        reg = self.registry.lookup(target_node)
        if fault_type == "STOP_NODE":
            self.registry.set_status(target_node, "OFFLINE")
            if reg:
                reg.health_score = 0.0
        elif fault_type == "RESTART_NODE":
            self.registry.set_status(target_node, "HEALTHY")
            if reg:
                reg.last_heartbeat = time.time()
                reg.health_score = 100.0
                reg.battery = 100.0
                reg.temperature = 25.0
                reg.cpu_usage = 15.0
        elif fault_type == "HIGH_LATENCY":
            latency_ms = float(params.get("latency_ms", 500))
            fault_record["latency_ms"] = latency_ms
        elif fault_type == "PACKET_LOSS":
            loss_pct = float(params.get("loss_pct", 20.0))
            fault_record["loss_pct"] = loss_pct
        elif fault_type == "TEMP_SPIKE":
            if reg:
                reg.temperature = float(params.get("temperature", 85.0))
                reg.health_score = 45.0
                reg.status = "CRITICAL"
        elif fault_type == "BATTERY_DRAIN":
            if reg:
                reg.battery = float(params.get("battery", 15.0))
                reg.health_score = 30.0
                reg.status = "CRITICAL"
        elif fault_type == "CPU_OVERLOAD":
            if reg:
                reg.cpu_usage = float(params.get("cpu_usage", 98.0))
                reg.health_score = 65.0
                reg.status = "WARNING"

        logger.info(f"[FAULT APPLIED] Target={target_node} | Fault={fault_type} | Params={params} | Status={reg.status if reg else 'UNKNOWN'}")
        return fault_record

    def clear_faults(self, target_node: Optional[str] = None) -> int:
        cleared_count = 0
        to_remove = []
        for fid, f in self.active_faults.items():
            if target_node is None or f["target_node"] == target_node:
                f["is_active"] = False
                f["resolved_at"] = time.time()
                to_remove.append(fid)
                cleared_count += 1
                
                # Reset satellite to HEALTHY if stopped
                reg = self.registry.lookup(f["target_node"])
                if reg:
                    reg.status = "HEALTHY"
                    reg.health_score = 100.0
                    reg.last_heartbeat = time.time()

        for fid in to_remove:
            del self.active_faults[fid]

        logger.info(f"[FAULT CLEAR APPLIED] Target={target_node or 'ALL_NODES'} | ClearedCount={cleared_count}")
        return cleared_count

    def get_node_faults(self, node_id: str) -> List[Dict[str, Any]]:
        return [f for f in self.active_faults.values() if f["target_node"] == node_id and f["is_active"]]

    def get_all_active_faults(self) -> List[Dict[str, Any]]:
        return list(self.active_faults.values())

    def get_history(self) -> List[Dict[str, Any]]:
        return self.fault_history
