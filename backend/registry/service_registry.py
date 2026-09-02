import time
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

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

class SatelliteRegistry:
    def __init__(self, heartbeat_ttl_seconds: float = 10.0):
        self._registry: Dict[str, SatelliteRegistration] = {}
        self.ttl = heartbeat_ttl_seconds
        self._event_listeners = []

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
            # Auto-register node if heartbeat arrives prior to explicit registration
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
        reg.last_heartbeat = now
        reg.health_score = health_score
        reg.status = status if reg.status != "OFFLINE" else ("HEALTHY" if health_score >= 90 else status)
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

    def set_status(self, satellite_id: str, status: str) -> bool:
        if satellite_id in self._registry:
            self._registry[satellite_id].status = status
            return True
        return False

    def lookup(self, satellite_id: str) -> Optional[SatelliteRegistration]:
        return self._registry.get(satellite_id)

    def list_all(self) -> List[SatelliteRegistration]:
        return list(self._registry.values())

    def sweep_failures(self) -> List[str]:
        now = time.time()
        failed_satellites = []
        for sat_id, reg in self._registry.items():
            if reg.status != "OFFLINE" and (now - reg.last_heartbeat) > self.ttl:
                reg.status = "OFFLINE"
                reg.health_score = 0.0
                failed_satellites.append(sat_id)
        return failed_satellites

    def to_dict_list(self) -> List[Dict[str, Any]]:
        now = time.time()
        res = []
        for reg in self._registry.values():
            d = asdict(reg)
            d["seconds_since_heartbeat"] = round(now - reg.last_heartbeat, 2)
            res.append(d)
        return res

global_registry = SatelliteRegistry()
