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

class TelemetryObservation(BaseModel):
    """Validated measurement payload; absent readings must never become synthetic values."""
    satellite_id: str = Field(..., min_length=1, max_length=64)
    battery: float = Field(..., ge=0, le=100)
    temperature: float = Field(..., ge=-100, le=200)
    cpu_usage: float = Field(..., ge=0, le=100)
    memory_usage: float = Field(..., ge=0, le=100)
    signal_strength: float = Field(..., ge=0, le=100)
    timestamp: Optional[float] = None
    sequence_number: Optional[int] = Field(None, ge=0)


class HeartbeatRequest(BaseModel):
    satellite_id: str = Field(..., min_length=1, max_length=64)
    battery: float = Field(..., ge=0, le=100)
    temperature: float = Field(..., ge=-100, le=200)
    cpu_usage: float = Field(..., ge=0, le=100)
    memory_usage: float = Field(..., ge=0, le=100)
    signal_strength: float = Field(..., ge=0, le=100)
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
