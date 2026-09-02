# DISTRIBUTED SYSTEMS PROJECT — COMPLETE LEARNING, CODE MAPPING, VERIFICATION & DEMONSTRATION MANUAL

**Project Title**: Distributed Satellite Constellation Health Monitoring & Autonomous Fault Recovery System  
**Target Syllabus**: FA-1 Distributed Systems (Unit 1: Introduction to Distributed Systems & Unit 2: Communication)  
**Target Audience**: Student presenting to a Distributed Systems Professor, Project Evaluator, or Examiner.

---

# PART 1 — UNDERSTAND THE PROJECT FIRST

## 1.1 Problem Statement

### Comprehensive Problem Statement (For Exam Documentation / Report)
Modern Low Earth Orbit (LEO) satellite constellations (e.g. Starlink, OneWeb, Earth Observation swarms) consist of dozens to thousands of autonomous satellites operating in harsh space environments. Each satellite continuously monitors internal subsystem health (battery state of charge, solar flare thermal exposure, processor load, memory consumption, signal-to-noise ratios) and orbital trajectory parameters.

Relying on a traditional centralized monolithic architecture to collect and process all health data introduces significant operational risks:
1. **Single Point of Failure**: If the ground station or central server crashes, visibility over the entire satellite constellation is lost.
2. **Bandwidth & Latency Bottlenecks**: Transmitting high-frequency telemetry from every satellite back to a single ground station creates severe network congestion and propagation delays.
3. **Lack of Autonomy & Resilience**: Satellites cannot coordinate directly with adjacent peers during loss-of-signal events or orbital eclipse phases.

### Why Does This Require a Distributed System?
To solve these challenges, the system is architected as a **Genuine Distributed System**:
- **Independent Autonomy**: Each satellite operates as a self-contained microservice process (`SAT-01` to `SAT-05`) maintaining its local orbit telemetry state.
- **Dynamic Service Discovery**: Satellites dynamically register their network endpoints (gRPC, P2P, hostnames) with a central Satellite Registry.
- **Multi-Protocol Communication**: Asynchronous telemetry publishing via RabbitMQ message broker, high-frequency WebSockets telemetry streaming, synchronous gRPC Remote Procedure Calls, direct inter-satellite P2P cross-links, and WebRTC video streaming.
- **Fault Tolerance & Availability**: If a satellite node crashes or experiences a communications outage, the remaining constellation nodes continue operating seamlessly. When the node recovers, it dynamically re-registers and resumes heartbeat reporting.

### Short Verbal Problem Statement (30-Second Examiner Answer)
> *"Professor, modern satellite constellations cannot rely on a single central server because a crash or network delay would blind Mission Control. Our project implements a genuine distributed system where 5 independent satellite microservices generate telemetry autonomously, communicate using gRPC, RabbitMQ, WebSockets, WebRTC, and direct P2P cross-links, and detect node failures using dynamic heartbeat timeouts so the constellation remains operational even when nodes crash."*

---

## 1.2 System Architecture Overview

```
                              ┌──────────────────────────────────────────────┐
                              │         React Mission Control Frontend       │
                              │           (Port 3000 / Vite Dev 5173)        │
                              └──────┬───────────────────▲───────────────────┘
                                     │ HTTP REST         │ WebSockets / WebRTC
                                     ▼                   │
                              ┌──────────────────────────┴───────────────────┐
                              │      Mission Control Backend Service         │
                              │            (FastAPI - Port 8000)             │
                              │  - Satellite Registry & Health Engine        │
                              │  - gRPC Controller & Client Pool             │
                              │  - RabbitMQ Consumer & Stream Broadcaster    │
                              │  - Fault & Network Simulator                 │
                              │  - Event Logger & Persistence Store          │
                              └──────┬───────────────────┬───────────────────┘
                                     │                   │
                     RabbitMQ Broker │                   │ gRPC Calls (Ports 5001-5005)
                     (Port 5672/15672)                   │ HTTP P2P Direct Links
                                     │                   │
        ┌────────────────────────────┼───────────────────┼────────────────────────────┐
        │                            ▼                   ▼                            │
 ┌──────┴──────┐              ┌──────────────┐    P2P    ┌──────────────┐      ┌──────┴──────┐
 │   SAT-01    │ ◄──────────► │    SAT-02    │ ◄───────► │    SAT-03    │ ...  │   SAT-05    │
 │ (gRPC 5001) │   P2P Link   │ (gRPC 5002) │ P2P Link  │ (gRPC 5003) │      │ (gRPC 5005) │
 └─────────────┘              └──────────────┘           └──────────────┘      └─────────────┘
        ▲                            ▲                          ▲                    ▲
        └────────────────────────────┴──────────────────────────┴────────────────────┘
                                  PostgreSQL Database (Port 5432)
```

