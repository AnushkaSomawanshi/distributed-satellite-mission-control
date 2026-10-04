# Distributed Satellite Monitoring System — Complete Distributed Systems Architecture, Implementation & Viva Study Guide

**Project**: Distributed Satellite Monitoring & Mission Control System  
**Purpose**: Comprehensive technical study manual, system architecture guide, Distributed Systems syllabus mapping (Units 1 & 2), implementation truth matrix, demonstration execution plan, and 50+ Viva Q&A defense.  
**Source Baseline**: Actual codebase (`DS-Project` workspace)

---

## PART 1 — PROJECT OVERVIEW

### 1. What is this project?
The **Distributed Satellite Monitoring System** is a real-world, multi-node distributed application simulating an orbital constellation of autonomous satellites (`SAT-01` through `SAT-05`) monitored and controlled by a centralized Mission Control server (`mission-control-backend`) and a real-time web observability platform (`mission-control-frontend`).

### 2. What real-world problem are we solving?
In space operations, satellite constellations orbit independently in hostile environments with latency, link blackouts, power constraints, thermal spikes, and hardware degradation. Operators require:
- Real-time telemetry monitoring (battery, temperature, CPU, memory, signal strength, orbital positioning).
- Autonomous failure detection when contact is lost.
- Multi-protocol RPC and direct inter-satellite communication (gRPC and Peer-to-Peer cross-links).
- Message-oriented telemetry streaming over message queues (RabbitMQ).
- Fault tolerance and dynamic leader consensus during node outages.

### 3. Why is a distributed system suitable for this problem?
Satellites physically operate as **independent computing nodes** separated by distance. They execute local control loops, sample sensors asynchronously, communicate over high-latency or temporary radio cross-links, and cannot rely on a single monolithic shared-memory system.

### 4. What would happen if this were implemented as a single monolithic process?
If all 5 satellites and Mission Control ran inside a single Python script:
- A crash or memory leak in `SAT-02` would terminate the entire constellation.
- There would be shared memory instead of real network message passing.
- Network latency, packet loss, port binding, socket timeouts, and independent process scheduling could not be tested or demonstrated.
- It would fail as a Distributed Systems engineering demonstration.

### 5. Why are multiple satellite nodes required?
Multiple independent processes/containers (`SAT-01` to `SAT-05`) are required to demonstrate concurrent execution, dynamic service discovery, P2P direct node-to-node routing, message queue fanout, heartbeat failure detection, and Ring Leader Election.

### 6. Component Roles
- **Mission Control (`mission-control-backend`)**: Central coordinator running FastAPI (Port `8000`). Maintains the dynamic Service Registry, receives satellite heartbeats, detects node failures, invokes gRPC methods, triggers P2P links, manages WebSockets, logs communication events to PostgreSQL, and broadcasts live state updates to the UI.
- **Satellite Nodes (`SAT-01` to `SAT-05`)**: 5 autonomous Python processes running inside dedicated Docker containers (`5001`–`5005` gRPC, `6001`–`6005` P2P). Each runs an autonomous telemetry loop, auto-registers with Mission Control, sends periodic heartbeats, serves gRPC requests, handles direct P2P HTTP requests from peer satellites, and publishes telemetry to RabbitMQ.
- **Frontend (`mission-control-frontend`)**: React 18 / Vite SPA running on Port `3000`. Acts as an observability and proof layer. Connects to `/ws` for live telemetry, visualizes metrics via Recharts line charts, displays the Service Registry table, triggers RPC calls, initiates P2P packets, injects faults, and triggers Ring Leader Election.
- **PostgreSQL (`satellite-postgres`)**: Relational database (Port `5432`). Persists satellite registrations, telemetry logs, communication events, fault logs, and concept evidence audit records.
- **RabbitMQ (`satellite-rabbitmq`)**: Message broker (Ports `5672` AMQP, `15672` Management UI). Handles asynchronous telemetry message publishing and consuming via fanout exchange.
- **Docker & Docker Compose**: Containerization infrastructure. Executes 9 isolated containers on a bridge network (`satellite-net`), giving each node its own IP address, loopback interface, file system, and network stack.

---

## PART 2 — PROBLEM STATEMENT

### Academic Problem Statement
"Design, implement, containerize, and evaluate a resilient, multi-protocol Distributed Satellite Monitoring and Mission Control System capable of dynamic service discovery, multi-metric health scoring, stream-oriented telemetry broadcasting, RPC invocation, direct peer-to-peer cross-linking, message-oriented queuing, fault simulation, failure detection, and leader election across independent containerized satellite microservices."

### Proposed Solution Architecture
Our solution combines:
- **FastAPI Mission Control** coordinator.
- **5 Autonomous Satellite Nodes** (`SAT-01` to `SAT-05`).
- **Dynamic Service Registry** with heartbeat TTL sweeper.
- **Health Engine** scoring algorithm.
- **gRPC / Protocol Buffers** for synchronous RPC.
- **Direct P2P Cross-Links** for node-to-node HTTP data packets.
- **RabbitMQ AMQP Queue** for asynchronous telemetry decoupling.
- **WebSocket Broadcast Manager** for sub-second UI updates.
- **WebRTC Signaling Manager** for multimedia SDP offer/answer exchanges.
- **PostgreSQL / SQLAlchemy** for audit trail persistence.
- **Docker Compose** network orchestration across 9 services.

---

## PART 3 — PROJECT OBJECTIVES & VERIFICATION

| Objective | How the Project Achieves It | Actual Implementation |
| :--- | :--- | :--- |
| **Monitor Satellites** | Satellites transmit battery, temperature, CPU, memory, signal strength, position every 2s | `satellites/satellite_node.py` -> `backend/main.py` (`receive_heartbeat`) |
| **Discover Satellites** | Satellites auto-register with Mission Control IP/ports at boot | `backend/registry/service_registry.py` (`register`) |
| **Calculate Health** | Compute composite 0-100 score based on weighted telemetry metrics | `backend/services/health_engine.py` (`calculate_health`) |
| **Execute RPC** | Mission Control issues gRPC calls to satellite containers over gRPC channels | `backend/communication/grpc_client.py` (`invoke_rpc`) |
| **Direct P2P Link** | Source satellite sends direct HTTP packet to destination satellite without MC relay | `satellites/satellite_node.py` (`send_to_peer`) |
| **Real-time UI Stream** | Server pushes events over persistent WebSocket connection to React SPA | `backend/communication/websocket_manager.py` (`broadcast`) |
| **Failure Detection** | Background sweeper marks nodes `OFFLINE` if no heartbeat for >10s | `backend/main.py` (`heartbeat_sweeper_task`) |
| **Failure Recovery** | Restarted container auto-registers, resumes heartbeats, restores status `HEALTHY` | `satellites/satellite_node.py` (`start_autonomous_loop`) |
| **Data Persistence** | Store telemetry logs, RPC events, fault records in PostgreSQL | `backend/database/models.py` (`CommunicationEvent`, `TelemetryLog`) |
| **Ring Leader Election** | Circulate election message through active ring nodes; highest active ID wins | `backend/registry/service_registry.py` (`run_ring_election`) |
| **Fault Simulation** | Inject latency, packet loss, battery drop, thermal spike, or node stop | `backend/faults/fault_simulator.py` (`inject_fault`) |

---

## PART 4 — COMPLETE TECHNOLOGY STACK

| Technology | Category | Why Used | Where Used in Code | Port | Evidence |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **React 18** | Frontend Library | Component-driven UI for live observability | `frontend/src/App.jsx`, `pages/` | `3000` | Browser UI at `http://localhost:3000` |
| **Vite** | Build Tool | Fast HMR development and asset bundling | `frontend/vite.config.js` | `3000` | Container `mission-control-frontend` |
| **Recharts** | Data Viz | Smooth stream-oriented telemetry line graphs | `frontend/src/pages/LiveTelemetryPage.jsx` | N/A | 4 continuous line graphs |
| **Python 3.11** | Backend Core | Asynchronous async/await I/O and networking | `backend/`, `satellites/` | N/A | Container processes |
| **FastAPI** | REST Framework | High-performance async REST & WebSocket server | `backend/main.py` | `8000` | REST endpoints & `/ws` |
| **Uvicorn** | ASGI Server | Production-grade async server runner | `docker/Dockerfile.backend` | `8000` | `uvicorn backend.main:app` |
| **gRPC Async** | Synchronous RPC | High-efficiency typed binary RPC calling | `backend/communication/grpc_client.py` | `5001-5005` | Container logs `[gRPC OUT]` / `[gRPC IN]` |
| **Protobuf v3** | Serialization | Contract-first interface definition | `proto/satellite.proto` | N/A | Generated `satellite_pb2.py` |
| **HTTPX** | Async HTTP Client | Non-blocking HTTP client for P2P triggers & REST | `satellites/satellite_node.py` | `6001-6005` | Container logs `[DIRECT P2P OUTGOING]` |
| **RabbitMQ** | Message Broker | Decoupled AMQP message publish/subscribe | `backend/communication/rabbitmq_manager.py` | `5672`, `15672` | Management UI at `http://localhost:15672` |
| **WebSockets** | Real-time Push | Full-duplex persistent stream to browser | `backend/communication/websocket_manager.py` | `8000` (`/ws`) | UI status indicator `WebSocket: CONNECTED` |
| **WebRTC** | Multimedia Signaling | SDP offer/answer exchange for payload camera | `backend/communication/webrtc_signaling.py` | `8000` | `CommunicationObservatory.jsx` WebRTC tab |
| **PostgreSQL 15** | RDBMS | Persistent ACID transactional database | `backend/database/models.py` | `5432` | Container `satellite-postgres` |
| **SQLAlchemy 2.0** | Async ORM | Database abstraction and migrations | `backend/database/db.py` | N/A | Database tables in PostgreSQL |
| **Docker Compose** | Orchestration | Multi-container microservice lifecycle | `docker-compose.yml` | Various | `docker compose ps` (9 services) |

