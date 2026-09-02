from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class RegistrationRequest(BaseModel):
    satellite_id: str
    node_id: str
    hostname: str
    address: str
    grpc_port: int
    p2p_port: int
    capabilities: Optional[List[str]] = None

class HeartbeatRequest(BaseModel):
    satellite_id: str
    battery: float = 100.0
    temperature: float = 25.0
    cpu_usage: float = 15.0
    memory_usage: float = 30.0
    signal_strength: float = 95.0
    node_id: Optional[str] = None
    address: Optional[str] = None
    grpc_port: Optional[int] = None
    p2p_port: Optional[int] = None

class RPCInvokeRequest(BaseModel):
    target_satellite_id: str
    method: str  # GetHealth, Ping, GetSatelliteInfo, ExecuteCommand
    payload: Optional[Dict[str, Any]] = None
    timeout: float = 3.0

class P2PSendRequest(BaseModel):
    source_satellite_id: str
    destination_satellite_id: str
    message_type: str = "TELEMETRY_SYNC"
    payload: str
    ttl: int = 5

class FaultInjectRequest(BaseModel):
    fault_type: str  # STOP_NODE, RESTART_NODE, HIGH_LATENCY, PACKET_LOSS, TEMP_SPIKE, BATTERY_DRAIN, CPU_OVERLOAD
    target_node: str
    parameters: Optional[Dict[str, Any]] = None

class WebRTCOfferRequest(BaseModel):
    offer_sdp: str
    peer: str = "SAT-02"

class WebRTCICECandidateRequest(BaseModel):
    session_id: str
    candidate: Dict[str, Any]