---

## 1.3 System Objective & Runtime Lifecycle

1. **System Startup**:
   - PostgreSQL database initializes schema tables (`satellites`, `telemetry_logs`, `communication_events`, `fault_logs`).
   - RabbitMQ message broker creates `telemetry.exchange` (fanout type) and `telemetry.queue`.
   - Mission Control FastAPI backend starts on port 8000 and connects to PostgreSQL & RabbitMQ.
   - Satellites `SAT-01` through `SAT-05` start as independent processes/containers listening on gRPC ports (5001-5005) and P2P ports (6001-6005).

2. **Registration & Discovery**:
   - Each satellite node sends a dynamic HTTP POST registration request to `/api/satellites/register`, informing Mission Control of its satellite ID, internal node ID, hostname, gRPC port, and P2P port.

3. **Normal Telemetry & Heartbeat Loop**:
   - Every satellite executes an autonomous orbit calculation loop (updating latitude, longitude, solar thermal exposure, battery charge, CPU load).
   - Every satellite sends a periodic heartbeat payload (`POST /api/satellites/heartbeat`) every 2 seconds.
   - Mission Control Health Engine calculates Health Score (0-100%) and updates node status (`HEALTHY`, `WARNING`, `CRITICAL`).
   - Telemetry is published asynchronously to RabbitMQ and broadcast in real-time over WebSockets (`/ws`) to React charts.

4. **Inter-Node Communication**:
   - **gRPC**: Mission Control invokes RPC calls (`GetHealth()`, `Ping()`, `GetSatelliteInfo()`) directly against satellite gRPC ports.
   - **Direct P2P**: `SAT-01` sends direct cross-link packets directly to `SAT-04` (`SAT-01:6001 -> SAT-04:6004`). Mission Control does NOT act as a message relay.
   - **WebRTC**: Browser negotiates SDP offer/answer with backend to render a 1080p animated orbital camera stream.

5. **Failure Detection & Recovery**:
   - Background sweeper task checks `last_heartbeat` timestamps every 3 seconds.
   - If a satellite stops sending heartbeats for >10 seconds, the backend marks it `OFFLINE` and broadcasts a `NODE_DISCONNECTED` event over WebSockets. Remaining nodes continue operating.
   - When the failed satellite restarts, it issues a heartbeat/registration request, instantly recovering to `HEALTHY` state.

---

# PART 2 — COMPLETE ARCHITECTURE & CONTAINER INVENTORY

| Component | Purpose | Technology | Network Port | Location in Repository | Key Class / Function |
| :--- | :--- | :--- | :---: | :--- | :--- |
| **React Frontend** | Orbital Mission Control Dashboard | React 18, Vite, Tailwind CSS | `3000` | `frontend/src/` | `App.jsx`, `Header.jsx`, `Sidebar.jsx` |
| **Mission Control Backend** | REST Orchestrator & Registry | Python 3.11, FastAPI, uvicorn | `8000` | `backend/main.py` | `app`, `receive_heartbeat()`, `invoke_rpc()` |
| **Satellite Node 01** | Microservice Node 1 | Python Process / Docker Container | `5001` (gRPC), `6001` (P2P) | `satellites/satellite_node.py` | `SatelliteNode`, `send_to_peer()` |
| **Satellite Node 02** | Microservice Node 2 | Python Process / Docker Container | `5002` (gRPC), `6002` (P2P) | `satellites/satellite_node.py` | `SatelliteNode`, `send_to_peer()` |
| **Satellite Node 03** | Microservice Node 3 | Python Process / Docker Container | `5003` (gRPC), `6003` (P2P) | `satellites/satellite_node.py` | `SatelliteNode`, `send_to_peer()` |
| **Satellite Node 04** | Microservice Node 4 | Python Process / Docker Container | `5004` (gRPC), `6004` (P2P) | `satellites/satellite_node.py` | `SatelliteNode`, `send_to_peer()` |
| **Satellite Node 05** | Microservice Node 5 | Python Process / Docker Container | `5005` (gRPC), `6005` (P2P) | `satellites/satellite_node.py` | `SatelliteNode`, `send_to_peer()` |
| **Message Broker** | AMQP Pub/Sub Broker | RabbitMQ Alpine | `5672` (AMQP), `15672` (Mgmt) | `backend/communication/rabbitmq_manager.py` | `RabbitMQManager` |
| **Database** | Persistent Event & Log Store | PostgreSQL 15 / SQLite | `5432` | `backend/database/` | `db.py`, `models.py` |