---

## PART 5 — COMPLETE REPOSITORY STRUCTURE

```
DS-Project/
├── backend/
│   ├── communication/
│   │   ├── grpc_client.py         # Outbound async gRPC client manager
│   │   ├── rabbitmq_manager.py    # AMQP producer/consumer with in-memory fallback
│   │   ├── websocket_manager.py   # ConnectionManager broadcasting UI events
│   │   └── webrtc_signaling.py    # WebRTC SDP offer/answer session manager
│   ├── database/
│   │   ├── db.py                  # SQLAlchemy async engine & session maker
│   │   └── models.py              # ORM Models (SatelliteModel, TelemetryLog, etc.)
│   ├── fa2_extensions/
│   │   └── interfaces.py          # Abstract interfaces (ILamportClock, IVectorClock, etc.)
│   ├── faults/
│   │   └── fault_simulator.py     # Fault injection engine & active fault history
│   ├── models/
│   │   └── schemas.py             # Pydantic request/response validation schemas
│   ├── registry/
│   │   └── service_registry.py    # Dynamic SatelliteRegistry & Ring Leader Election
│   ├── services/
│   │   └── health_engine.py       # HealthEngine composite health formula
│   ├── config.py                  # Environment settings & constants
│   └── main.py                    # FastAPI application, REST endpoints & sweeper
├── frontend/
│   ├── src/
│   │   ├── components/            # Header, ExecutionTrace UI components
│   │   ├── pages/                 # MissionOverview, SatelliteRegistryPage, etc.
│   │   ├── App.jsx                # Core state, WebSocket connection, routing
│   │   └── main.jsx               # React DOM entrypoint
│   └── vite.config.js             # Vite proxy target setup
├── satellites/
│   └── satellite_node.py          # Satellite microservice node implementation
├── proto/
│   ├── satellite.proto            # gRPC protocol buffer service contracts
│   ├── satellite_pb2.py           # Generated Protobuf message types
│   └── satellite_pb2_grpc.py      # Generated gRPC stubs & servicer classes
├── docker/
│   ├── Dockerfile.backend         # Mission Control container build spec
│   ├── Dockerfile.frontend        # React Vite container build spec
│   └── Dockerfile.satellite       # Satellite microservice build spec
├── docs/                          # Engineering manuals & study documentation
├── tests/                         # Automated pytest integration test suite
└── docker-compose.yml             # Blueprint declaring 9 container services
```

---

## PART 6 — COMPLETE SYSTEM ARCHITECTURE

```mermaid
flowchart TB
    subgraph Client_Layer ["Client Observability Layer (Port 3000)"]
        UI["React 18 / Vite SPA\n(Mission Overview / Telemetry / Observatory)"]
    end

    subgraph Coordinator_Layer ["Coordinator Layer (Port 8000)"]
        MC["Mission Control Backend\n(FastAPI / Uvicorn)"]
        REG["Service Registry\n(Heartbeat TTL Sweeper)"]
        HE["Health Engine"]
        WS["WebSocket Manager\n(/ws)"]
        FS["Fault Simulator"]
        GRPC_C["gRPC Client Manager"]
    end

    subgraph Infrastructure_Layer ["Middleware & Storage Infrastructure"]
        PG[("PostgreSQL 15 DB\n(Port 5432)")]
        RMQ["RabbitMQ AMQP Broker\n(Ports 5672 / 15672)"]
    end

    subgraph Constellation_Layer ["Containerized Satellite Constellation"]
        SAT1["Satellite 01\n(gRPC: 5001 | P2P: 6001)"]
        SAT2["Satellite 02\n(gRPC: 5002 | P2P: 6002)"]
        SAT3["Satellite 03\n(gRPC: 5003 | P2P: 6003)"]
        SAT4["Satellite 04\n(gRPC: 5004 | P2P: 6004)"]
        SAT5["Satellite 05\n(gRPC: 5005 | P2P: 6005)"]
    end

    UI <-->|HTTP REST / WebSocket| MC
    MC --- REG
    MC --- HE
    MC --- WS
    MC --- FS
    MC --- GRPC_C
    
    MC -->|SQLAlchemy Async| PG
    SAT1 & SAT2 & SAT3 & SAT4 & SAT5 -->|AMQP Telemetry| RMQ
    RMQ -->|Consumer Callback| MC
    
    GRPC_C ==>|Synchronous gRPC| SAT1 & SAT2 & SAT3 & SAT4 & SAT5
    SAT1 <==>|Direct P2P Cross-Link| SAT4
    SAT2 <==>|Direct P2P Cross-Link| SAT5
```

---

## PART 7 — DISTRIBUTED SYSTEMS FUNDAMENTALS

### What is a Distributed System?
A distributed system is a collection of autonomous computing entities (nodes) that communicate over a network, coordinate their actions by passing messages, share no global memory or common physical clock, and appear to the user as a single coherent system.

| Distributed Systems Property | Project Mapping & Implementation Evidence |
| :--- | :--- |
| **Independent Autonomous Nodes** | 5 Satellite processes (`SAT-01`..`SAT-05`) executing independently in separate Docker containers. |
| **No Shared Memory** | Nodes communicate exclusively over network sockets (gRPC, P2P HTTP, AMQP, WebSockets). |
| **Concurrent Execution** | Satellite loops, FastAPI endpoints, RabbitMQ consumers, and WebSocket broadcast execute concurrently. |
| **Partial Failures** | Stopping `SAT-02` container does not crash Mission Control or other satellites. |
| **Dynamic Service Discovery** | Satellites register IP/ports at boot; Mission Control maintains dynamic address lookup table. |
| **Heterogeneous Protocols** | Uses gRPC (binary protobuf), P2P (HTTP/JSON), AMQP (RabbitMQ), WebSockets (WS), REST (HTTP/1.1). |

---

## PART 8 — UNIT 1: INTRODUCTION TO DISTRIBUTED SYSTEMS

### 8.1 Definition & Characteristics
- **Resource Sharing**: Satellites share telemetry, health scores, and cross-link bandwidth across the constellation.
- **Openness**: Protocols use standard open specifications (Protobuf v3, AMQP 0-9-1, HTTP/JSON, WebSockets).
- **Concurrency**: Satellites sample sensors simultaneously while Mission Control handles async API requests.

### 8.2 Goals of Distributed Systems
1. **Resource Sharing**: Remote satellites allow Mission Control to invoke RPC methods (`GetHealth`, `Ping`).
2. **Transparency**: The React UI displays a unified constellation status without exposing socket details.
3. **Scalability**: New satellites (`SAT-06`, etc.) can spin up, register, and join the constellation dynamically.
4. **Fault Tolerance**: Loss of heartbeats triggers sweeper isolation without stopping system operation.

### 8.3 Architecture Classification
- **Primary Type**: **Hybrid Distributed Architecture**.
- **Coordinator-Worker (Client-Server)**: Mission Control acts as coordinator; satellites auto-register and send heartbeats.
- **Peer-to-Peer (P2P)**: Satellites send direct cross-link packets node-to-node without passing payload data through Mission Control.

### 8.4 Design Issues
- **Heterogeneity**: Handled via Docker containers standardizing execution across host operating systems.
- **Failure Handling**: Addressed via heartbeat TTL sweeper (`10.0s`) and dynamic status transitions (`HEALTHY` -> `OFFLINE`).
- **Naming & Addressing**: Solved via Service Registry mapping logical ID (`SAT-01`) to container DNS (`satellite-01:5001`).

### 8.5 Middleware Concept
**Middleware** is software that resides between the operating system and applications to provide communication and data management capabilities.
- **In this project**: gRPC, RabbitMQ AMQP broker, FastAPI ASGI framework, and WebSockets act as communication middleware.
- **Important Viva Distinction**: Docker is **containerization infrastructure**, NOT middleware. Middleware handles inter-process communication contracts.

