import time
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, BigInteger
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class SatelliteModel(Base):
    __tablename__ = "satellites"
    
    satellite_id = Column(String(50), primary_key=True)
    node_id = Column(String(50), nullable=False)
    hostname = Column(String(100), nullable=False)
    address = Column(String(100), nullable=False)
    grpc_port = Column(Integer, nullable=False)
    p2p_port = Column(Integer, nullable=False)
    status = Column(String(20), default="HEALTHY")
    health_score = Column(Float, default=100.0)
    battery = Column(Float, default=100.0)
    temperature = Column(Float, default=25.0)
    cpu_usage = Column(Float, default=15.0)
    memory_usage = Column(Float, default=30.0)
    signal_strength = Column(Float, default=95.0)
    last_heartbeat = Column(Float, default=time.time)
    registered_at = Column(Float, default=time.time)

class TelemetryLog(Base):
    __tablename__ = "telemetry_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    satellite_id = Column(String(50), nullable=False, index=True)
    sequence_number = Column(BigInteger, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    altitude_km = Column(Float, nullable=False)
    battery = Column(Float, nullable=False)
    temperature = Column(Float, nullable=False)
    cpu_usage = Column(Float, nullable=False)
    memory_usage = Column(Float, nullable=False)
    signal_strength = Column(Float, nullable=False)
    health_score = Column(Float, nullable=False)
    status = Column(String(20), nullable=False)
    timestamp = Column(Float, default=time.time, index=True)

class CommunicationEvent(Base):
    __tablename__ = "communication_events"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String(100), unique=True, nullable=False)
    source = Column(String(50), nullable=False)
    destination = Column(String(50), nullable=False)
    protocol = Column(String(30), nullable=False) # gRPC, RabbitMQ, WebSocket, P2P, WebRTC
    method = Column(String(50), nullable=True)
    latency_ms = Column(Float, default=0.0)
    status = Column(String(20), default="SUCCESS")
    payload_summary = Column(Text, nullable=True)
    timestamp = Column(Float, default=time.time, index=True)

class FaultInjectionLog(Base):
    __tablename__ = "fault_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    fault_type = Column(String(50), nullable=False) # STOP, DISCONNECT, LATENCY, PACKET_LOSS, TEMP_SPIKE, BATTERY_DROP, CPU_OVERLOAD
    target_node = Column(String(50), nullable=False)
    parameters = Column(Text, nullable=True)
    applied_at = Column(Float, default=time.time)
    resolved_at = Column(Float, nullable=True)
    is_active = Column(Boolean, default=True)

class ConceptEvidence(Base):
    __tablename__ = "concept_evidences"
    
    concept_id = Column(String(50), primary_key=True) # e.g. RPC, P2P, MIDDLEWARE
    unit = Column(String(20), nullable=False) # UNIT_1, UNIT_2
    concept_name = Column(String(100), nullable=False)
    technology_used = Column(String(100), nullable=False)
    last_evidence_summary = Column(Text, nullable=True)
    last_triggered_at = Column(Float, default=time.time)

class MissionModel(Base):
    __tablename__ = "missions"

    mission_id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(30), default="ACTIVE") # ACTIVE, COMPLETED, DEGRADED
    created_at = Column(Float, default=time.time)

class MissionTaskModel(Base):
    __tablename__ = "mission_tasks"

    task_id = Column(String(50), primary_key=True)
    mission_id = Column(String(50), nullable=False, index=True)
    task_type = Column(String(50), nullable=False) # EARTH_OBSERVATION, THERMAL_MAP, DATA_RELAY, COMPUTE_ANALYTICS
    description = Column(Text, nullable=True)
    priority = Column(String(20), default="MEDIUM") # HIGH, MEDIUM, LOW
    deadline = Column(Float, nullable=True)
    required_capabilities = Column(Text, nullable=False) # JSON array e.g. ["CAMERA", "COMPUTE"]
    current_owner = Column(String(50), nullable=True)
    previous_owner = Column(String(50), nullable=True)
    status = Column(String(30), default="RUNNING") # CREATED, RUNNING, PAUSED, AFFECTED, REASSIGNED, COMPLETED
    lamport_timestamp = Column(BigInteger, default=0)
    vector_clock = Column(Text, nullable=True) # JSON dict e.g. {"SAT-01": 1, ...}
    created_at = Column(Float, default=time.time)
    updated_at = Column(Float, default=time.time)

class SnapshotModel(Base):
    __tablename__ = "snapshots"

    snapshot_id = Column(String(50), primary_key=True)
    initiator = Column(String(50), nullable=False)
    global_state_json = Column(Text, nullable=False)
    channel_state_json = Column(Text, nullable=True)
    in_transit_messages_json = Column(Text, nullable=True)
    timestamp = Column(Float, default=time.time, index=True)

class IncidentModel(Base):
    __tablename__ = "incidents"

    incident_id = Column(String(50), primary_key=True)
    title = Column(String(100), nullable=False)
    severity = Column(String(20), default="HIGH") # HIGH, CRITICAL, MEDIUM, LOW
    cause_node = Column(String(50), nullable=False)
    affected_tasks_json = Column(Text, nullable=True)
    recovery_status = Column(String(30), default="RECOVERED")
    recovery_duration_ms = Column(Float, default=0.0)
    event_timeline_json = Column(Text, nullable=False)
    created_at = Column(Float, default=time.time, index=True)

class ExperimentModel(Base):
    __tablename__ = "experiments"

    experiment_id = Column(String(50), primary_key=True)
    title = Column(String(100), nullable=False)
    scenario = Column(String(50), nullable=False)
    parameters_json = Column(Text, nullable=False)
    results_json = Column(Text, nullable=False)
    metrics_json = Column(Text, nullable=False)
    created_at = Column(Float, default=time.time, index=True)