---

# PART 3 — CONCEPT IMPLEMENTATION & VERIFICATION MATRIX

| Distributed Systems Concept | Status | Exact Repository File | Exact Class / Function | What It Does | Demonstration Command / Procedure |
| :--- | :---: | :--- | :--- | :--- | :--- |
| **1. Distributed System** | 🟢 | `satellites/satellite_node.py` | `SatelliteNode` | 5 autonomous processes running concurrently | `docker compose ps` / View ports 5001-5005 |
| **2. Distributed Nodes** | 🟢 | `satellites/satellite_node.py` | `run_satellite()` | Self-contained nodes owning local telemetry state | Stop `SAT-03`; `SAT-01,02,04,05` remain online |
| **3. Client-Server Architecture** | 🟢 | `backend/main.py` | FastAPI `@app` routes | React UI requests REST endpoints from FastAPI | Open `http://localhost:3000` |
| **4. Service Discovery & Naming** | 🟢 | `backend/registry/service_registry.py` | `SatelliteRegistry` | Dynamic mapping of IDs to hostnames & ports | View Satellite Registry table on UI |
| **5. Remote Procedure Call (RPC)** | 🟢 | `backend/communication/grpc_client.py` | `GRPCClientManager.invoke_rpc()` | Synchronous RPC execution over network | Click 'EXECUTE gRPC REQUEST' on Observatory |
| **6. gRPC & Protobuf** | 🟢 | `proto/satellite.proto` | `SatelliteService` | High-performance protobuf binary contracts | `python -m grpc_tools.protoc` |
| **7. Message-Oriented Middleware** | 🟢 | `backend/communication/rabbitmq_manager.py` | `RabbitMQManager` | Decoupled pub/sub telemetry queue publishing | Check RabbitMQ UI `http://localhost:15672` |
| **8. RabbitMQ** | 🟢 | `docker-compose.yml` | `rabbitmq` service | Containerized AMQP message broker on 5672 | `docker compose exec rabbitmq rabbitmq-diagnostics check_running` |
| **9. Producer / Consumer** | 🟢 | `satellites/` & `backend/` | `publish_telemetry()` / `_start_consumer()` | Producer publishes telemetry; consumer processes | View RabbitMQ `telemetry.queue` consumer counter |
| **10. Asynchronous Communication** | 🟢 | `backend/communication/websocket_manager.py` | `ConnectionManager.broadcast()` | Non-blocking telemetry streaming over WebSockets | Observe live updating Recharts line graphs |
| **11. Synchronous Communication** | 🟢 | `backend/communication/grpc_client.py` | `invoke_rpc()` | Blocking RPC call waiting for node response | Inspect RPC latency timing (e.g. 14ms) |
| **12. Heartbeat Monitoring** | 🟢 | `satellites/satellite_node.py` | `send_heartbeat()` | Satellites transmit heartbeat POST every 2s | Inspect backend log `POST /api/satellites/heartbeat 200` |
| **13. Failure Detection** | 🟢 | `backend/registry/service_registry.py` | `sweep_failures()` | Detects missing heartbeats (>10s) & marks `OFFLINE` | Stop `SAT-03`; observe transition to `OFFLINE` |
| **14. Fault Tolerance** | 🟢 | `backend/faults/fault_simulator.py` | `FaultSimulator` | Injects crashes, delays, and sensor spikes safely | Inject 500ms latency on Fault Simulator UI |
| **15. Failure Recovery** | 🟢 | `satellites/satellite_node.py` | `register_with_mission_control()` | Node auto-re-registers on restart | Restart `SAT-03`; observe transition to `HEALTHY` |
| **16. Persistence** | 🟢 | `backend/database/models.py` | `CommunicationEvent`, `TelemetryLog` | Persists telemetry and communication logs to SQL | Query SQLite/PostgreSQL `communication_events` |
| **17. Direct P2P Messaging** | 🟢 | `satellites/satellite_node.py` | `send_to_peer()` | Direct network link `SAT-01 -> SAT-04` without relay | Click 'SEND DIRECT P2P MESSAGE' on Observatory |
| **18. WebRTC / Multimedia** | 🟢 | `backend/communication/webrtc_signaling.py` | `WebRTCOfferRequest` | SDP Offer/Answer signaling for live camera feed | Click 'ESTABLISH WEBRTC CONNECTION' |
| **19. Containerization** | 🟢 | `docker-compose.yml` | Services definition | Virtualization of 9 distinct application containers | `docker compose ps` |
| **20. Logical / Vector Clocks** | 🔵 | `backend/fa2_extensions/interfaces.py` | `ILamportClock`, `IVectorClock` | Code stubs prepared for FA-2 extension | View `interfaces.py` extension points |
| **21. Leader Election** | 🔵 | `backend/fa2_extensions/interfaces.py` | `ILeaderElection` | Code stubs prepared for FA-2 extension | View `interfaces.py` extension points |
| **22. Distributed Mutex** | 🔵 | `backend/fa2_extensions/interfaces.py` | `IDistributedMutex` | Code stubs prepared for FA-2 extension | View `interfaces.py` extension points |
| **23. Global Snapshot** | 🔵 | `backend/fa2_extensions/interfaces.py` | `IGlobalStateSnapshot` | Code stubs prepared for FA-2 extension | View `interfaces.py` extension points |