### 8.6 Distributed Multimedia & WebRTC
- **Concept**: Real-time transmission of streaming video/audio over networks.
- **Project Mapping**: `backend/communication/webrtc_signaling.py` implements **WebRTC Signaling** (SDP Offer/Answer exchange and ICE candidate registration). Full peer-to-peer media transport is handled at the signaling layer.

### 8.7 Virtualization & Docker
- **VM vs Container**: Virtual Machines virtualize hardware (Hypervisor + Guest OS), causing high overhead. Docker virtualizes the operating system kernel, making containers lightweight, fast to boot, and isolated.
- **Why Docker is Required**: Ensures each satellite runs as an isolated process with its own loopback network interface, preventing local port collision.

---

## PART 9 — UNIT 2: COMMUNICATION MECHANICS

### 9.1 Communication Fundamentals
Communication in distributed systems relies on message passing across physical/logical channels.
- **Synchronous**: Sender blocks until recipient returns response (e.g., gRPC `Ping()` call).
- **Asynchronous**: Sender publishes message and continues without waiting (e.g., RabbitMQ telemetry publish).

### 9.2 gRPC & Protocol Buffers (Synchronous RPC)
**gRPC** is a high-performance open-source RPC framework. It uses **Protocol Buffers** (`.proto`) as its Interface Definition Language (IDL) and binary serialization mechanism.

#### Complete gRPC Execution Flow
```mermaid
sequenceDiagram
    autonumber
    participant UI as React Frontend
    participant MC as Mission Control Backend
    participant GC as gRPC Client Manager
    participant SAT as SAT-01 Container (Port 5001)

    UI->>MC: POST /api/rpc/invoke {target_satellite_id: "SAT-01", method: "Ping"}
    Note over MC: Log [HTTP API] Request Received
    MC->>GC: invoke_rpc("SAT-01", "Ping")
    GC->>GC: Lookup SAT-01 endpoint (satellite-01:5001)
    Note over GC: Log [gRPC OUT] Mission Control -> SAT-01
    GC->>SAT: gRPC PingRequest (Binary Protobuf over HTTP/2)
    Note over SAT: SatelliteGrpcServicer.Ping()
    Note over SAT: Log [gRPC IN] SAT-01 <- Mission Control
    SAT-->>GC: gRPC PingResponse {status: "PONG"}
    Note over SAT: Log [gRPC OUT] SAT-01 -> Mission Control
    Note over GC: Log [gRPC RESULT] Latency: 12.4ms
    GC-->>MC: Return result payload
    MC->>MC: Persist CommunicationEvent to PostgreSQL
    MC-->>UI: Return JSON response
```

