import time
import asyncio
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class SatelliteRegistration:
    satellite_id: str
    node_id: str
    hostname: str
    address: str
    grpc_port: int
    p2p_port: int
    status: str
    capabilities: List[str]
    last_heartbeat: float
    registered_at: float
    health_score: float = 100.0
    battery: float = 100.0
    temperature: float = 25.0
    cpu_usage: float = 15.0
    memory_usage: float = 30.0
    signal_strength: float = 95.0
    suspected_timestamp: Optional[float] = None
    disconnected_timestamp: Optional[float] = None
    failure_timestamp: Optional[float] = None
    recovery_timestamp: Optional[float] = None
    detection_latency_ms: float = 0.0
    recovery_time_ms: float = 0.0
    failure_source: str = "SYSTEM"
    partition_group: Optional[str] = None
    last_correlation_id: Optional[str] = None

class SatelliteRegistry:
    def __init__(self, heartbeat_ttl_seconds: float = 10.0):
        self._registry: Dict[str, SatelliteRegistration] = {}
        self.ttl = heartbeat_ttl_seconds
        self._event_listeners = []
        self.current_leader: str = "SAT-05"
        self.active_partitions: Dict[str, List[str]] = {} # e.g. {"Partition A": ["SAT-01", "SAT-02"], ...}

    def register(
        self,
        satellite_id: str,
        node_id: str,
        hostname: str,
        address: str,
        grpc_port: int,
        p2p_port: int,
        capabilities: Optional[List[str]] = None
    ) -> SatelliteRegistration:
        now = time.time()
        reg = SatelliteRegistration(
            satellite_id=satellite_id,
            node_id=node_id,
            hostname=hostname,
            address=address,
            grpc_port=grpc_port,
            p2p_port=p2p_port,
            status="HEALTHY",
            capabilities=capabilities or ["TELEMETRY", "gRPC", "P2P", "RABBITMQ", "WEBRTC"],
            last_heartbeat=now,
            registered_at=now
        )
        self._registry[satellite_id] = reg
        return reg

    def update_heartbeat(
        self,
        satellite_id: str,
        health_score: float = 100.0,
        status: str = "HEALTHY",
        battery: float = 100.0,
        temperature: float = 25.0,
        cpu_usage: float = 15.0,
        memory_usage: float = 30.0,
        signal_strength: float = 95.0,
        node_id: Optional[str] = None,
        address: Optional[str] = None,
        grpc_port: Optional[int] = None,
        p2p_port: Optional[int] = None
    ) -> SatelliteRegistration:
        now = time.time()
        if satellite_id not in self._registry:
            num_suffix = satellite_id.split("-")[-1] if "-" in satellite_id else "01"
            try:
                idx = int(num_suffix)
            except ValueError:
                idx = 1

            self.register(
                satellite_id=satellite_id,
                node_id=node_id or f"NODE-{satellite_id}",
                hostname=f"{satellite_id.lower()}.orbital.local",
                address=address or satellite_id.lower(),
                grpc_port=grpc_port or (5000 + idx),
                p2p_port=p2p_port or (6000 + idx)
            )

        reg = self._registry[satellite_id]
        
        # Check recovery transition
        if reg.status in ["SUSPECTED", "DISCONNECTED", "OFFLINE"]:
            reg.recovery_timestamp = now
            if reg.failure_timestamp:
                reg.recovery_time_ms = round((now - reg.failure_timestamp) * 1000, 2)
            else:
                reg.recovery_time_ms = round((now - reg.last_heartbeat) * 1000, 2)
            logger.info(f"[REGISTRY RECOVERY] Satellite {satellite_id} recovered from {reg.status} -> HEALTHY | recovery_time={reg.recovery_time_ms}ms")
            reg.status = "HEALTHY"
        elif reg.status not in ["SUSPECTED", "DISCONNECTED", "OFFLINE"]:
            reg.status = status

        reg.last_heartbeat = now
        reg.health_score = health_score
        reg.battery = battery
        reg.temperature = temperature
        reg.cpu_usage = cpu_usage
        reg.memory_usage = memory_usage
        reg.signal_strength = signal_strength
        if address:
            reg.address = address
        if grpc_port:
            reg.grpc_port = grpc_port
        if p2p_port:
            reg.p2p_port = p2p_port

        return reg

    def set_status(self, satellite_id: str, status: str, source: str = "SYSTEM") -> bool:
        if satellite_id in self._registry:
            reg = self._registry[satellite_id]
            reg.status = status
            reg.failure_source = source
            if status in ["SUSPECTED", "DISCONNECTED", "OFFLINE"]:
                now = time.time()
                if not reg.failure_timestamp:
                    reg.failure_timestamp = now
            return True
        return False

    def lookup(self, satellite_id: str) -> Optional[SatelliteRegistration]:
        return self._registry.get(satellite_id)

    def list_all(self) -> List[SatelliteRegistration]:
        return list(self._registry.values())

    def sweep_failures(self) -> Dict[str, List[str]]:
        """
        Multistage failure sweeper:
        - 5s < heartbeat age <= 10s -> SUSPECTED
        - heartbeat age > 10s -> DISCONNECTED
        """
        now = time.time()
        suspected_satellites = []
        disconnected_satellites = []

        for sat_id, reg in self._registry.items():
            age = now - reg.last_heartbeat
            if age > 5.0 and age <= self.ttl and reg.status not in ["SUSPECTED", "DISCONNECTED", "OFFLINE"]:
                reg.status = "SUSPECTED"
                reg.suspected_timestamp = now
                reg.failure_timestamp = reg.last_heartbeat
                reg.detection_latency_ms = round((now - reg.last_heartbeat) * 1000, 2)
                suspected_satellites.append(sat_id)
                logger.warning(f"[FAILURE DETECTOR] Satellite {sat_id} heartbeat delayed ({age:.1f}s) -> Marked SUSPECTED")
            elif age > self.ttl and reg.status != "DISCONNECTED" and reg.status != "OFFLINE":
                reg.status = "DISCONNECTED"
                reg.disconnected_timestamp = now
                if not reg.failure_timestamp:
                    reg.failure_timestamp = reg.last_heartbeat
                reg.health_score = 0.0
                reg.detection_latency_ms = round((now - reg.last_heartbeat) * 1000, 2)
                disconnected_satellites.append(sat_id)
                logger.warning(f"[FAILURE DETECTOR] Satellite {sat_id} heartbeat lost ({age:.1f}s) -> Marked DISCONNECTED")

        return {
            "suspected": suspected_satellites,
            "disconnected": disconnected_satellites
        }

    def to_dict_list(self) -> List[Dict[str, Any]]:
        now = time.time()
        res = []
        for reg in self._registry.values():
            d = asdict(reg)
            d["seconds_since_heartbeat"] = round(now - reg.last_heartbeat, 2)
            res.append(d)
        return res

    def run_ring_election(self, initiator_id: str = "SAT-01") -> Dict[str, Any]:
        start_time = time.time()
        all_ring_nodes = ["SAT-01", "SAT-02", "SAT-03", "SAT-04", "SAT-05"]
        
        if initiator_id not in all_ring_nodes:
            initiator_id = "SAT-01"

        start_idx = all_ring_nodes.index(initiator_id)
        ordered_ring = all_ring_nodes[start_idx:] + all_ring_nodes[:start_idx]

        logger.info(f"[RING ELECTION] Election initiated by {initiator_id} | Logical ring path: {' -> '.join(ordered_ring)}")

        visited_active = []
        bypassed_failed = []
        election_trace = []

        for node_id in ordered_ring:
            reg = self._registry.get(node_id)
            is_active = reg and reg.status != "OFFLINE"
            
            if is_active:
                visited_active.append(node_id)
                election_trace.append({
                    "step": len(election_trace) + 1,
                    "from_node": visited_active[-2] if len(visited_active) > 1 else initiator_id,
                    "to_node": node_id,
                    "action": "PASSED_ELECTION_MSG",
                    "highest_candidate": max(visited_active),
                    "timestamp": round(time.time(), 3)
                })
            else:
                bypassed_failed.append(node_id)
                election_trace.append({
                    "step": len(election_trace) + 1,
                    "node": node_id,
                    "action": "NODE_OFFLINE_BYPASSED",
                    "timestamp": round(time.time(), 3)
                })

        winner = max(visited_active) if visited_active else "NONE"
        self.current_leader = winner
        duration_ms = round((time.time() - start_time) * 1000, 2)
        event_id = f"EVT-ELECT-{int(time.time() * 1000)}"

        logger.info(f"[RING ELECTION COMPLETED] Winner Leader={winner} | Participated={visited_active} | Bypassed Offline={bypassed_failed} | Latency={duration_ms}ms")

        return {
            "event_id": event_id,
            "status": "SUCCESS",
            "protocol": "Ring Leader Election (Highest ID Wins)",
            "initiator": initiator_id,
            "current_leader": winner,
            "ring_topology": "SAT-01 -> SAT-02 -> SAT-03 -> SAT-04 -> SAT-05 -> SAT-01",
            "ring_path": ordered_ring,
            "participating_nodes": visited_active,
            "failed_nodes": bypassed_failed,
            "election_trace": election_trace,
            "latency_ms": duration_ms,
            "timestamp": time.time()
        }

global_registry = SatelliteRegistry()