*(Legend: 🟢 Implemented & Verified in FA-1 | 🔵 Prepared Stub Interface for FA-2 Extension | 🔴 Not Implemented)*

---

# PART 4 — DETAILED CONCEPT LEARNING & VIVA GUIDE

## Concept 1: Service Discovery & Dynamic Naming

### A. What is it?
Service discovery allows distributed nodes to locate each other dynamically over a network without hardcoding IP addresses or port numbers in source code.

### B. Why does Distributed Systems need it?
In cloud/containerized environments, IP addresses change dynamically when services restart. Service discovery resolves symbolic names (e.g. `SAT-03`) to physical network endpoints (`127.0.0.1:5003`).

### C. How does OUR project use it?
When a satellite node starts, it sends a registration request to Mission Control's `SatelliteRegistry` (`backend/registry/service_registry.py`), reporting its ID, hostname, gRPC port, and P2P port. When Mission Control needs to make an RPC call to `SAT-03`, it looks up `SAT-03` in `SatelliteRegistry.lookup("SAT-03")` to retrieve target endpoint `:5003`.

### D. Code Location
- `backend/registry/service_registry.py` -> `SatelliteRegistry` class (Lines 15–110)
- `satellites/satellite_node.py` -> `register_with_mission_control()` (Lines 112 border)

### E. Viva Explanation (30 Seconds)
> *"Professor, we implement dynamic service discovery using a central Satellite Registry. Satellites do not have hardcoded addresses; on startup, each satellite registers its gRPC and P2P ports with Mission Control. When making an RPC call or P2P link, the system looks up the destination in the registry."*

---

## Concept 2: Remote Procedure Call (RPC via gRPC)

### A. What is it?
RPC allows a computer program to cause a subroutine to execute in a different address space (on another process or machine) without the programmer explicitly coding network details.

### B. How OUR project uses it:
We use **gRPC** with binary **Protocol Buffers** (`proto/satellite.proto`). Mission Control issues synchronous `GetHealth()`, `Ping()`, or `GetSatelliteInfo()` calls to target satellite gRPC servers listening on ports 5001–5005.

### C. Code Location
- Contract: `proto/satellite.proto` -> `service SatelliteService`
- Client: `backend/communication/grpc_client.py` -> `GRPCClientManager.invoke_rpc()`
- Server: `satellites/satellite_node.py` -> `SatelliteGrpcServicer`