#### gRPC Code References
- **Protobuf Spec**: [`proto/satellite.proto`](file:///c:/Users/Anushka/Downloads/DS-Project/proto/satellite.proto)
- **Outbound Client**: [`backend/communication/grpc_client.py`](file:///c:/Users/Anushka/Downloads/DS-Project/backend/communication/grpc_client.py) (`invoke_rpc`)
- **Inbound Servicer**: [`satellites/satellite_node.py`](file:///c:/Users/Anushka/Downloads/DS-Project/satellites/satellite_node.py) (`SatelliteGrpcServicer`)
- **API Endpoint**: [`backend/main.py`](file:///c:/Users/Anushka/Downloads/DS-Project/backend/main.py) (`/api/rpc/invoke`)

### 9.3 Message-Oriented Communication (RabbitMQ / AMQP)
- **Concept**: Asynchronous, decoupled communication via message broker. Producers publish to exchanges; queues buffer messages; consumers process them asynchronously.
- **In this project**: Satellites publish telemetry messages to exchange `telemetry.exchange`. Mission Control registers a consumer listener that receives messages, updates registry metrics, and broadcasts to WebSocket clients.
- **Implementation**: [`backend/communication/rabbitmq_manager.py`](file:///c:/Users/Anushka/Downloads/DS-Project/backend/communication/rabbitmq_manager.py). Includes in-memory queue fallback if RabbitMQ broker is unreachable.

### 9.4 Stream-Oriented Communication (WebSockets)
- **Concept**: Full-duplex persistent TCP connection for continuous real-time streaming.
- **In this project**: `ConnectionManager` in [`backend/communication/websocket_manager.py`](file:///c:/Users/Anushka/Downloads/DS-Project/backend/communication/websocket_manager.py) manages browser connections at `/ws`. Whenever telemetry or state events occur, `websocket_manager.broadcast()` pushes JSON payloads instantly to all connected React clients.

### 9.5 Direct Peer-to-Peer (P2P) Communication
- **Concept**: Direct node-to-node communication without routing payload data through a central server.
- **In this project**: `SAT-01` sends direct HTTP POST packets to `SAT-04` at `http://satellite-04:6004/p2p/receive`. Mission Control triggers the command, but payload execution travels directly between satellite container network interfaces.
- **Implementation**: `send_to_peer()` in [`satellites/satellite_node.py`](file:///c:/Users/Anushka/Downloads/DS-Project/satellites/satellite_node.py).

### 9.6 WebRTC Signaling
- **Concept**: P2P multimedia audio/video communication setup via SDP offer/answer exchange.
- **Implementation**: [`backend/communication/webrtc_signaling.py`](file:///c:/Users/Anushka/Downloads/DS-Project/backend/communication/webrtc_signaling.py). Processes browser SDP offers and returns synthetic SDP answer sessions for simulated orbit camera feeds.

---

## PART 10 — NAMING, IDENTIFIERS, AND ADDRESSES

In distributed systems, entity identification requires mapping abstract logical names to concrete network locators.

| Identifier / Address | Example Value | Description / Scope |
| :--- | :--- | :--- |
| **Logical Satellite ID** | `SAT-01` | Human-readable unique constellation identifier |
| **Internal Node ID** | `NODE-SAT-01-8014` | Runtime unique process instance identifier |
| **Docker Hostname** | `satellite-01` | DNS host name inside Docker bridge network |
| **IP Address** | `172.18.0.6` | Dynamic IP assigned by Docker bridge network |
| **gRPC Port / Endpoint** | `5001` / `satellite-01:5001` | Synchronous RPC server port |
| **P2P Port / Endpoint** | `6001` / `satellite-01:6001` | Direct peer-to-peer HTTP server port |

---

## PART 11 — SERVICE DISCOVERY AND SERVICE REGISTRY

### Concept
Service discovery allows distributed nodes to locate each other dynamically without hardcoded IP addresses.

### Implementation
- **Registry Location**: [`backend/registry/service_registry.py`](file:///c:/Users/Anushka/Downloads/DS-Project/backend/registry/service_registry.py) (`SatelliteRegistry`).
- **Registration Flow**:
  1. Satellite container boots up and reads environment variables (`SAT_ID`, `GRPC_PORT`, `P2P_PORT`).
  2. Executes POST request to Mission Control: `/api/satellites/register`.
  3. `SatelliteRegistry.register()` stores a `SatelliteRegistration` dataclass record in memory.
  4. Mission Control broadcasts `NODE_REGISTERED` event over WebSocket.

---

## PART 12 — HEALTH MONITORING ENGINE & MATHEMATICAL FORMULA

### Composite Health Score Calculation
Located in [`backend/services/health_engine.py`](file:///c:/Users/Anushka/Downloads/DS-Project/backend/services/health_engine.py).

$$\text{Health Score} = 0.30 \cdot S_{\text{battery}} + 0.25 \cdot S_{\text{temp}} + 0.20 \cdot S_{\text{cpu}} + 0.15 \cdot S_{\text{memory}} + 0.10 \cdot S_{\text{signal}}$$

Where individual metric sub-scores $S_x$ are evaluated as:
- **Battery ($S_{\text{battery}}$)**: Directly equals battery percentage ($0.0 - 100.0\%$).
- **Temperature ($S_{\text{temp}}$)**: Ideal $\le 30^\circ\text{C}$ ($100\%$). If $>30^\circ\text{C}$, sub-score $= \max(0, 100 - (\text{temp} - 30) \cdot 2.5)$.
- **CPU ($S_{\text{cpu}}$)**: $100 - \text{CPU Usage}\%$.
- **Memory ($S_{\text{memory}}$)**: $100 - \text{Memory Usage}\%$.
- **Signal ($S_{\text{signal}}$)**: Directly equals signal strength percentage ($0.0 - 100.0\%$).

### Status Threshold Classification
- `HEALTHY`: Health Score $\ge 85.0$ and no critical fault.
- `WARNING`: $60.0 \le \text{Health Score} < 85.0$.
- `CRITICAL`: Health Score $< 60.0$ or severe thermal/battery fault.
- `OFFLINE`: Node heartbeat timed out ($>10.0\text{s}$) or container stopped.

---

## PART 13 — HEARTBEAT MECHANISM AND FAILURE DETECTION

```mermaid
stateDiagram-v2
    [*] --> HEALTHY: Container Boot & Register
    HEALTHY --> WARNING: Temp Spike / CPU Overload
    WARNING --> CRITICAL: Battery Drain / High Latency
    CRITICAL --> HEALTHY: Clear Faults & Recover
    HEALTHY --> OFFLINE: Heartbeat Timeout > 10.0s
    OFFLINE --> HEALTHY: Heartbeat Resumed (Container Start)
```

### Technical Details
- **Heartbeat Period**: Satellites send POST `/api/satellites/heartbeat` every 2.0s.
- **Heartbeat TTL**: Configured as `SWEEP_INTERVAL_SECONDS = 3.0` and `HEARTBEAT_TIMEOUT_SECONDS = 10.0`.
- **Sweeper Task**: `heartbeat_sweeper_task()` in [`backend/main.py`](file:///c:/Users/Anushka/Downloads/DS-Project/backend/main.py) runs asynchronously every 3 seconds. Executes `global_registry.sweep_failures()`.
- **Failure Event**: If `time.time() - reg.last_heartbeat > 10.0s`, status is updated to `OFFLINE` and `NODE_DISCONNECTED` event is broadcast over WebSocket to the UI.

---

## PART 14 — FAULT TOLERANCE (CONTAINER CRASH & RECOVERY)

### Container Crash Demonstration
1. **Action**: Run `docker compose stop satellite-02`.
2. **Result**: `SAT-02` container stops sending heartbeats.
3. **Detection**: After 10 seconds, `heartbeat_sweeper_task()` detects timeout.
4. **Log Output**: `[FAILURE DETECTOR] Satellite SAT-02 heartbeat timed out! Status marked OFFLINE.`
5. **UI Transition**: Main Overview updates status badge to `4/5 Active` and `DEGRADED`.

### Container Recovery Demonstration
1. **Action**: Run `docker compose start satellite-02`.
2. **Result**: Container boots, `start_autonomous_loop()` executes auto-registration retry loop.
3. **Re-registration**: Sends POST `/api/satellites/register`.
4. **Log Output**: `[RECOVERY] Mission Control ← SAT-02 | Heartbeat resumed | status=ONLINE/HEALTHY`.
5. **UI Transition**: Main Overview updates back to `5/5 Active` and `HEALTHY`.

---

## PART 15 — FAULT SIMULATOR MECHANICS

Managed by [`backend/faults/fault_simulator.py`](file:///c:/Users/Anushka/Downloads/DS-Project/backend/faults/fault_simulator.py).

| Fault Type | Target Node | Parameter | Effect on System |
| :--- | :--- | :--- | :--- |
| `STOP_NODE` | Any Satellite | N/A | Forces registry status to `OFFLINE`, health score to `0.0`. |
| `RESTART_NODE` | Any Satellite | N/A | Resets registry status to `HEALTHY`, health score to `100.0`. |
| `HIGH_LATENCY` | Any Satellite | `latency_ms: 500` | Injects async delay prior to P2P or RPC execution. |
| `PACKET_LOSS` | Any Satellite | `loss_pct: 20` | Simulates dropped packets in communication events. |
| `TEMP_SPIKE` | Any Satellite | `temperature: 85` | Forces temperature to 85°C, status to `CRITICAL`. |
| `BATTERY_DRAIN` | Any Satellite | `battery: 15` | Forces battery to 15%, status to `CRITICAL`. |
| `CPU_OVERLOAD` | Any Satellite | `cpu_usage: 98` | Forces CPU usage to 98%, status to `WARNING`. |

---

## PART 16 — LEADER ELECTION ALGORITHM (RING ELECTION)

### Ring Leader Election Consensus
Implemented in `run_ring_election()` inside [`backend/registry/service_registry.py`](file:///c:/Users/Anushka/Downloads/DS-Project/backend/registry/service_registry.py).

```mermaid
flowchart LR
    SAT1(("SAT-01")) --> SAT2(("SAT-02"))
    SAT2 --> SAT3(("SAT-03"))
    SAT3 --> SAT4(("SAT-04"))
    SAT4 --> SAT5(("SAT-05 (Leader)"))
    SAT5 --> SAT1
```

### Execution Steps
1. Logical ring topology ordered as: `SAT-01 -> SAT-02 -> SAT-03 -> SAT-04 -> SAT-05 -> SAT-01`.
2. Initiator (e.g. `SAT-01`) circulates election tokens through active ring members.
3. If a node is `OFFLINE` (e.g. `SAT-02`), it is automatically **bypassed** in the ring path.
4. Active nodes append their ID to participating list.
5. The node with the **highest active numerical ID** wins the election (nominally `SAT-05`).
6. Result is persisted to PostgreSQL and broadcast over WebSocket as `LEADER_ELECTION_COMPLETED`.

---

## PART 17 — DATABASE PERSISTENCE (POSTGRESQL & SQLALCHEMY)

- **Container**: `satellite-postgres` running `postgres:15-alpine` on Port `5432`.
- **Database Name**: `satellite_db`, User: `postgres`, Password: `postgrespassword`.
- **ORM Configuration**: [`backend/database/db.py`](file:///c:/Users/Anushka/Downloads/DS-Project/backend/database/db.py) uses SQLAlchemy `create_async_engine` with `postgresql+asyncpg`.

### Models ([`backend/database/models.py`](file:///c:/Users/Anushka/Downloads/DS-Project/backend/database/models.py))
1. `SatelliteModel` (`satellites`): Dynamic registry snapshots.
2. `TelemetryLog` (`telemetry_logs`): Historical telemetry metrics.
3. `CommunicationEvent` (`communication_events`): Log of all gRPC, P2P, RabbitMQ, and Election events.
4. `FaultInjectionLog` (`fault_logs`): Active and cleared fault injection history.
5. `ConceptEvidence` (`concept_evidences`): Academic unit evidence audit records.

---

## PART 18 — DOCKER INFRASTRUCTURE & CONTAINERIZATION

### Why Docker is Essential for This Project
1. **Process Isolation**: Prevents global variable leaking between satellites.
2. **Network Stack Isolation**: Gives each satellite its own IP address and loopback interface inside `satellite-net`.
3. **Port Management**: Allows binding gRPC ports `5001`–`5005` and P2P ports `6001`–`6005` independently.
4. **Reproducibility**: Eliminates "works on my machine" issues across Windows/Linux host environments.

---

## PART 19 — DOCKER COMPOSE ARCHITECTURE & SERVICES

Declared in [`docker-compose.yml`](file:///c:/Users/Anushka/Downloads/DS-Project/docker-compose.yml).

| Container Name | Service Name | Image / Dockerfile | Exposed Ports | Role |
| :--- | :--- | :--- | :--- | :--- |
| `satellite-postgres` | `postgres` | `postgres:15-alpine` | `5432:5432` | Relational Database |
| `satellite-rabbitmq` | `rabbitmq` | `rabbitmq:3-management-alpine` | `5672:5672`, `15672:15672` | AMQP Message Broker |
| `mission-control-backend` | `mission-control` | `docker/Dockerfile.backend` | `8000:8000` | FastAPI Coordinator |
| `satellite-01` | `satellite-01` | `docker/Dockerfile.satellite` | `5001:5001`, `6001:6001` | Satellite 01 Microservice |
| `satellite-02` | `satellite-02` | `docker/Dockerfile.satellite` | `5002:5002`, `6002:6002` | Satellite 02 Microservice |
| `satellite-03` | `satellite-03` | `docker/Dockerfile.satellite` | `5003:5003`, `6003:6003` | Satellite 03 Microservice |
| `satellite-04` | `satellite-04` | `docker/Dockerfile.satellite` | `5004:5004`, `6004:6004` | Satellite 04 Microservice |
| `satellite-05` | `satellite-05` | `docker/Dockerfile.satellite` | `5005:5005`, `6005:6005` | Satellite 05 Microservice |
| `mission-control-frontend` | `frontend` | `docker/Dockerfile.frontend` | `3000:3000` | React 18 / Vite Web UI |

---

## PART 20 — DOCKER NETWORKING (CONTAINER DNS vs LOCALHOST)

### Critical Networking Rule
- **Host Machine Browser**: Accesses services via `localhost` (e.g. `http://localhost:3000`, `http://localhost:8000`).
- **Inside Container Bridge Network (`satellite-net`)**: Containers CANNOT connect to `localhost:8000` because `localhost` points to that container's internal loopback. Containers resolve each other using **Docker Compose Service DNS Names**:
  - Mission Control: `http://mission-control:8000`
  - Satellite 01: `satellite-01:5001` (gRPC) / `satellite-01:6001` (P2P)
  - RabbitMQ: `amqp://guest:guest@rabbitmq:5672/`
  - PostgreSQL: `postgresql+asyncpg://postgres:postgrespassword@postgres:5432/satellite_db`

---

## PART 21 — COMPLETE END-TO-END SYSTEM WORKFLOW

```mermaid
flowchart TD
    A["1. docker compose up -d --build"] --> B["2. Postgres & RabbitMQ boot & report HEALTHY"]
    B --> C["3. Mission Control initializes DB schema & connects to RabbitMQ"]
    C --> D["4. Satellites (SAT-01..05) boot & run auto-registration loop"]
    D --> E["5. Satellites register with Mission Control & start sending 2s heartbeats"]
    E --> F["6. Telemetry published to RabbitMQ -> Consumed by MC -> Broadcast via WebSocket"]
    F --> G["7. React Frontend connects to /ws -> Renders live overview & telemetry charts"]
    G --> H["8. User triggers gRPC Ping -> MC invokes gRPC on SAT-01 -> Logs RPC in Docker"]
    H --> I["9. User triggers P2P message -> SAT-01 sends direct HTTP POST to SAT-04"]
    I --> J["10. Container SAT-02 stopped -> Sweeper detects timeout after 10s -> Marks OFFLINE"]
    J --> K["11. Container SAT-02 restarted -> Re-registers & recovers to HEALTHY"]
```

---

## PART 22 — COMPLETE COMMUNICATION MATRIX

| Communication Flow | Protocol | Source Endpoint | Destination Endpoint | Sync / Async | Primary Purpose |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Satellite Registration** | HTTP REST | `SAT-01`..`05` | `POST mission-control:8000/api/satellites/register` | Async | Initial service discovery registration |
| **Satellite Heartbeat** | HTTP REST | `SAT-01`..`05` | `POST mission-control:8000/api/satellites/heartbeat` | Async | Health metric update & liveness signal |
| **RPC Invocation** | gRPC / Protobuf | `Mission Control` | `satellite-XX:500X` (`Ping`, `GetHealth`, `GetInfo`) | Synchronous | Direct command/telemetry RPC execution |
| **Direct P2P Link** | HTTP REST | `satellite-01` | `POST satellite-04:6004/p2p/receive` | Async/Sync | Direct inter-satellite data cross-link |
| **Telemetry Publish** | AMQP 0-9-1 | `SAT-01`..`05` | `rabbitmq:5672` (`telemetry.exchange`) | Asynchronous | Decoupled message queue publishing |
| **Telemetry Consume** | AMQP 0-9-1 | `rabbitmq:5672` | `Mission Control` listener callback | Asynchronous | Message consumption & database storage |
| **Real-time UI Stream** | WebSockets | `Mission Control` | `ws://localhost:8000/ws` -> React UI | Asynchronous | Sub-second telemetry & state push |
| **WebRTC Signaling** | HTTP REST | React UI | `POST mission-control:8000/api/webrtc/offer` | Synchronous | SDP offer/answer camera feed setup |

---

## PART 23 — CODE-TO-CONCEPT MAPPING MATRIX

| Distributed Systems Concept | Repository File Path | Responsible Class / Function | Description of Code Execution |
| :--- | :--- | :--- | :--- |
| **Service Discovery** | `backend/registry/service_registry.py` | `SatelliteRegistry.register()` | Registers dynamic satellite IP/ports at runtime |
| **Synchronous gRPC** | `backend/communication/grpc_client.py` | `GRPCClientManager.invoke_rpc()` | Establishes gRPC async channel and calls stub |
| **gRPC Servicer** | `satellites/satellite_node.py` | `SatelliteGrpcServicer` | Receives and processes gRPC calls on satellite |
| **Direct P2P Link** | `satellites/satellite_node.py` | `send_to_peer()`, `receive_p2p()` | Transmits direct node-to-node packets |
| **Message Queueing** | `backend/communication/rabbitmq_manager.py` | `RabbitMQManager.publish_telemetry()` | Publishes telemetry messages to AMQP fanout exchange |
| **Stream Push** | `backend/communication/websocket_manager.py` | `ConnectionManager.broadcast()` | Pushes WebSocket JSON frames to React clients |
| **Health Engine** | `backend/services/health_engine.py` | `HealthEngine.calculate_health()` | Evaluates weighted composite satellite score |
| **Failure Detector** | `backend/main.py` | `heartbeat_sweeper_task()` | Background task sweeping nodes exceeding 10s TTL |
| **Ring Leader Election** | `backend/registry/service_registry.py` | `run_ring_election()` | Circulates election token through active ring nodes |
| **Fault Injection** | `backend/faults/fault_simulator.py` | `FaultSimulator.inject_fault()` | Simulates node crashes, latency, thermal spikes |
| **Database Audit** | `backend/database/models.py` | `CommunicationEvent`, `TelemetryLog` | ORM schemas for PostgreSQL audit logs |
| **WebRTC Signaling** | `backend/communication/webrtc_signaling.py` | `WebRTCSignalingManager.process_offer()` | Handles SDP offer/answer media negotiation |

---

## PART 24 — FRONTEND PAGE -> BACKEND API -> DISTRIBUTED OPERATION

```mermaid
flowchart LR
    P1["1. Main Overview Page"] -->|GET /api/satellites| MC1["Mission Control Registry"]
    P2["2. Satellite Registry Page"] -->|GET /api/satellites| MC2["Service Lookup Table"]
    P3["3. Live Telemetry Page"] -->|ws://localhost:8000/ws| MC3["WebSocket Stream Manager"]
    P4["4. Observatory gRPC Tab"] -->|POST /api/rpc/invoke| MC4["gRPC Client -> SAT Container"]
    P5["5. Observatory P2P Tab"] -->|POST /api/p2p/send| MC5["P2P Trigger -> SAT-01 -> SAT-04"]
    P6["6. Fault Simulator Page"] -->|POST /api/faults/inject| MC6["Fault Simulator Engine"]
    P7["7. Topology Page"] -->|POST /api/election/ring| MC7["Ring Leader Election Engine"]
```

---

## PART 25 — HOW TO PRESENT THE PROJECT TO THE PANEL

### Logical 8-Step Presentation Sequence
1. **Introduction & Motivation**: State project title, goal, and why satellite constellations require distributed systems.
2. **System Architecture Overview**: Present the 9-container topology (Mission Control, 5 Satellites, Postgres, RabbitMQ, Frontend).
3. **Live Overview Dashboard**: Open `http://localhost:3000/` showing 5 active discovered satellites and health scores.
4. **Service Discovery & Registry**: Show `/registry` table proving dynamic IP/port registration (`5001`–`5005` gRPC, `6001`–`6005` P2P).
5. **Synchronous gRPC Demo**: Open Observatory page, trigger `Ping` for `SAT-01`, show Docker logs proving `[gRPC OUT]` and `[gRPC IN]`.
6. **Direct P2P Cross-Link Demo**: Trigger P2P message `SAT-01` -> `SAT-04`, show Docker logs proving direct node-to-node HTTP transmission.
7. **Fault Tolerance & Recovery**: Run `docker compose stop satellite-02`. Demonstrate 10s sweeper detecting failure. Restart container and demonstrate automatic recovery.
8. **Conclusion & Q&A**: Summarize implementation truth, key engineering takeaways, and invite questions.

---

## PART 26 — LIVE DEMONSTRATION EXECUTION PLAN

### Terminal Setup
Open 3 terminals in VS Code:
- **Terminal 1**: Control Terminal (commands)
- **Terminal 2**: `docker compose logs -f mission-control`
- **Terminal 3**: `docker compose logs -f satellite-01`

### Step 1: Clean Startup Sequence
```powershell
cd C:\Users\Anushka\Downloads\DS-Project
docker compose down
docker compose up -d --build
docker compose ps
```
*Verify all 9 services show `Up`.*

---

## PART 27 — DEMO 1: SYSTEM OVERVIEW & DASHBOARD
1. Open `http://localhost:3000/` in browser.
2. Highlight Constellation Overview cards: `5/5 Active Satellites`, `System Status: HEALTHY`, `Current Leader: SAT-05`.
3. Point out live WebSocket connection badge (`WebSocket: CONNECTED`).
4. **Panel Explanation**: "This dashboard receives real-time telemetry updates broadcast from Mission Control over WebSockets."

---

## PART 28 — DEMO 2: SERVICE REGISTRY & DISCOVERY
1. Navigate to `http://localhost:3000/registry`.
2. Review discovery lookup table: `Satellite ID`, `Internal Node ID`, `Address`, `gRPC Port`, `P2P Port`, `Status`, `Last Heartbeat`.
3. **Panel Explanation**: "This table proves dynamic service discovery. Satellites auto-registered their IP addresses and ports with Mission Control upon container boot."

---

## PART 29 — DEMO 3: LIVE STREAM-ORIENTED TELEMETRY
1. Navigate to `http://localhost:3000/telemetry`.
2. Select satellite `SAT-03`. Observe 4 continuous Recharts line graphs (Battery, Temperature, CPU, Health Score).
3. **Panel Explanation**: "Telemetry messages sample every 2 seconds, publish to RabbitMQ, consume asynchronously, and stream to Recharts over WebSockets."

---

## PART 30 — DEMO 4: gRPC REMOTE PROCEDURE CALL
1. Navigate to `http://localhost:3000/observatory`, select **gRPC / RPC** tab.
2. Select target satellite `SAT-01`, method `Ping`, click **Execute gRPC Call**.
3. **Observe Terminal 2 (Mission Control)**:
   ```log
   INFO:backend.communication.grpc_client:[gRPC OUT] Mission Control → SAT-01 | method=Ping | target=satellite-01:5001 | protocol=gRPC | status=SENT
   INFO:backend.communication.grpc_client:[gRPC RESULT] Mission Control ← SAT-01 | method=Ping | status=SUCCESS | latency=12.4ms
   ```
4. **Observe Terminal 3 (`satellite-01`)**:
   ```log
   [INFO] [SatelliteNode] [gRPC IN] SAT-01 ← Mission Control | method=Ping | status=REQUEST_RECEIVED
   [INFO] [SatelliteNode] [gRPC OUT] SAT-01 → Mission Control | method=Ping | status=SUCCESS
   ```
5. **Panel Explanation**: "This log trace proves synchronous gRPC communication across container boundaries using Protocol Buffers."

---

## PART 31 — DEMO 5: PEER-TO-PEER (P2P) DIRECT COMMUNICATION
1. In Observatory page, select **Direct P2P Link** tab.
2. Set Source: `SAT-01`, Destination: `SAT-04`, click **Send Direct P2P Message**.
3. **Observe `satellite-01` Docker Log**:
   ```log
   [INFO] [SatelliteNode] [SAT-01 DIRECT P2P OUTGOING] Sending direct P2P packet to SAT-04 at http://satellite-04:6004/p2p/receive
   [INFO] [SatelliteNode] [SAT-01 DIRECT P2P ACK] Direct ACK from SAT-04 in 68.08ms
   ```
4. **Panel Explanation**: "Mission Control triggered the request, but payload data traveled directly from `satellite-01` to `satellite-04` over port `6004` without being relayed through Mission Control."

---

## PART 32 — DEMO 6: RABBITMQ MESSAGE BROKER
1. Run terminal command: `docker compose logs --tail=50 satellite-rabbitmq`.
2. Open RabbitMQ Management UI at `http://localhost:15672` (Username: `guest`, Password: `guest`).
3. Show `telemetry.exchange` fanout exchange and queue `telemetry.queue`.
4. **Panel Explanation**: "RabbitMQ provides message-oriented decoupling. Satellites publish telemetry without waiting for Mission Control database writes."

---

## PART 33 — DEMO 7: FAULT TOLERANCE & FAILURE RECOVERY
1. Execute in Terminal 1: `docker compose stop satellite-02`.
2. Wait 10 seconds. Observe Mission Control terminal log:
   ```log
   WARNING:MissionControl:[FAILURE DETECTOR] Satellite SAT-02 heartbeat timed out! Status marked OFFLINE.
   ```
3. Show Dashboard UI updating to `4/5 Active Satellites` and `DEGRADED`.
4. Execute in Terminal 1: `docker compose start satellite-02`.
5. Observe Mission Control log:
   ```log
   INFO:MissionControl:[REGISTRY] Dynamic Registration SUCCESS | satellite_id=SAT-02 | address=satellite-02:5002
   INFO:MissionControl:[RECOVERY] Mission Control ← SAT-02 | Heartbeat resumed | status=ONLINE/HEALTHY
   ```
6. Show Dashboard UI recovering back to `5/5 Active Satellites` and `HEALTHY`.
7. **Panel Explanation**: "This proves fault tolerance and automatic recovery in our distributed system."

---

## PART 34 — DEMO 8: WEBRTC SIGNALING
1. In Observatory page, select **WebRTC Camera Stream** tab. Click **Establish Orbit Cam Feed**.
2. Observe SDP Offer/Answer negotiation trace and ICE Candidate status `CONNECTED`.
3. **Panel Explanation**: "Mission Control handles WebRTC SDP offer/answer signaling for simulated satellite payload feeds."

---

## PART 35 — TERMINAL PROOF GUIDE

| Terminal Command | Purpose & Objective | Expected Observation |
| :--- | :--- | :--- |
| `docker compose ps` | Verify status of all 9 services | 9 services showing `Up` or `Up (healthy)` |
| `docker compose logs -f mission-control` | Monitor coordinator logs | `[gRPC OUT]`, `[HEARTBEAT]`, `[FAILURE DETECTOR]` |
| `docker compose logs -f satellite-01` | Monitor Satellite 01 logs | `[gRPC IN]`, `[SAT-01 DIRECT P2P OUTGOING]` |
| `docker compose logs -f satellite-03` | Monitor Satellite 03 logs | `[gRPC IN]` for `GetHealth` calls |
| `docker compose stop satellite-02` | Simulate node failure | `SAT-02` container stops execution |
| `docker compose start satellite-02` | Test automatic recovery | Re-registration log & heartbeat recovery |
| `python -m pytest tests/ -v` | Run automated QA test suite | `5 passed in 0.31s` |

---

## PART 36 — WHAT EVERY LOG MEANS

- `[HTTP API]`: HTTP request received by Mission Control REST API from React frontend.
- `[gRPC OUT]`: Outbound RPC request sent from Mission Control client to satellite container.
- `[gRPC IN]`: Inbound RPC request received by target satellite servicer on port `500X`.
- `[gRPC RESULT]`: Successful RPC response received by Mission Control with latency measurement.
- `[SAT-01 DIRECT P2P OUTGOING]`: Direct P2P packet transmitted from `SAT-01` container to peer container.
- `[HEARTBEAT]`: Satellite periodic liveness check received by Mission Control.
- `[FAILURE DETECTOR]`: Background sweeper task detected node timeout ($>10.0\text{s}$) and marked node `OFFLINE`.
- `[RECOVERY]`: Previously offline satellite resumed heartbeats and recovered to `HEALTHY`.

---

## PART 37 — WHY EACH COMMUNICATION METHOD EXISTS

| Communication Method | Why Used in This Project | Best Suited For | Key Difference |
| :--- | :--- | :--- | :--- |
| **HTTP REST** | Simple command triggering and status retrieval | Short request/response interactions | Request-driven, synchronous, higher overhead |
| **gRPC** | Fast, typed, contract-first remote procedure calls | Internal microservice-to-microservice RPC | Binary Protobuf over HTTP/2, low latency |
| **Direct P2P Link** | Direct satellite-to-satellite data transfers | Node-to-node cross-links without coordinator relay | Eliminates central bottleneck for peer data |
| **RabbitMQ AMQP** | Asynchronous decoupled telemetry messaging | High-volume message queuing & fanout | Sender publishes and immediately continues |
| **WebSockets** | Real-time server-push to browser UI | Persistent stream-oriented telemetry | Full-duplex persistent TCP connection |
| **WebRTC Signaling** | SDP session negotiation for media feeds | Real-time peer audio/video streaming | Negotiates P2P media session parameters |

---

## PART 38 — COMPLETE ALGORITHMS INVENTORY

| Algorithm Name | Location in Code | Inputs | Outputs | Primary DS Relevance |
| :--- | :--- | :--- | :--- | :--- |
| **Composite Health Scoring** | `backend/services/health_engine.py` | Battery, temp, CPU, memory, signal | Score ($0-100$), status (`HEALTHY`..`CRITICAL`) | Local state evaluation & metric weighting |
| **Heartbeat Failure Sweeper** | `backend/main.py` (`heartbeat_sweeper_task`) | Registry timestamp snapshot | List of timed-out nodes (`OFFLINE`) | Unreliable failure detector with TTL timeout |
| **Ring Leader Election** | `backend/registry/service_registry.py` | Initiator ID, active registry nodes | Elected leader ID (highest active ID) | Ring-based leader consensus with node bypass |
| **P2P Direct Routing** | `satellites/satellite_node.py` | Peer IP, port, message payload | ACK status & latency | Decentralized peer-to-peer data transmission |
| **Registration Retry Loop** | `satellites/satellite_node.py` | Coordinator URL | Successful dynamic registration | Resilient boot-up & network fault tolerance |

---

## PART 39 — WHY THIS QUALIFIES AS A REAL DISTRIBUTED SYSTEM

During your viva defense, if asked **"Is this really a distributed system or just a web app?"**, answer:

"This project is a true distributed system because:
1. **Independent Process Boundary**: Satellites execute as isolated, independent operating system processes inside 5 separate Docker containers.
2. **Network Isolation**: Nodes share zero global memory and communicate exclusively over network sockets (`5001`–`5005`, `6001`–`6005`, `8000`, `5672`, `5432`).
3. **Dynamic Discovery**: Nodes register dynamically at runtime via a Service Registry.
4. **Heterogeneous Protocols**: Demonstrates synchronous gRPC binary RPC, asynchronous RabbitMQ message queuing, direct P2P HTTP cross-linking, and streaming WebSockets.
5. **Partial Failures**: Crashing `SAT-02` container degrades system performance without crashing coordinator or peer satellites.
6. **Distributed Consensus**: Implements Ring Leader Election to elect a constellation leader dynamically."

---

## PART 40 — DISTRIBUTED SYSTEMS DESIGN ISSUES MATRIX

| Design Issue | Where It Appears in System | How Our Project Solves It |
| :--- | :--- | :--- |
| **Heterogeneity** | Different OS hosts / Python environments | Containerized via Docker Compose specs |
| **Naming & Addressing** | Mapping `SAT-01` to IP and port | Service Registry dynamic lookup table |
| **Partial Failure** | Satellite container crash or outage | Heartbeat TTL sweeper & status update |
| **Concurrency** | Simultaneous telemetry & REST API requests | Python `asyncio` async/await event loops |
| **Communication Overhead**| Telemetry data serialization | Protobuf v3 binary serialization for RPC |
| **Scalability** | Adding additional satellite nodes | Dynamic registration without code changes |

---

## PART 41 — PANEL VIVA QUESTIONS & ANSWERS (50+ Q&A)

### Basic & Conceptual
1. **Q: What is a distributed system?**  
   *A: A collection of autonomous computing nodes connected via network that communicate by message passing and coordinate actions to appear as a single system.*
2. **Q: Why are satellites suitable as distributed nodes?**  
   *A: Satellites run independent control loops in orbit, separated by distance, communicating over wireless cross-links without shared memory.*
3. **Q: What is the role of Mission Control?**  
   *A: Central coordinator managing Service Registry, issuing gRPC calls, receiving telemetry, executing failure detection, and serving the React UI.*
4. **Q: Why use 5 satellite containers instead of 1?**  
   *A: To demonstrate multi-node concurrency, service discovery, P2P routing, message queuing, and leader consensus.*
5. **Q: What happens if Mission Control restarts?**  
   *A: Satellites run background registration retry loops until Mission Control is back online.*

### Architecture & Networking
6. **Q: What architecture model is used?**  
   *A: Hybrid Coordinator-Worker and Peer-to-Peer architecture.*
7. **Q: What network interface connects containers?**  
   *A: Docker bridge network `satellite-net` assigning container DNS names (`satellite-01`, etc.).*
8. **Q: Why can't a container use `localhost:8000` to reach Mission Control?**  
   *A: Inside a container, `localhost` points to its own loopback. It must use service name `http://mission-control:8000`.*
9. **Q: What ports are exposed by satellite containers?**  
   *A: gRPC ports `5001`–`5005` and P2P ports `6001`–`6005`.*
10. **Q: What port does Mission Control run on?**  
    *A: Port `8000` (FastAPI / Uvicorn).*

### gRPC & Protocol Buffers
11. **Q: What is gRPC?**  
    *A: A high-performance RPC framework developed by Google using Protocol Buffers over HTTP/2.*
12. **Q: What is Protocol Buffers?**  
    *A: Language-neutral binary serialization format defined in `.proto` files.*
13. **Q: Which file defines the gRPC contract?**  
    *A: `proto/satellite.proto`.*
14. **Q: Name 3 gRPC methods defined in the proto file.**  
    *A: `Ping()`, `GetHealth()`, `GetSatelliteInfo()`.*
15. **Q: Who acts as the gRPC client and server?**  
    *A: Mission Control is the gRPC client (`grpc_client.py`); satellite containers are gRPC servers (`SatelliteGrpcServicer`).*

### Message Queuing (RabbitMQ)
16. **Q: What is RabbitMQ?**  
    *A: An AMQP message broker handling asynchronous message queuing.*
17. **Q: Why use RabbitMQ for telemetry instead of direct HTTP POST?**  
    *A: Decouples satellite telemetry generation from database write latency.*
18. **Q: What AMQP ports are used?**  
    *A: Port `5672` for AMQP messaging, Port `15672` for Management Web UI.*
19. **Q: What exchange type is used?**  
    *A: Fanout exchange named `telemetry.exchange`.*
20. **Q: What happens if RabbitMQ is offline?**  
    *A: `RabbitMQManager` falls back resiliently to an async in-memory queue.*

### Peer-to-Peer (P2P)
21. **Q: What is P2P communication in this project?**  
    *A: Direct satellite-to-satellite HTTP packet transmission without passing payload through Mission Control.*
22. **Q: How do you prove P2P doesn't pass payload through Mission Control?**  
    *A: In `satellite-01` Docker log, we see direct HTTP POST to `http://satellite-04:6004/p2p/receive`.*
23. **Q: What functions handle P2P?**  
    *A: `send_to_peer()` and `receive_p2p()` in `satellites/satellite_node.py`.*
24. **Q: Why use P2P cross-links in space missions?**  
    *A: Allows satellites to relay emergency alerts or orbit sync packets directly when ground stations are out of line-of-sight.*

### WebSockets & Real-Time UI
25. **Q: Why use WebSockets for the UI?**  
    *A: Provides persistent full-duplex connection for real-time telemetry streaming without HTTP polling overhead.*
26. **Q: What WebSocket endpoint does the React UI connect to?**  
    *A: `ws://localhost:8000/ws`.*
27. **Q: What Python class manages WebSockets?**  
    *A: `ConnectionManager` in `backend/communication/websocket_manager.py`.*
28. **Q: What event type updates line charts?**  
    *A: `TELEMETRY_UPDATED`.*

### Failure Detection & Recovery
29. **Q: How does Mission Control detect satellite failure?**  
    *A: Background task `heartbeat_sweeper_task()` runs every 3s and checks if `last_heartbeat > 10.0s`.*
30. **Q: What happens when a satellite times out?**  
    *A: Status updates to `OFFLINE`, health score to `0.0`, and `NODE_DISCONNECTED` event broadcasts to UI.*
31. **Q: How does recovery work?**  
    *A: When container restarts, auto-registration loop re-registers node and resumes 2s heartbeats.*
32. **Q: Is the failure detector crash-proof?**  
    *A: Yes, sweeper exceptions are caught so the background loop never terminates.*

### Leader Election
33. **Q: What leader election algorithm is implemented?**  
    *A: Ring Leader Election (Highest Active ID Wins).*
34. **Q: How does the ring algorithm handle offline nodes?**  
    *A: Offline nodes are detected in registry lookup and automatically bypassed in the logical ring path.*
35. **Q: Which satellite is nominally elected leader?**  
    *A: `SAT-05` (highest numerical ID).*

### Database & Persistence
36. **Q: What database is used?**  
    *A: PostgreSQL 15 running in `satellite-postgres` container on Port `5432`.*
37. **Q: What ORM is used?**  
    *A: SQLAlchemy 2.0 with `asyncpg` async driver.*
38. **Q: Name 3 ORM tables.**  
    *A: `satellites`, `telemetry_logs`, `communication_events`.*

### Health Scoring Algorithm
39. **Q: What is the health score formula?**  
    *A: Weighted composite: 30% Battery + 25% Temp + 20% CPU + 15% Memory + 10% Signal.*
40. **Q: What temperature triggers `CRITICAL` status?**  
    *A: Temperature $> 30^\circ\text{C}$ degrades score; severe spikes trigger `CRITICAL` status.*

### Docker Infrastructure
41. **Q: How many containers run in Docker Compose?**  
    *A: 9 containers.*
42. **Q: Name all 9 services.**  
    *A: `postgres`, `rabbitmq`, `mission-control`, `satellite-01`..`05`, `frontend`.*
43. **Q: Where are Dockerfiles located?**  
    *A: Inside `docker/` directory (`Dockerfile.backend`, `Dockerfile.satellite`, `Dockerfile.frontend`).*

### Implementation Truth
44. **Q: Are Lamport Clocks implemented as executable logic?**  
    *A: No, defined as an abstract interface `ILamportClock` in `backend/fa2_extensions/interfaces.py` for FA-2 extensions.*
45. **Q: Are Vector Clocks implemented as executable logic?**  
    *A: No, defined as an abstract interface `IVectorClock`.*
46. **Q: Is Ricart-Agrawala Distributed Mutex implemented?**  
    *A: No, defined as an abstract interface `IDistributedMutex`.*
47. **Q: Is Ring Leader Election implemented?**  
    *A: Yes, fully executable in `backend/registry/service_registry.py` (`run_ring_election`).*
48. **Q: Is full WebRTC media streaming implemented?**  
    *A: WebRTC SDP offer/answer signaling is implemented; raw video media streaming is simulated at the signaling layer.*
49. **Q: Is automated testing included?**  
    *A: Yes, 5 automated pytest integration and unit tests (`tests/test_unit.py`, `tests/test_integration.py`).*
50. **Q: How do you verify tests?**  
    *A: Run `python -m pytest tests/ -v` (5/5 passed).*

---

## PART 42 — "EXPLAIN THIS PROJECT IN 2 MINUTES"

"Good morning panel. Our project is a containerized **Distributed Satellite Monitoring and Mission Control System**.

In space operations, satellite constellations execute autonomously, sampling telemetry and communicating across uncertain network links. To mirror this real-world scenario, our architecture consists of **5 independent Python satellite microservices**, a central **FastAPI Mission Control coordinator**, a **React 18 web UI**, **RabbitMQ message broker**, and **PostgreSQL database**, orchestrated as **9 isolated containers using Docker Compose**.

Key technical highlights include:
1. **Dynamic Service Discovery**: Satellites auto-register their IP addresses and ports upon container boot.
2. **Multi-Protocol Communication**: Demonstrates synchronous **gRPC** calls over Protocol Buffers, asynchronous telemetry queuing via **RabbitMQ AMQP**, direct satellite-to-satellite **P2P cross-links**, and streaming **WebSockets**.
3. **Fault Tolerance & Recovery**: A background heartbeat sweeper task detects node outages after a 10-second TTL, marking crashed nodes `OFFLINE`. When restarted, nodes auto-register and recover automatically.
4. **Ring Leader Election**: Executes distributed consensus where active ring nodes elect the highest numerical ID as leader.

Everything is containerized, fully verified, and logged in real-time across Docker containers."

---

## PART 43 — "EXPLAIN THIS PROJECT IN 5 MINUTES"

*(Follow 2-minute structure, expanding on specific code implementation, composite health formula, gRPC Protobuf specs, and container failure demonstration).*

---

## PART 44 — "EXPLAIN THIS PROJECT IN 10 MINUTES"

*(Follow 5-minute structure, conducting live walkthrough of Demo 4 gRPC logs, Demo 5 P2P logs, Demo 7 container stop/start, and code-to-concept mapping).*

---

## PART 45 — CONCEPT -> DEMO -> CODE -> LOG REVISION SHEET

| DS Concept | Frontend Action | Backend Code File | Function / Class | Docker Log Proof |
| :--- | :--- | :--- | :--- | :--- |
| **Service Discovery** | Open `/registry` page | `backend/registry/service_registry.py` | `SatelliteRegistry.register()` | `[REGISTRY] Dynamic Registration SUCCESS` |
| **gRPC Call** | Observatory -> gRPC -> Execute | `backend/communication/grpc_client.py` | `GRPCClientManager.invoke_rpc()` | `[gRPC OUT] Mission Control → SAT-01` |
| **Direct P2P Link** | Observatory -> P2P -> Send | `satellites/satellite_node.py` | `send_to_peer()`, `receive_p2p()` | `[SAT-01 DIRECT P2P OUTGOING]` |
| **RabbitMQ Queue** | View Telemetry charts | `backend/communication/rabbitmq_manager.py` | `RabbitMQManager.publish_telemetry()` | `[RABBITMQ PUBLISH] producer=SAT-03` |
| **WebSocket Stream**| View Dashboard badge | `backend/communication/websocket_manager.py` | `ConnectionManager.broadcast()` | `[WEBSOCKET BROADCAST] event_type=...` |
| **Failure Detector** | Stop container `SAT-02` | `backend/main.py` | `heartbeat_sweeper_task()` | `[FAILURE DETECTOR] SAT-02 heartbeat timed out!` |
| **Failure Recovery** | Start container `SAT-02` | `satellites/satellite_node.py` | `start_autonomous_loop()` | `[RECOVERY] Mission Control ← SAT-02` |
| **Ring Election** | Topology -> Run Election | `backend/registry/service_registry.py` | `run_ring_election()` | `[RING ELECTION COMPLETED] Leader=SAT-05` |

---

## PART 46 — IMPLEMENTATION TRUTH TABLE

| Feature / Concept | Implementation Status | Evidence / Verification |
| :--- | :--- | :--- |
| **Dynamic Service Registry** | `IMPLEMENTED` | `backend/registry/service_registry.py` (`SatelliteRegistry`) |
| **Synchronous gRPC Calls** | `IMPLEMENTED` | `proto/satellite.proto` & `grpc_client.py` (`invoke_rpc`) |
| **Direct Satellite P2P Link** | `IMPLEMENTED` | `satellites/satellite_node.py` (`send_to_peer`) |
| **RabbitMQ AMQP Decoupling** | `IMPLEMENTED` | `backend/communication/rabbitmq_manager.py` |
| **WebSocket Live Streaming** | `IMPLEMENTED` | `backend/communication/websocket_manager.py` |
| **Heartbeat Failure Sweeper**| `IMPLEMENTED` | `backend/main.py` (`heartbeat_sweeper_task`) |
| **Composite Health Engine** | `IMPLEMENTED` | `backend/services/health_engine.py` (`calculate_health`) |
| **Fault Simulator Engine** | `IMPLEMENTED` | `backend/faults/fault_simulator.py` (`inject_fault`) |
| **Ring Leader Election** | `IMPLEMENTED` | `backend/registry/service_registry.py` (`run_ring_election`) |
| **PostgreSQL Persistence** | `IMPLEMENTED` | `backend/database/models.py` & `satellite-postgres` container |
| **WebRTC Signaling** | `IMPLEMENTED` | `backend/communication/webrtc_signaling.py` (SDP Offer/Answer) |
| **Lamport Logical Clock** | `INTERFACE / EXTENSION POINT` | `ILamportClock` interface in `backend/fa2_extensions/interfaces.py` |
| **Vector Clock Sync** | `INTERFACE / EXTENSION POINT` | `IVectorClock` interface in `backend/fa2_extensions/interfaces.py` |
| **Distributed Mutex** | `INTERFACE / EXTENSION POINT` | `IDistributedMutex` interface in `backend/fa2_extensions/interfaces.py` |
| **Chandy-Lamport Snapshot**| `INTERFACE / EXTENSION POINT` | `IGlobalStateSnapshot` interface in `backend/fa2_extensions/interfaces.py` |

---

## PART 47 — COMMON VIVA TRAPS & MYTHS

- ❌ **Trap 1**: Claiming Docker makes the system distributed.  
  *✔ Truth*: Docker provides **containerization infrastructure**. The distributed nature comes from 5 independent processes communicating over sockets.
- ❌ **Trap 2**: Claiming HTTP REST calls are gRPC.  
  *✔ Truth*: `POST /api/rpc/invoke` is an HTTP request from Frontend to Mission Control. The subsequent call from Mission Control to `satellite-01:5001` is gRPC.
- ❌ **Trap 3**: Claiming P2P messages pass payload through Mission Control.  
  *✔ Truth*: Mission Control triggers the command, but payload data travels directly from `satellite-01` to `satellite-04:6004`.
- ❌ **Trap 4**: Claiming Lamport / Vector clocks are fully executable.  
  *✔ Truth*: They are abstract interfaces (`ILamportClock`, `IVectorClock`) reserved for FA-2 extensions.
- ❌ **Trap 5**: Claiming WebSockets and RabbitMQ do the same thing.  
  *✔ Truth*: WebSockets stream events to browser UI clients; RabbitMQ queues AMQP telemetry messages between microservices.

---

## PART 48 — FINAL MASTER SYSTEM ARCHITECTURE DIAGRAM

```
+-----------------------------------------------------------------------------------+
|                                 REACT FRONTEND                                    |
|                      (Port 3000 | mission-control-frontend)                        |
+------------------------------------------+----------------------------------------+
                                           |
                              HTTP REST & WebSocket (/ws)
                                           |
                                           v
+-----------------------------------------------------------------------------------+
|                             MISSION CONTROL BACKEND                               |
|                     (Port 8000 | mission-control-backend)                           |
|                                                                                   |
|  +--------------------+  +----------------------+  +---------------------------+  |
|  |  Service Registry  |  |  Health Engine       |  |  Heartbeat Sweeper (10s)  |  |
|  +--------------------+  +----------------------+  +---------------------------+  |
|  +--------------------+  +----------------------+  +---------------------------+  |
|  |  gRPC Client Mgr   |  |  WebSocket Manager   |  |  Fault Simulator Engine   |  |
|  +--------------------+  +----------------------+  +---------------------------+  |
+---------+----------------------------+----------------------------+---------------+
          |                            |                            |
    gRPC Channels                AMQP 0-9-1                    SQLAlchemy Async
    (Ports 5001-5005)            (Port 5672)                    (Port 5432)
          |                            |                            |
          v                            v                            v
+-------------------+        +--------------------+       +-------------------+
| SATELLITE NODES   |        |  RABBITMQ BROKER   |       |   POSTGRESQL DB   |
| SAT-01 .. SAT-05  |        | (satellite-rabbitmq)|       | (satellite-postgres|
+---------+---------+        +--------------------+       +-------------------+
          |
    Direct P2P Link (HTTP/JSON)
    (Ports 6001 <-> 6004)
          |
          v
+-------------------+
|  peer-to-peer     |
+-------------------+
```
