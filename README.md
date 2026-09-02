# Distributed Satellite Monitoring & Mission Control System

A containerized, resilient Distributed Systems platform simulating a constellation of Low Earth Orbit (LEO) satellite microservices communicating with a Mission Control backend over gRPC, RabbitMQ AMQP, WebSockets, HTTP REST, P2P, and WebRTC.

---

## 1. Project Overview

The **Distributed Satellite Monitoring & Mission Control System** models an orbital satellite constellation (`SAT-01` through `SAT-05`) monitored and orchestrated by an autonomous Mission Control backend. Each satellite runs as an isolated microservice process within a Docker container, generating real-time telemetry, computing local metrics, exchanging peer-to-peer telemetry payloads, and communicating with Mission Control.

Mission Control maintains an authoritative dynamic Service Registry, tracks node liveness using configurable heartbeat TTL failure detectors, provides real-time WebSockets telemetry broadcasting, and presents a live interactive React/Vite observability dashboard.

---

## 2. Problem Statement

Modern orbital constellations consist of autonomous satellite nodes operating in harsh environments subject to orbital displacement, thermal fluctuations, radiation-induced hardware failures, and intermittent ground-station connectivity.

Monitoring such systems requires:
- **Independent Node Autonomy**: Nodes must generate local telemetry and maintain P2P links without centralized control.
- **Dynamic Service Discovery**: Satellites must dynamically register network endpoints (gRPC, P2P) upon orbital deployment.
- **Fault Detection & Resiliency**: Automated detection of dead or unresponsive nodes without locking up system state.
- **Multi-Protocol Communication**: Synchronous RPC for control actions, asynchronous messaging for telemetry queues, WebSockets for live monitoring, and direct P2P for inter-satellite routing.
- **Dynamic Leader Election**: Autonomous selection of a coordinator node among active constellation members.

---

## 3. Objectives

- **Multi-Service Architecture**: Deploy 5 satellite nodes (`SAT-01` to `SAT-05`), FastAPI Mission Control, PostgreSQL, RabbitMQ, and React frontend in Docker Compose.
- **Live Observability**: Provide live stream-oriented telemetry line charts and dynamic discovery tables backed exclusively by actual backend state.
- **Fault Tolerance & Recovery**: Demonstrate automatic heartbeat failure detection (`> 10.0s` TTL) and autonomous node recovery upon container restart.
- **Multi-Protocol Proof**: Implement and observe gRPC, RabbitMQ AMQP, WebSockets, direct P2P TCP links, and WebRTC signaling.
- **Consensus & Coordination**: Execute Ring Leader Election where active constellation nodes vote on the coordinator node.

---

## 4. Key Features

- **Dynamic Service Registry**: Auto-registers satellite endpoints (`grpc_port`, `p2p_port`, `capabilities`, `hostname`).
- **Heartbeat Liveness Sweeper**: Background sweeper running every 3s checking node TTL (`10.0s`).
- **Health Engine**: Multi-metric weighted health scoring (Battery 25%, Temperature 25%, CPU 20%, Memory 15%, Signal 15%).
- **Live Telemetry Stream**: WebSocket stream (`/ws`) delivering real-time metric updates to continuous line charts.
- **Controlled Fault Injection**: Inject CPU overload, battery drain, thermal spikes, latency, and node stops.
- **Ring Leader Election**: Highest active satellite node ID selection algorithm (`SAT-05` nominal leader).
- **Direct P2P Cross-Links**: Direct satellite-to-satellite messaging triggering peer acknowledgments.

---

## 5. Distributed Systems Concepts Demonstrated