### D. Demonstration Command
In PowerShell:
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/rpc/invoke" -Method Post -ContentType "application/json" -Body '{"target_satellite_id":"SAT-03","method":"GetHealth"}' | ConvertTo-Json -Depth 5
```
**Expected Output**:
```json
{
  "success": true,
  "method": "GetHealth",
  "target": "SAT-03",
  "latency_ms": 14.2,
  "data": {
    "satellite_id": "SAT-03",
    "status": "HEALTHY",
    "health_score": 100.0,
    "battery_level": 98.5,
    "temperature": 24.0
  }
}
```

---

## Concept 3: Direct Peer-to-Peer (P2P) Communication

### A. What is it?
P2P communication occurs directly between equal peer nodes over a network link without routing messages through a central server or backend relay.

### B. How OUR project uses it:
When `SAT-01` needs to send an orbital handshake or telemetry sync packet to `SAT-04`, `SAT-01` invokes its internal `/p2p/send_to_peer` function. `SAT-01` opens a direct HTTP/socket connection across the network to `SAT-04` at `http://SAT-04:6004/p2p/receive`. Mission Control is **NEVER** a relay.

### C. Code Location
- Sender Node: `satellites/satellite_node.py` -> `send_to_peer()` function
- Receiver Node: `satellites/satellite_node.py` -> `/p2p/receive` endpoint
- Trigger API: `backend/main.py` -> `send_p2p_message()`

### D. Demonstration Command
In PowerShell:
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/p2p/send" -Method Post -ContentType "application/json" -Body '{"source_satellite_id":"SAT-01","destination_satellite_id":"SAT-04","payload":"CROSS_LINK_HANDSHAKE"}' | ConvertTo-Json -Depth 5
```
**Expected Response**:
```json
{
  "success": true,
  "source": "SAT-01",
  "destination": "SAT-04",
  "direct_link": "SAT-01 (127.0.0.1:6001) -> SAT-04 (sat-04:6004)",
  "relay_status": "DIRECT_SATELLITE_TO_SATELLITE (No Mission Control Relay)",
  "latency_ms": 12.4
}
```

---

# PART 5 — RABBITMQ DEEP DIVE

## 5.1 What is RabbitMQ & AMQP?
RabbitMQ is an open-source message broker implementing **AMQP 0-9-1** (Advanced Message Queuing Protocol). It provides asynchronous, decoupled, non-blocking message delivery between producers and consumers.

## 5.2 Key Terminology Mapped to Our Code
- **Producer**: `satellites/satellite_node.py` publishing telemetry frames.
- **Exchange**: `telemetry.exchange` (Fanout exchange created in `backend/communication/rabbitmq_manager.py`).
- **Queue**: `telemetry.queue` (Durable queue bound to exchange).
- **Consumer**: `RabbitMQManager._start_consumer()` processing incoming queue messages and pushing to WebSockets.

## 5.3 Verification Commands (PowerShell)
```powershell
# 1. Verify RabbitMQ is healthy
docker compose exec rabbitmq rabbitmq-diagnostics check_running

# 2. List queues, message counts, and consumer counts
docker compose exec rabbitmq rabbitmqctl list_queues name messages consumers
```
**Expected Output**:
```text
Timeout: 60.000s ...
Listing queues for vhost / ...
name            messages        consumers
telemetry.queue 0               1
```

## 5.4 Management UI Access
- URL: **`http://localhost:15672`**
- Username: `guest`
- Password: `guest`
- What to show teacher: Click **Queues** tab -> click `telemetry.queue` -> view real-time consumer graph and message throughput.

---

# PART 6 — POSTGRESQL & PERSISTENCE DEEP DIVE

## 6.1 Purpose of Database Persistence
While satellite microservices hold transient local orbit state in memory, Mission Control requires persistent storage to record historical events, telemetry logs, communication latency records, and fault injection history.

## 6.2 Data Schema & Models (`backend/database/models.py`)
- `SatelliteModel`: Registry state (`satellite_id`, `grpc_port`, `p2p_port`, `status`, `health_score`).
- `TelemetryLog`: Historical telemetry points (`latitude`, `longitude`, `battery`, `temperature`).
- `CommunicationEvent`: Audit trail of all RPC, RabbitMQ, P2P, and WebRTC events (`event_id`, `source`, `destination`, `protocol`, `latency_ms`).
- `FaultInjectionLog`: Records active/historical fault simulation events.

