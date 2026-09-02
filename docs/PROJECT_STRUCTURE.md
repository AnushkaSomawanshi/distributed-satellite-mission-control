# Repository Project Structure & File Map

A comprehensive directory guide mapping repository layout, module responsibilities, database schemas, and architectural boundaries in the **Distributed Satellite Monitoring System**.

---

## 1. Repository Directory Tree

```
DS-Project/
├── README.md                           # Main Project Entrypoint & Overview
├── docker-compose.yml                  # Blueprint for 9 Docker Compose services
├── satellite_system.db                 # SQLite local database (dev fallback)
├── docs/                               # Engineering Documentation Suite
│   ├── ARCHITECTURE.md                 # System Architecture & Component Diagrams
│   ├── DISTRIBUTED_SYSTEMS.md          # Academic Syllabus & Viva Q&A Guide
│   ├── COMMUNICATION.md                # Multi-Protocol Communication Manual
│   ├── FAULT_TOLERANCE.md              # Heartbeat TTL Sweeper & Fault Injection
│   ├── SERVICE_DISCOVERY.md            # Dynamic Name & Endpoint Registry
│   ├── LEADER_ELECTION.md              # Ring Leader Election Consensus
│   ├── DEPLOYMENT.md                   # Docker Compose & Network Configuration
│   ├── API.md                          # REST & WebSocket API Specification
│   ├── DEMO_GUIDE.md                   # Teacher Presentation & Demonstration Guide
│   ├── TESTING.md                      # QA Test Suite & Verification Matrix
│   └── PROJECT_STRUCTURE.md            # File Map & Module Responsibilities
├── backend/                            # FastAPI Mission Control Service
│   ├── communication/                  # Protocol Communication Managers
│   │   ├── grpc_client.py              # Async gRPC client wrapper for satellite RPCs
│   │   ├── rabbitmq_manager.py         # Async AMQP broker connection & listener
│   │   ├── webrtc_signaling.py         # WebRTC SDP offer/answer & ICE candidate manager
│   │   └── websocket_manager.py        # Connection pool & event broadcaster
│   ├── database/                       # Database Session & Models
│   │   ├── db.py                       # Async SQLAlchemy database engine setup
│   │   └── models.py                   # ORM models (Satellite, Telemetry, Events)
│   ├── fa2_extensions/                 # Abstract Interfaces for Advanced DS Concepts
│   │   └── interfaces.py               # Abstract base classes (Lamport, Vector, Mutex)
│   ├── faults/                         # Fault Injection Engine
│   │   └── fault_simulator.py          # Anomaly simulator & node status override
│   ├── models/                         # Pydantic Schemas
│   │   └── schemas.py                  # API Request/Response data validation schemas
│   ├── registry/                       # Dynamic Service Registry & Consensus
│   │   └── service_registry.py         # In-memory registry & Ring leader election
│   ├── services/                       # Business Logic & Algorithms
│   │   └── health_engine.py            # Multi-metric 0-100% health calculation
│   ├── config.py                       # Pydantic environment configuration settings
│   └── main.py                         # FastAPI Router, Lifespan, & Sweeper Task
├── satellites/                         # Satellite Microservice implementation
│   └── satellite_node.py               # Autonomous Satellite process (SAT-01..05)
├── proto/                              # Protocol Buffer Definitions
│   └── satellite.proto                 # gRPC Service Contract definition
├── frontend/                           # React 18 / Vite Observability UI
│   ├── src/
│   │   ├── components/                 # Reusable UI components
│   │   │   ├── ExecutionTrace.jsx      # Leader election visual step-by-step trace
│   │   │   ├── Header.jsx              # Navigation header & dynamic summary badges
│   │   │   └── Sidebar.jsx             # Navigation sidebar menu
│   │   ├── pages/                      # Application Page Views
│   │   │   ├── CommunicationObservatory.jsx # Multi-protocol evidence inspector
│   │   │   ├── CommunicationReplay.jsx # Event history playback view
│   │   │   ├── ConstellationMap.jsx    # Interactive topology canvas
│   │   │   ├── DistributedConcepts.jsx # Syllabus matrix & concept evidence
│   │   │   ├── FaultSimulatorPage.jsx  # Interactive fault injection panel
│   │   │   ├── LiveTelemetryPage.jsx   # Stream-oriented Recharts line graphs
│   │   │   ├── MiddlewarePage.jsx      # AMQP broker statistics view
│   │   │   ├── MissionOverview.jsx     # Main overview dashboard & node table
│   │   │   ├── MultimediaPage.jsx      # WebRTC signaling inspector view
│   │   │   ├── SatelliteRegistryPage.jsx # Dynamic lookup discovery table
│   │   │   ├── SystemHealthDemo.jsx    # Health engine calculator view
│   │   │   └── TeacherQuestionsPage.jsx # Interactive viva preparation Q&A
│   │   ├── App.jsx                     # Top-level router & central WebSocket listener
│   │   ├── main.jsx                    # React DOM entrypoint
│   │   └── index.css                   # Custom glassmorphism Tailwind styling
│   ├── package.json                    # Frontend dependencies (React, Recharts, Lucide)
│   └── vite.config.js                  # Vite server & backend proxy configuration
├── docker/                             # Docker Build Configuration
│   ├── Dockerfile.backend              # Dockerfile for FastAPI Mission Control
│   ├── Dockerfile.frontend             # Dockerfile for React/Vite UI
│   └── Dockerfile.satellite            # Dockerfile for Satellite microservices
├── scripts/                            # Utility & Maintenance Scripts
│   ├── run_local.py                    # Non-Docker local runner script
│   └── generate_proto.py               # Protobuf code generation utility
└── tests/                              # Automated Test Suite
    ├── test_health_engine.py           # Unit tests for HealthEngine formula
    ├── test_registry.py                # Unit tests for ServiceRegistry & TTL sweep
    └── test_api.py                     # Integration tests for FastAPI endpoints
```