| Concept | Project Implementation | Documentation |
| :--- | :--- | :--- |
| **Distributed Architecture** | 9 containerized services communicating over Docker network | [ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| **Remote Procedure Calls (RPC)** | Protocol Buffers & gRPC (`SatelliteService`) | [COMMUNICATION.md](docs/COMMUNICATION.md) |
| **Message-Oriented Middleware** | RabbitMQ AMQP exchange & telemetry consumer queue | [COMMUNICATION.md](docs/COMMUNICATION.md) |
| **Stream-Oriented Real-Time Updates** | FastAPI WebSockets (`/ws`) broadcasting to React UI | [COMMUNICATION.md](docs/COMMUNICATION.md) |
| **Peer-to-Peer (P2P) Cross-Links** | Direct inter-satellite HTTP/TCP messaging (`/p2p/send_to_peer`) | [COMMUNICATION.md](docs/COMMUNICATION.md) |
| **Dynamic Naming & Discovery** | In-memory `SatelliteRegistry` with heartbeat lookup | [SERVICE_DISCOVERY.md](docs/SERVICE_DISCOVERY.md) |
| **Fault Detection & Liveness** | 10.0s TTL failure detector sweeper & status transition | [FAULT_TOLERANCE.md](docs/FAULT_TOLERANCE.md) |
| **Leader Election & Consensus** | Ring Leader Election algorithm (highest active node wins) | [LEADER_ELECTION.md](docs/LEADER_ELECTION.md) |
| **Virtualization & Containerization** | Docker Compose multi-container deployment blueprint | [DEPLOYMENT.md](docs/DEPLOYMENT.md) |

---

## 6. System Architecture

Mission Control acts as the central observability and orchestration hub, communicating with 5 satellite microservices across isolated Docker network bridges.

```
+-------------------------------------------------------------------------------+
|                             REACT FRONTEND (3000)                             |
|       Mission Overview | Service Registry | Live Telemetry | Observatory      |
+--------------------------------───────▲───────────────────────────────────────+
                                        │ WebSockets / REST API
+--------------------------------───────▼───────────────────────────────────────+
|                        MISSION CONTROL BACKEND (8000)                         |
|   ServiceRegistry | HealthEngine | FaultSimulator | gRPC Manager | AMQP Bus   |
+──────────▲────────────────────────────▲───────────────────────────▲───────────+
           │                            │                           │
  gRPC /   │ HTTP Heartbeats            │ AMQP Message              │ REST/Signaling
  Protobuf │ & Registration             │ Telemetry Exchange        │ 
           │                            │                           │
+──────────▼───────────+    +───────────▼───────────+    +──────────▼───────────+
|     SATELLITE 01     |<==>|     SATELLITE 02     |<==>|     SATELLITE 03...  |
| gRPC:5001 P2P:6001   |P2P | gRPC:5002 P2P:6002   |P2P | gRPC:5003 P2P:6003   |
+----------------------+    +----------------------+    +----------------------+
```

*For complete details, view [ARCHITECTURE.md](docs/ARCHITECTURE.md).*

---

## 7. Technology Stack

| Layer | Technology | Purpose | Implementation Location |
| :--- | :--- | :--- | :--- |
| **Frontend** | React 18 + Vite + TailwindCSS + Recharts | Live Observability & Mission Control UI | `frontend/src/` |
| **Backend API** | FastAPI + Uvicorn | Async REST API & WebSocket Server | `backend/main.py` |
| **Satellite Nodes** | Python 3.11 + Asyncio + HTTPX | Microservice satellite simulation processes | `satellites/satellite_node.py` |
| **RPC Framework** | gRPC + Protocol Buffers v3 | High-performance binary remote invocation | `proto/satellite.proto`, `backend/communication/grpc_client.py` |
| **Message Broker** | RabbitMQ 3.9 AMQP | Message-oriented telemetry pub-sub queue | `backend/communication/rabbitmq_manager.py` |
| **Database** | PostgreSQL 15 + AsyncPG + SQLAlchemy | Persistent logging of events and telemetry | `backend/database/` |
| **Containerization** | Docker + Docker Compose | Isolated multi-service network orchestration | `docker-compose.yml`, `docker/` |

---

## 8. Project Structure Overview

```
DS-Project/
├── README.md                           # Main Project Entrypoint
├── docs/                               # Detailed Engineering Documentation
│   ├── ARCHITECTURE.md                 # System Architecture & Component Mapping
│   ├── DISTRIBUTED_SYSTEMS.md          # Academic Syllabus & Viva Mapping
│   ├── COMMUNICATION.md                # Multi-Protocol Communication Models
│   ├── FAULT_TOLERANCE.md              # Failure Detection & Recovery Mechanics
│   ├── SERVICE_DISCOVERY.md            # Dynamic Name & Endpoint Discovery
│   ├── LEADER_ELECTION.md              # Ring Leader Election Algorithm
│   ├── DEPLOYMENT.md                   # Docker Compose & Network Setup
│   ├── API.md                          # REST API & WebSocket Interface Specification
│   ├── DEMO_GUIDE.md                   # Step-by-Step Teacher Demonstration Guide
│   ├── TESTING.md                      # Verification Matrix & Automated Test Suite
│   └── PROJECT_STRUCTURE.md            # Directory Layout & Responsibility Matrix
├── backend/                            # FastAPI Mission Control Service
│   ├── communication/                  # gRPC, RabbitMQ, WebSocket, WebRTC handlers
│   ├── database/                       # Async SQLAlchemy models & db session
│   ├── fa2_extensions/                 # Abstract interfaces for advanced DS concepts
│   ├── faults/                         # Fault Injection Engine
│   ├── registry/                       # Dynamic Service Registry & Ring Election
│   ├── services/                       # Health Calculation Engine
│   └── main.py                         # FastAPI Application Router & Lifespan
├── satellites/                         # Satellite Microservice implementation
│   └── satellite_node.py               # Autonomous Satellite process
├── proto/                              # Protocol Buffer Definitions
│   └── satellite.proto                 # gRPC Service Contract
├── docker/                             # Dockerfiles for Backend, Satellites, Frontend
└── docker-compose.yml                  # Production Blueprint for 9 Services
```

*For complete file breakdown, view [PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md).*

---

## 9. System Components

1. **Mission Control Backend (`backend/main.py`)**: Core FastAPI hub hosting registry, failure sweeper, WebSocket manager, and RPC clients.
2. **Satellite Nodes (`satellites/satellite_node.py`)**: 5 independent instances (`SAT-01`..`SAT-05`) executing autonomous telemetry steps, HTTP heartbeats, gRPC servers, and P2P receivers.
3. **Service Registry (`backend/registry/service_registry.py`)**: Manages dynamic node registrations, calculates heartbeat TTL timeouts, and executes Ring Leader Election.
4. **Health Engine (`backend/services/health_engine.py`)**: Computes weighted health scores (0-100%) and assigns status (`HEALTHY`, `WARNING`, `CRITICAL`, `OFFLINE`).
5. **Fault Simulator (`backend/faults/fault_simulator.py`)**: Injects metric anomalies, network delays, packet drops, and node failure overrides.
6. **Frontend UI (`frontend/src/`)**: React 18 single-page application providing live dashboards, telemetry graphs, and fault injection triggers.

---

## 10. Communication Mechanisms

The system implements 5 distinct communication paradigms:
1. **gRPC / Protocol Buffers**: Synchronous unary RPCs for node diagnostics and control (`GetHealth`, `GetTelemetry`, `ExecuteCommand`).
2. **RabbitMQ AMQP**: Asynchronous message-oriented pub-sub queue for telemetry ingestion.
3. **WebSockets**: Real-time server-to-client streaming push for telemetry updates and system events.
4. **Direct P2P Cross-Links**: Direct HTTP/TCP communications between satellite nodes without backend relay.
5. **WebRTC Signaling**: Peer connection signaling and ICE candidate exchange handler.

*For complete details, view [COMMUNICATION.md](docs/COMMUNICATION.md).*

---

## 11. Fault Tolerance & Liveness

The system guarantees fault detection through an active **Heartbeat TTL Sweeper**:
- Satellite nodes transmit heartbeats every `2.0 seconds`.
- Mission Control runs a background task every `3.0 seconds` scanning registered nodes.
- If `time.time() - last_heartbeat > 10.0s`, the node status transitions to `OFFLINE` and a `NODE_DISCONNECTED` event is broadcast over WebSockets.
- Container restart re-triggers dynamic registration and restores node status to `HEALTHY`.

*For complete details, view [FAULT_TOLERANCE.md](docs/FAULT_TOLERANCE.md).*

---

## 12. Service Discovery

Nodes dynamically discover network endpoints without hardcoded IP lists:
- Satellites issue `POST /api/satellites/register` upon boot.
- Metadata includes `satellite_id`, `node_id`, `hostname`, `address`, `grpc_port`, `p2p_port`, and `capabilities`.
- Mission Control exposes `GET /api/satellites` to populate the frontend lookup table.

*For complete details, view [SERVICE_DISCOVERY.md](docs/SERVICE_DISCOVERY.md).*

---

## 13. Leader Election

Consensus and coordination are established via **Ring Leader Election**:
- Logical Ring: `SAT-01 ➔ SAT-02 ➔ SAT-03 ➔ SAT-04 ➔ SAT-05 ➔ SAT-01`.
- Initiator sends election message circulating the ring.
- Active nodes append their ID; `OFFLINE` nodes are automatically bypassed.
- Node with the highest active ID is elected leader (`SAT-05` under nominal conditions).

*For complete details, view [LEADER_ELECTION.md](docs/LEADER_ELECTION.md).*

---

## 14. Docker Deployment Architecture

The system deploys 9 isolated services over a custom Docker Compose bridge network:
- `mission-control-frontend` (Port `3000`)
- `mission-control-backend` (Port `8000`)
- `satellite-01` through `satellite-05` (gRPC Ports `5001-5005`, P2P Ports `6001-6005`)
- `satellite-postgres` (Port `5432`)
- `satellite-rabbitmq` (Ports `5672`, `15672`)

*For complete details, view [DEPLOYMENT.md](docs/DEPLOYMENT.md).*

---

## 15. Installation & Prerequisites

### Requirements:
- Docker Desktop (with Docker Compose v2+)
- Python 3.11+ (optional, for local client testing)
- Node.js 18+ (optional, for local frontend dev)

---

## 16. Running the System

Execute the following commands from the project root:

```powershell
# 1. Stop existing containers
docker compose down

# 2. Build and launch all 9 services in detached mode
docker compose up -d --build

# 3. Verify all services are Up and healthy
docker compose ps
```

---

## 17. Accessing System Interfaces

- **Mission Control Frontend Dashboard**: `http://localhost:3000/`
- **Satellite Service Registry**: `http://localhost:3000/registry`
- **Live Telemetry Line Charts**: `http://localhost:3000/telemetry`
- **Communication Observatory**: `http://localhost:3000/observatory`
- **FastAPI OpenAPI Swagger Documentation**: `http://localhost:8000/docs`
- **RabbitMQ Management Dashboard**: `http://localhost:15672/` (Credentials: `guest` / `guest`)

---

## 18. Testing & Verification

Run automated test suites inside the virtual environment:

```powershell
pytest tests/
```

*For complete test matrix, view [TESTING.md](docs/TESTING.md).*

---

## 19. Failure Demonstration

Test distributed failure detection and autonomous recovery:

```powershell
# 1. Stop container satellite-02
docker compose stop satellite-02

# Observe: Mission Control detects heartbeat loss (>10s TTL), marks SAT-02 OFFLINE, and broadcasts state to UI.

# 2. Restart container satellite-02
docker compose start satellite-02

# Observe: SAT-02 re-registers, heartbeats resume, and state recovers to HEALTHY.
```

---

## 20. Implementation Status & Limitations

| Feature / Concept | Implementation Status | Implementation Notes |
| :--- | :--- | :--- |
| **Service Registry & Discovery** | **FULLY IMPLEMENTED** | Dynamic registration & REST query lookup (`/api/satellites`) |
| **Heartbeat Failure Sweeper** | **FULLY IMPLEMENTED** | 10.0s TTL sweeper task in `backend/main.py` |
| **Multi-Metric Health Engine** | **FULLY IMPLEMENTED** | Weighted health formula in `backend/services/health_engine.py` |
| **gRPC Control RPCs** | **FULLY IMPLEMENTED** | Proto v3 definitions in `proto/satellite.proto` |
| **RabbitMQ AMQP Pub-Sub** | **FULLY IMPLEMENTED** | Real-time queue ingestion with fallback mode |
| **WebSocket Streaming** | **FULLY IMPLEMENTED** | Broadcast manager in `backend/communication/websocket_manager.py` |
| **Direct P2P Links** | **FULLY IMPLEMENTED** | Inter-satellite HTTP/TCP trigger in `satellites/satellite_node.py` |
| **Ring Leader Election** | **FULLY IMPLEMENTED** | Ring algorithm in `backend/registry/service_registry.py` |
| **WebRTC Signaling** | **PARTIALLY IMPLEMENTED** | SDP offer/answer exchange stubs in `webrtc_signaling.py` |
| **Lamport & Vector Clocks** | **INTERFACE STUB** | Abstract interfaces defined in `backend/fa2_extensions/interfaces.py` |
| **Chandy-Lamport Snapshots** | **INTERFACE STUB** | Abstract interfaces defined in `backend/fa2_extensions/interfaces.py` |

---

## 21. Documentation Index

Detailed engineering and viva documentation files are located in the [`docs/`](docs/) directory:

- 🏗️ **[System Architecture](docs/ARCHITECTURE.md)**: Detailed component diagrams and file responsibility mappings.
- 🎓 **[Distributed Systems Syllabus Matrix](docs/DISTRIBUTED_SYSTEMS.md)**: Academic topic mapping, code evidence, and viva Q&A.
- 📡 **[Communication Architecture](docs/COMMUNICATION.md)**: gRPC, RabbitMQ, WebSockets, P2P, and WebRTC protocols.
- 🛡️ **[Fault Tolerance & Failure Recovery](docs/FAULT_TOLERANCE.md)**: Heartbeat mechanics, TTL sweeper, and fault injection.
- 🔍 **[Service Registry & Discovery](docs/SERVICE_DISCOVERY.md)**: Naming, addressing, dynamic registration, and lookup.
- 👑 **[Leader Election](docs/LEADER_ELECTION.md)**: Ring election algorithm, ring topology, and trace logs.
- 🐳 **[Deployment & Containerization](docs/DEPLOYMENT.md)**: Docker Compose blueprint, ports, and troubleshooting.
- 🔌 **[API Documentation](docs/API.md)**: REST endpoints, request/response schemas, and WebSocket events.
- 🎬 **[Teacher Demonstration Guide](docs/DEMO_GUIDE.md)**: Step-by-step presentation script and viva prompts.
- 🧪 **[Testing & Verification](docs/TESTING.md)**: Automated tests, manual test matrix, and verification status.
- 📂 **[Project Structure](docs/PROJECT_STRUCTURE.md)**: Repository map, module responsibilities, and data models.