## 6.3 Database Verification Commands
```powershell
# Query communication events table inside Postgres container
docker compose exec postgres psql -U postgres -d satellite_db -c "SELECT event_id, source, destination, protocol, latency_ms, status FROM communication_events ORDER BY id DESC LIMIT 5;"
```

---

# PART 7 — DOCKER & CONTAINERIZATION DEEP DIVE

## 7.1 Container Inventory in `docker-compose.yml`
Our system deploys **9 independent containers** connected via a custom Docker bridge network:
1. `satellite-postgres` (PostgreSQL 15 on port 5432)
2. `satellite-rabbitmq` (RabbitMQ on ports 5672 / 15672)
3. `mission-control-backend` (FastAPI backend on port 8000)
4. `satellite-01` (Satellite 1 on gRPC 5001 / P2P 6001)
5. `satellite-02` (Satellite 2 on gRPC 5002 / P2P 6002)
6. `satellite-03` (Satellite 3 on gRPC 5003 / P2P 6003)
7. `satellite-04` (Satellite 4 on gRPC 5004 / P2P 6004)
8. `satellite-05` (Satellite 5 on gRPC 5005 / P2P 6005)
9. `mission-control-frontend` (React UI on port 3000)

## 7.2 Docker DNS Service Discovery
Inside the Docker network, containers resolve each other using service names as hostnames:
- Mission Control reaches RabbitMQ via `amqp://guest:guest@rabbitmq:5672/`.
- Mission Control reaches PostgreSQL via `postgres:5432`.
- `SAT-01` reaches Mission Control via `http://mission-control:8000`.
- `SAT-01` communicates directly with `SAT-04` via `http://satellite-04:6004`.

## 7.3 Verification Command
```powershell
docker compose ps
```

---

# PART 8 — HEARTBEAT & FAILURE DETECTION DEMO

## 8.1 Heartbeat Lifecycle
1. Satellite node sends `POST /api/satellites/heartbeat` payload every 2 seconds containing metrics (`battery`, `temperature`, `cpu_usage`).
2. Mission Control updates `registry.last_heartbeat = time.time()`.
3. Background task `heartbeat_sweeper_task()` runs every 3 seconds checking for nodes where `(now - last_heartbeat) > 10.0s`.
4. If timeout exceeds 10s, satellite status transitions to `OFFLINE`.

## 8.2 Safe Failure & Recovery Experiment

### Step 1: Verify Initial State
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/health" | ConvertTo-Json -Depth 5
```
*Expected*: All 5 satellites `healthy: 5`, `offline: 0`.

### Step 2: Stop Satellite 03
```powershell
docker compose stop satellite-03
```

### Step 3: Observe Failure Detection
Wait 12 seconds, then query health API:
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/health" | ConvertTo-Json -Depth 5
```
*Expected*: `status: DEGRADED`, `healthy: 4`, `offline: 1`. Satellites 01, 02, 04, 05 remain 100% operational!