---

## 2. Source-Code Responsibility Mapping

| Module / Path | Technology | Key Responsibility |
| :--- | :--- | :--- |
| **`backend/main.py`** | FastAPI / Python | Main backend app, REST routing, WebSocket `/ws`, lifespan, heartbeat sweeper task. |
| **`backend/registry/service_registry.py`** | Python | In-memory registry data store, TTL heartbeat failure evaluation, Ring Leader Election. |
| **`backend/services/health_engine.py`** | Python | Pure metric scorer computing 0-100% score from battery, temp, cpu, memory, signal metrics. |
| **`backend/faults/fault_simulator.py`** | Python | Fault injection manager (STOP, RESTART, TEMP_SPIKE, LATENCY, PACKET_LOSS, CPU_OVERLOAD). |
| **`backend/communication/grpc_client.py`** | gRPC / Python | Async gRPC client stubs invoking `GetHealth`, `GetTelemetry`, `ExecuteCommand` on satellites. |
| **`backend/communication/rabbitmq_manager.py`** | aio-pika / AMQP | Async AMQP manager handling queue declaration, telemetry ingestion, and WebSocket forwarding. |
| **`backend/communication/websocket_manager.py`** | FastAPI WebSockets | Connection pool manager broadcasting real-time JSON events to active React clients. |
| **`satellites/satellite_node.py`** | Python / Asyncio | Autonomous satellite microservice, stepping telemetry, issuing heartbeats, hosting gRPC & P2P. |
| **`proto/satellite.proto`** | Protocol Buffers v3 | Contract defining `SatelliteService` RPC methods and Protobuf message structures. |
| **`frontend/src/App.jsx`** | React 18 | Central state manager, WebSocket listener, rolling telemetry history accumulator. |
| **`docker-compose.yml`** | Docker Compose | Multi-container blueprint defining ports, environment variables, healthchecks, bridge network. |
