import time
import logging
from typing import Dict, Any, List, Optional
from backend.services.event_manager import generate_correlation_id

logger = logging.getLogger(__name__)

class FaultSimulator:
    """
    Simulates distributed design issues & faults:
    - Node stopping / crash / restart
    - Network latency injection
    - Packet / message loss simulation
    - Metric spikes (Temperature, Battery drain, CPU overload)
    - Network Partition simulation & State Reconciliation
    """
    def __init__(self, registry):
        self.registry = registry
        self.active_faults: Dict[str, Dict[str, Any]] = {}
        self.fault_history: List[Dict[str, Any]] = []
        self.partitions: Dict[str, List[str]] = {} # e.g. {"Partition A": ["SAT-01", "SAT-02"], "Partition B": ["SAT-03", "SAT-04", "SAT-05"]}

    def inject_fault(
        self,
        fault_type: str,
        target_node: str,
        parameters: Optional[Dict[str, Any]] = None,
        source: str = "FRONTEND"
    ) -> Dict[str, Any]:
        cid = generate_correlation_id("EVT-FLT")
        fault_id = f"fault-{fault_type.lower()}-{target_node.lower()}-{int(time.time())}"
        params = parameters or {}
        
        fault_record = {
            "fault_id": fault_id,
            "correlation_id": cid,
            "fault_type": fault_type,
            "target_node": target_node,
            "parameters": params,
            "source": source,
            "applied_at": time.time(),
            "is_active": True
        }

        self.active_faults[fault_id] = fault_record
        self.fault_history.append(fault_record)

        # Apply specific fault mechanics
        reg = self.registry.lookup(target_node)
        if fault_type in ["STOP_NODE", "STOP"]:
            self.registry.set_status(target_node, "DISCONNECTED", source=source)
            if reg:
                reg.health_score = 0.0
                reg.failure_timestamp = time.time()
                reg.failure_source = source
        elif fault_type in ["RESTART_NODE", "RESTART"]:
            self.registry.set_status(target_node, "HEALTHY", source=source)
            if reg:
                reg.last_heartbeat = time.time()
                reg.health_score = 100.0
                reg.battery = 100.0
                reg.temperature = 25.0
                reg.cpu_usage = 15.0
                reg.recovery_timestamp = time.time()
        elif fault_type == "HIGH_LATENCY":
            latency_ms = float(params.get("latency_ms", 500))
            fault_record["latency_ms"] = latency_ms
        elif fault_type == "PACKET_LOSS":
            loss_pct = float(params.get("loss_pct", 20.0))
            fault_record["loss_pct"] = loss_pct
        elif fault_type in ["TEMP_SPIKE", "HIGH_TEMP"]:
            if reg:
                reg.temperature = float(params.get("temperature", 85.0))
                reg.health_score = 45.0
                reg.status = "CRITICAL"
        elif fault_type in ["BATTERY_DRAIN", "LOW_BATTERY"]:
            if reg:
                reg.battery = float(params.get("battery", 15.0))
                reg.health_score = 30.0
                reg.status = "CRITICAL"
        elif fault_type == "CPU_OVERLOAD":
            if reg:
                reg.cpu_usage = float(params.get("cpu_usage", 98.0))
                reg.health_score = 65.0
                reg.status = "WARNING"
        elif fault_type == "NETWORK_PARTITION":
            part_a = params.get("partition_a", ["SAT-01", "SAT-02", "SAT-03"])
            part_b = params.get("partition_b", ["SAT-04", "SAT-05"])
            self.partitions = {
                "Partition A": part_a,
                "Partition B": part_b
            }
            logger.info(f"[NETWORK PARTITION CREATED] Partition A={part_a} | Partition B={part_b}")

        logger.info(f"[FAULT APPLIED] CID={cid} | Source={source} | Target={target_node} | Fault={fault_type} | Params={params}")
        return fault_record

    def is_partition_blocked(self, source_node: str, dest_node: str) -> bool:
        if not self.partitions:
            return False
        
        source_group = None
        dest_group = None
        for group_name, members in self.partitions.items():
            if source_node in members:
                source_group = group_name
            if dest_node in members:
                dest_group = group_name

        if source_group and dest_group and source_group != dest_group:
            logger.warning(f"[PARTITION BLOCKED] Message from {source_node} ({source_group}) to {dest_node} ({dest_group}) BLOCKED by Network Partition")
            return True
        return False

    def clear_partition(self) -> Dict[str, Any]:
        cid = generate_correlation_id("EVT-RECONCILE")
        self.partitions.clear()
        logger.info(f"[NETWORK PARTITION RESTORED] CID={cid} | All satellite nodes reconnected. Executing deterministic state reconciliation.")
        return {
            "status": "RESTORED",
            "correlation_id": cid,
            "message": "Network partition restored. Global state reconciled across all 5 satellite nodes."
        }

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

        if target_node is None:
            self.partitions.clear()

        logger.info(f"[FAULT CLEAR APPLIED] Target={target_node or 'ALL_NODES'} | ClearedCount={cleared_count}")
        return cleared_count

    def get_node_faults(self, node_id: str) -> List[Dict[str, Any]]:
        return [f for f in self.active_faults.values() if f["target_node"] == node_id and f["is_active"]]

    def get_all_active_faults(self) -> List[Dict[str, Any]]:
        return list(self.active_faults.values())

    def get_history(self) -> List[Dict[str, Any]]:
        return self.fault_history

from backend.registry.service_registry import global_registry
global_fault_simulator = FaultSimulator(global_registry)