### Step 4: Restart Satellite 03 (Recovery)
```powershell
docker compose start satellite-03
```
Wait 4 seconds, then query health API:
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/health" | ConvertTo-Json -Depth 5
```
*Expected*: `status: HEALTHY`, `healthy: 5`, `offline: 0`. Node 03 dynamically re-registered and recovered!

---

# PART 9 — COMPARISON OF COMMUNICATION MECHANISMS

| Protocol | Communication Style | Sync / Async | Primary Use Case in Our System | Code Location |
| :--- | :--- | :---: | :--- | :--- |
| **REST API** | Client-Server Request/Response | Sync | UI controls, health status, registry queries | `backend/main.py` |
| **gRPC** | Binary RPC over HTTP/2 | Sync | Mission Control -> Satellite command execution (`GetHealth`) | `backend/communication/grpc_client.py` |
| **RabbitMQ** | Message Queue Pub/Sub | Async | Asynchronous decoupled telemetry queue ingestion | `backend/communication/rabbitmq_manager.py` |
| **WebSockets** | Continuous Full-Duplex Stream | Async | Streaming telemetry frames to React line charts (~10 msg/s) | `backend/communication/websocket_manager.py` |
| **P2P** | Direct Satellite Cross-Link | Sync/Async | Direct `SAT-01 -> SAT-04` messaging without backend relay | `satellites/satellite_node.py` (`send_to_peer`) |
| **WebRTC** | PeerConnection SRTP Video Stream | Async | Real-time simulated 1080p orbital camera feed | `backend/communication/webrtc_signaling.py` |

---

# PART 10 — API DOCUMENTATION FOR VIVA

| Method | Endpoint | Purpose | Request Body | Response | Used By |
| :---: | :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/health` | Overall system health summary | None | `{ status, satellites: { healthy, offline } }` | Header & Health View |
| `GET` | `/api/satellites` | List all registered satellite nodes | None | `{ satellites: [...], count: 5 }` | Overview & Registry |
| `POST` | `/api/satellites/register` | Dynamic satellite registration | `{ satellite_id, grpc_port, p2p_port }` | `{ status: "SUCCESS" }` | Satellite startup |
| `POST` | `/api/satellites/heartbeat` | Periodic satellite heartbeat | `{ satellite_id, battery, temp, cpu }` | `{ status: "SUCCESS", health_score }` | Satellite loop |
| `POST` | `/api/rpc/invoke` | Execute gRPC call to satellite | `{ target_satellite_id, method }` | `{ success: true, latency_ms, data }` | Observatory UI |
| `POST` | `/api/p2p/send` | Trigger direct P2P link | `{ source_satellite_id, destination_satellite_id }` | `{ success: true, direct_link, latency_ms }` | Observatory UI |
| `POST` | `/api/faults/inject` | Inject controlled fault | `{ fault_type: "HIGH_LATENCY", target_node }` | `{ status: "SUCCESS", fault }` | Fault Simulator UI |
| `POST` | `/api/webrtc/offer` | WebRTC SDP Offer/Answer | `{ offer_sdp, peer }` | `{ session_id, answer_sdp, codec }` | WebRTC Camera UI |
| `WS` | `/ws` | WebSocket continuous telemetry stream | None | `{ event_type: "TELEMETRY_UPDATED", ... }` | Live Telemetry Charts |

---

# PART 11 — 50 VIVA QUESTIONS & ANSWERS FOR EXAMINER

### Q1: What makes this a distributed system rather than a normal web app?
> **Answer**: Rather than running all satellite logic inside a single monolithic backend server, our project deploys 5 independent satellite microservice processes. Each satellite maintains its local state, operates asynchronously, communicates over distinct network ports, and continues operating even if another node crashes.

### Q2: How does Mission Control know if a satellite has crashed?
> **Answer**: Satellites send heartbeats every 2 seconds. Mission Control runs a background sweeper task (`heartbeat_sweeper_task()`) checking timestamp deltas. If a satellite fails to send heartbeats for >10 seconds (`HEARTBEAT_TIMEOUT_SECONDS`), the sweeper marks the node status as `OFFLINE`.

### Q3: Where is service discovery implemented in your code?
> **Answer**: In `backend/registry/service_registry.py` inside the `SatelliteRegistry` class. Satellites register their IP, gRPC port, and P2P port dynamically upon startup rather than hardcoding addresses.

### Q4: Why did you use RabbitMQ for telemetry?
> **Answer**: High-frequency satellite telemetry generation is inherently asynchronous. RabbitMQ decouples message producers (satellites) from consumers (backend aggregators), preventing API blocking and providing message queuing resilience.

### Q5: How do you prove your P2P communication does not route through Mission Control?
> **Answer**: `satellites/satellite_node.py` exposes a `/p2p/send_to_peer` endpoint. When triggered, `SAT-01` opens a direct HTTP/socket network connection directly to `SAT-04:6004`. Mission Control does not relay the data payload.

### Q6: What happens if RabbitMQ is stopped?
> **Answer**: Our system features an automatic in-memory fallback event queue (`RabbitMQManager.in_memory_queue`) so the application remains 100% functional without crashing.

### Q7: Where are Protocol Buffers defined?
> **Answer**: In `proto/satellite.proto`. The file specifies the gRPC `SatelliteService` contract and message structures for `HealthRequest`, `TelemetryResponse`, `PingRequest`, etc.

