# System Architecture & Technical Design

A comprehensive architectural document detailing the multi-service design, message routing, data persistence, and software engineering patterns powering the **Distributed Satellite Monitoring & Mission Control System**.

---

## 1. Architectural Overview

The system is architected as a set of autonomous containerized microservices operating over a virtualized bridge network. It consists of:
- **1 Mission Control Orchestrator**: FastAPI application hosting the dynamic Service Registry, Health Engine, Fault Simulator, gRPC manager, RabbitMQ consumer, WebSocket stream broadcaster, and database ORM.
- **5 Satellite Microservice Nodes (`SAT-01` to `SAT-05`)**: Autonomous Python processes executing independent telemetry steps, issuing periodic heartbeats, running gRPC servers, and handling direct peer-to-peer (P2P) cross-links.
- **1 Real-Time Frontend Observability UI**: React 18 / Vite single-page application consuming REST endpoints and WebSocket events.
- **2 Supporting Infrastructure Services**: PostgreSQL database for event persistence and RabbitMQ message broker for asynchronous telemetry queue management.

---

## 2. Problem-to-Architecture Mapping

| Distributed System Problem | Architectural Solution | Implementation Component | Source File Reference |
| :--- | :--- | :--- | :--- |
| **Independent Satellite Autonomy** | Autonomous microservice processes | `SatelliteNode` | [`satellites/satellite_node.py`](../satellites/satellite_node.py) |
| **Dynamic Service Discovery** | In-memory dynamic registry | `SatelliteRegistry` | [`backend/registry/service_registry.py`](../backend/registry/service_registry.py) |
| **Liveness & Crash Detection** | Heartbeat sweeper (10.0s TTL) | `heartbeat_sweeper_task()` | [`backend/main.py`](../backend/main.py#L34-L53) |
| **Multi-Metric Health Evaluation** | Weighted telemetry scoring algorithm | `HealthEngine` | [`backend/services/health_engine.py`](../backend/services/health_engine.py) |
| **Control Action Remote Invocations** | Binary Protocol Buffers over gRPC | `GRPCClientManager` | [`backend/communication/grpc_client.py`](../backend/communication/grpc_client.py) |
| **Asynchronous Telemetry Ingestion** | RabbitMQ AMQP message broker | `RabbitMQManager` | [`backend/communication/rabbitmq_manager.py`](../backend/communication/rabbitmq_manager.py) |
| **Live UI Telemetry Streaming** | WebSocket broadcast manager | `ConnectionManager` | [`backend/communication/websocket_manager.py`](../backend/communication/websocket_manager.py) |
| **Inter-Satellite Cross-Links** | Direct P2P HTTP/TCP messaging | `send_to_peer` trigger | [`satellites/satellite_node.py`](../satellites/satellite_node.py#L225-L260) |
| **Distributed Consensus / Coordination** | Ring Leader Election algorithm | `run_ring_election()` | [`backend/registry/service_registry.py`](../backend/registry/service_registry.py#L140-L195) |
| **Environment Isolation** | Docker Compose multi-container setup | 9 Docker services | [`docker-compose.yml`](../docker-compose.yml) |

---

## 3. High-Level Architecture Diagram

```mermaid
graph TD
    UI["React Frontend UI<br/>(Port 3000)"]
    MC["FastAPI Mission Control<br/>(Port 8000)"]
    REG["ServiceRegistry<br/>(Global Memory)"]
    HE["HealthEngine"]
    FS["FaultSimulator"]
    WS["WebSocket Manager"]
    DB[(PostgreSQL 15<br/>Port 5432)]
    RMQ[("RabbitMQ 3.9<br/>Port 5672")]
    
    SAT1["Satellite 01<br/>gRPC:5001 | P2P:6001"]
    SAT2["Satellite 02<br/>gRPC:5002 | P2P:6002"]
    SAT3["Satellite 03<br/>gRPC:5003 | P2P:6003"]
    SAT4["Satellite 04<br/>gRPC:5004 | P2P:6004"]
    SAT5["Satellite 05<br/>gRPC:5005 | P2P:6005"]

    UI <-->|HTTP REST & WS /ws| MC
    MC <--> REG
    MC --> HE
    MC --> FS
    MC --> WS
    MC <-->|AsyncPG ORM| DB
    MC <-->|AMQP Bus| RMQ

    SAT1 -->|POST /register & /heartbeat| MC
    SAT2 -->|POST /register & /heartbeat| MC
    SAT3 -->|POST /register & /heartbeat| MC
    SAT4 -->|POST /register & /heartbeat| MC
    SAT5 -->|POST /register & /heartbeat| MC

    MC <-->|gRPC Unary RPCs| SAT1
    MC <-->|gRPC Unary RPCs| SAT2
    MC <-->|gRPC Unary RPCs| SAT3
    MC <-->|gRPC Unary RPCs| SAT4
    MC <-->|gRPC Unary RPCs| SAT5

    SAT1 <==>|Direct P2P Link| SAT2
    SAT2 <==>|Direct P2P Link| SAT3
    SAT3 <==>|Direct P2P Link| SAT4
    SAT4 <==>|Direct P2P Link| SAT5
    SAT5 <==>|Direct P2P Link| SAT1
```

---

## 4. Distributed Nodes Description

### Mission Control Backend (`mission-control-backend`)
- **Host**: `mission-control:8000` (Docker container name)
- **Role**: Coordinates constellation liveness, processes heartbeats, exposes REST endpoints, manages WebSockets broadcasts, persists logs to PostgreSQL, and ingests RabbitMQ telemetry messages.

### Satellite Microservice Nodes (`satellite-01` .. `satellite-05`)
- **Containers**: `satellite-01`, `satellite-02`, `satellite-03`, `satellite-04`, `satellite-05`
- **Network Ports**:
  - `SAT-01`: gRPC `5001`, P2P `6001`
  - `SAT-02`: gRPC `5002`, P2P `6002`
  - `SAT-03`: gRPC `5003`, P2P `6003`
  - `SAT-04`: gRPC `5004`, P2P `6004`
  - `SAT-05`: gRPC `5005`, P2P `6005`
- **Responsibilities**:
  1. Execute local telemetry stepping algorithm every 2 seconds.
  2. Issue HTTP registration and heartbeat requests to Mission Control.
  3. Host async gRPC servicer implementing `proto/satellite.proto`.
  4. Host async HTTP P2P listener for direct peer communication.

---

## 5. Frontend Architecture

The frontend is built using React 18 and Vite, structured into modular pages:
- **`MissionOverview.jsx`**: Summary metrics, healthy satellite counters, and live constellation node table.
- **`SatelliteRegistryPage.jsx`**: Dynamic discovery lookup table displaying hostnames, ports, and capabilities.
- **`LiveTelemetryPage.jsx`**: Recharts time-series line charts for Battery, Temperature, CPU, and Health Score metrics.
- **`CommunicationObservatory.jsx`**: Multi-protocol evidence inspector for gRPC, RabbitMQ, WebSockets, P2P, and WebRTC.
- **`ConstellationMap.jsx`**: Visual orbital topology canvas highlighting active nodes and P2P links.
- **`FaultSimulatorPage.jsx`**: Fault injection triggers and active fault management table.
- **`App.jsx`**: Top-level router, central WebSocket listener, and rolling telemetry history accumulator.

---

## 6. Backend Architecture

The backend is built with FastAPI and Uvicorn, structured as follows:
- **`backend/main.py`**: Lifespan initializer, route definitions, and background sweeper task.
- **`backend/registry/service_registry.py`**: In-memory `SatelliteRegistry` data structure and `run_ring_election()`.
- **`backend/services/health_engine.py`**: Pure functional metric scorer (`calculate_health()`).
- **`backend/communication/grpc_client.py`**: Async gRPC client wrapper invoking `SatelliteService` RPC methods.
- **`backend/communication/rabbitmq_manager.py`**: Async AMQP client managing connection, exchange declaration, and message listening.
- **`backend/communication/websocket_manager.py`**: Thread-safe WebSocket connection pool (`ConnectionManager`).
- **`backend/faults/fault_simulator.py`**: In-memory fault state tracker (`FaultSimulator`).
- **`backend/database/`**: SQLAlchemy async session manager and PostgreSQL models.

---

## 7. Satellite Node Lifecycle

```mermaid
stateDiagram-v2
    [*] --> STARTUP: Container Boot
    STARTUP --> REGISTERING: Read ENV (SAT_ID, GRPC_PORT, P2P_PORT)
    REGISTERING --> REGISTERING: POST /api/satellites/register Failed (Retry Loop)
    REGISTERING --> AUTONOMOUS_LOOP: Registration Success (200 OK)
    
    state AUTONOMOUS_LOOP {
        [*] --> STEP_TELEMETRY: Update Battery, Temp, CPU
        STEP_TELEMETRY --> SEND_HEARTBEAT: POST /api/satellites/heartbeat
        SEND_HEARTBEAT --> SLEEP: Wait 2.0s
        SLEEP --> STEP_TELEMETRY
    }

    AUTONOMOUS_LOOP --> OFFLINE: Container Stopped / Killed
    OFFLINE --> REGISTERING: Container Restarted
```

---

## 8. Database Architecture

Persistent storage is managed by PostgreSQL 15 via SQLAlchemy async ORM (`backend/database/models.py`):
1. **`SatelliteModel` (`satellites`)**: Persistent snapshot of satellite registration state and telemetry.
2. **`TelemetryLog` (`telemetry_logs`)**: Time-series log of satellite metric samples.
3. **`CommunicationEvent` (`communication_events`)**: Audit log for RPCs, RabbitMQ messages, P2P transfers, and election events.
4. **`FaultInjectionLog` (`fault_logs`)**: Historical record of injected fault events.
5. **`ConceptEvidence` (`concept_evidences`)**: Audit trail mapping executed operations to syllabus topics.

---

## 9. End-to-End Data Flow

```mermaid
sequenceDiagram
    autonumber
    participant SAT as Satellite Process (SAT-01)
    participant MC as Mission Control Backend
    participant REG as ServiceRegistry
    participant WS as WebSocket Manager
    participant UI as React Frontend UI

    SAT->>MC: POST /api/satellites/register (JSON Payload)
    MC->>REG: register(satellite_id, address, ports)
    REG-->>MC: SatelliteRegistration object
    MC->>WS: broadcast({"event_type": "NODE_REGISTERED"})
    WS-->>UI: WebSocket event push
    UI->>UI: Update Satellite Registry Table

    loop Every 2.0 Seconds
        SAT->>MC: POST /api/satellites/heartbeat (Telemetry Data)
        MC->>REG: update_heartbeat(battery, temp, cpu)
        REG-->>MC: Updated registration state & Health score
        MC->>WS: broadcast({"event_type": "TELEMETRY_UPDATED"})
        WS-->>UI: Live telemetry metrics push
        UI->>UI: Update Recharts Line Graphs & Overview Metrics
    end
```

---

## 10. Failure and Recovery Flow

```mermaid
sequenceDiagram
    autonumber
    participant SAT2 as Satellite Container (SAT-02)
    participant MC as Mission Control Sweeper
    participant REG as ServiceRegistry
    participant WS as WebSocket Manager
    participant UI as React Frontend UI

    SAT2->>MC: Heartbeat streaming...
    Note over SAT2: User executes: docker compose stop satellite-02
    SAT2--xMC: Heartbeats halt
    
    loop Every 3.0 Seconds Sweeper Check
        MC->>REG: sweep_failures()
        Note over REG: Check time.time() - last_heartbeat > 10.0s
        REG-->>MC: SAT-02 marked OFFLINE (Health 0.0%)
    end

    MC->>WS: broadcast({"event_type": "NODE_DISCONNECTED", "satellite_id": "SAT-02"})
    WS-->>UI: Event push: SAT-02 OFFLINE
    UI->>UI: Mark SAT-02 Red (4/5 Active, System DEGRADED)

    Note over SAT2: User executes: docker compose start satellite-02
    SAT2->>MC: POST /api/satellites/register
    SAT2->>MC: POST /api/satellites/heartbeat
    MC->>REG: update_heartbeat(is_online=True)
    REG-->>MC: SAT-02 marked HEALTHY
    MC->>WS: broadcast({"event_type": "TELEMETRY_UPDATED"})
    WS-->>UI: Event push: SAT-02 HEALTHY (5/5 Active)
```

---

## 11. Component-to-File Mapping

| Architectural Component | Class / Function | Source File Path | Primary Responsibility |
| :--- | :--- | :--- | :--- |
| **Mission Control API** | `FastAPI()` application | [`backend/main.py`](../backend/main.py) | Lifespan, REST endpoints, WebSocket endpoint `/ws` |
| **Service Registry** | `SatelliteRegistry` | [`backend/registry/service_registry.py`](../backend/registry/service_registry.py) | Endpoint lookup, TTL failure sweep, Ring election |
| **Health Engine** | `HealthEngine` | [`backend/services/health_engine.py`](../backend/services/health_engine.py) | Weighted 0-100% health calculation formula |
| **Fault Simulator** | `FaultSimulator` | [`backend/faults/fault_simulator.py`](../backend/faults/fault_simulator.py) | Anomaly injection and fault state management |
| **gRPC Client Manager** | `GRPCClientManager` | [`backend/communication/grpc_client.py`](../backend/communication/grpc_client.py) | Async gRPC stubs for satellite RPC invocations |
| **RabbitMQ Manager** | `RabbitMQManager` | [`backend/communication/rabbitmq_manager.py`](../backend/communication/rabbitmq_manager.py) | AMQP connection, exchange binding, message listener |
| **WebSocket Manager** | `ConnectionManager` | [`backend/communication/websocket_manager.py`](../backend/communication/websocket_manager.py) | WebSocket connection pooling and event broadcasting |
| **WebRTC Manager** | `WebRTCManager` | [`backend/communication/webrtc_signaling.py`](../backend/communication/webrtc_signaling.py) | SDP offer/answer processing and ICE candidate handling |
| **Satellite Microservice** | `SatelliteNode` | [`satellites/satellite_node.py`](../satellites/satellite_node.py) | Independent satellite logic, heartbeats, gRPC server |
| **Protobuf Contract** | `SatelliteService` | [`proto/satellite.proto`](../proto/satellite.proto) | gRPC message definitions and RPC service interface |
| **Database ORM** | `Base` models | [`backend/database/models.py`](../backend/database/models.py) | PostgreSQL schema definitions for audit logging |