### Q8: What does WebRTC provide in your project?
> **Answer**: Real browser-based multimedia streaming. Backend module `webrtc_signaling.py` negotiates SDP offer/answer session parameters to render a live 1080p orbital video canvas.

### Q9: How is Docker Compose used?
> **Answer**: `docker-compose.yml` orchestrates 9 containers across a single bridge network, allowing services to resolve each other by container name (e.g. `mission-control`, `satellite-01`, `rabbitmq`, `postgres`).

### Q10: How will this project extend to FA-2?
> **Answer**: `backend/fa2_extensions/interfaces.py` contains prepared extension interfaces (`ILamportClock`, `IVectorClock`, `ILeaderElection`, `IDistributedMutex`, `IGlobalStateSnapshot`) ready for FA-2 implementation without restructuring core communication loops.

---

# PART 12 — RAPID CODE LOOKUP FOR VIVA

| Teacher Asks | Open File | Class / Function | What to Point Out |
| :--- | :--- | :--- | :--- |
| *"Show me the satellite node code"* | `satellites/satellite_node.py` | `SatelliteNode` | Autonomous orbit step loop and `send_heartbeat()` |
| *"Show me gRPC RPC implementation"* | `proto/satellite.proto` & `backend/communication/grpc_client.py` | `GRPCClientManager` | `SatelliteService` proto contract & `invoke_rpc()` method |
| *"Show me RabbitMQ integration"* | `backend/communication/rabbitmq_manager.py` | `RabbitMQManager` | `telemetry.exchange` fanout exchange & async consumer loop |
| *"Show me direct P2P messaging"* | `satellites/satellite_node.py` | `send_to_peer()` | Direct network transmission to peer satellite port |
| *"Show me failure detection sweeper"* | `backend/main.py` | `heartbeat_sweeper_task()` | Background sweep loop marking nodes `OFFLINE` after 10s |
| *"Show me Health Engine formula"* | `backend/services/health_engine.py` | `HealthEngine.calculate_health()` | Weighted score formula for battery, temp, CPU, memory, signal |
| *"Show me WebSockets streaming"* | `backend/communication/websocket_manager.py` | `ConnectionManager` | Active client connection pool & live broadcast function |
| *"Show me WebRTC signaling"* | `backend/communication/webrtc_signaling.py` | `WebRTCSignalingManager` | SDP Offer/Answer negotiation & VP8 session setup |
| *"Show me Database models"* | `backend/database/models.py` | `CommunicationEvent`, `SatelliteModel` | SQLAlchemy async ORM table declarations |
| *"Show me Docker orchestration"* | `docker-compose.yml` | `services:` | Container declarations for 5 satellites, backend, frontend, broker, DB |
| *"Show me Viva Demo Center UI"* | `frontend/src/pages/SystemHealthDemo.jsx` | `SystemHealthDemo` | 14 preset single-click demonstration triggers |
| *"Show me Teacher Questions UI"* | `frontend/src/pages/TeacherQuestionsPage.jsx` | `TeacherQuestionsPage` | Viva defense question & answer guide |

---

# PART 13 — FINAL REVISION CHEAT SHEET

- **Project Goal**: Software simulation of a 5-satellite LEO constellation with autonomous health monitoring and multi-protocol communication.
- **5 Satellites**: `SAT-01` (5001/6001), `SAT-02` (5002/6002), `SAT-03` (5003/6003), `SAT-04` (5004/6004), `SAT-05` (5005/6005).
- **Communication Protocols**: gRPC (RPC), RabbitMQ (Async Pub/Sub), WebSockets (Real-time Stream), P2P (Direct Network Link), WebRTC (Multimedia Stream).
- **Key URLs**:
  - Frontend: `http://localhost:3000`
  - Backend REST API: `http://localhost:8000/api/satellites`
  - RabbitMQ Admin: `http://localhost:15672` (guest/guest)
  - Swagger Specs: `http://localhost:8000/docs`
- **Key Commands**:
  - Start Standalone: `python scripts/run_local.py` (Terminal 1) + `npm run dev` in `frontend` (Terminal 2).
  - Start Docker Compose: `docker compose up --build`.
  - Run Test Suite: `$env:PYTHONPATH="."; python -m pytest tests/`.
  - Verify Docker: `docker compose ps`.
