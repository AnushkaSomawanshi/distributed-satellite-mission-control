# FA-1 DISTRIBUTED SYSTEMS — COMPLETE TEACHER DEMONSTRATION GUIDE

**Project Title**: Distributed Satellite Constellation Health Monitoring & Autonomous Fault Recovery System  
**Target Syllabus**: Distributed Systems FA-1 (Unit 1: Introduction to Distributed Systems & Unit 2: Communication)  
**Format**: Step-by-Step Viva Execution Manual & Demonstration Script

---

# PART 1 — COMPLETE SYSTEM STATUS & AUDIT RESULT

| Component | Audit Result | Status | Operational Proof |
| :--- | :--- | :---: | :--- |
| **Frontend** | React 18, Vite, Tailwind UI Dashboard | **PASS** | Running at `http://localhost:3000` |
| **Mission Control Backend** | FastAPI, uvicorn, Python 3.11 | **PASS** | Running at `http://localhost:8000` |
| **Satellite Microservices** | 5 independent Python processes (`SAT-01` .. `SAT-05`) | **PASS** | Ports `5001-5005` (gRPC) & `6001-6005` (P2P) |
| **Message Broker** | RabbitMQ Alpine (AMQP 0-9-1) | **PASS** | `5672` (AMQP) & `15672` (Mgmt UI) |
| **Database** | PostgreSQL 15 / Async SQLite | **PASS** | `5432` / `satellite_system.db` |
| **Virtualization** | Docker Compose (9 containers) | **PASS** | `docker compose ps` healthy |
| **Classroom Demo Center** | Fixed & fully interactive UI | **PASS** | `http://localhost:3000/demo-center` |
| **Teacher Questions Guide** | Dedicated Viva Defense UI | **PASS** | `http://localhost:3000/teacher-questions` |
| **gRPC Remote Procedure Call** | Native `grpc.aio` & Compiled Protobuf | **PASS** | `GetHealth()` returning in ~14ms |
| **Direct P2P Cross-link** | SAT-01 -> SAT-04 direct network connection | **PASS** | Bypasses Mission Control relay |
| **WebSockets Streaming** | Full-duplex JSON broadcast | **PASS** | Recharts line graphs stream at ~10 msg/s |
| **WebRTC Multimedia** | SDP Offer/Answer signaling | **PASS** | Animated 1080p camera feed rendered |
| **Failure Detection & Recovery** | 10s Heartbeat Timeout Sweeper | **PASS** | Node transitions `HEALTHY` -> `OFFLINE` -> `HEALTHY` |

---

# PART 2 — SYSTEM ARCHITECTURE DIAGRAM

```text
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

# PART 3 — STEP-BY-STEP TEACHER DEMONSTRATION SCRIPT

---

## DEMO 1 — DISTRIBUTED NODES & VIRTUALIZATION

### Distributed Systems Concept
A distributed system consists of multiple autonomous computing entities (nodes) that communicate over a network to coordinate actions and share resources without relying on a shared physical memory space.

### What Is Implemented in Our Project?
Our system deploys 5 independent satellite microservice processes (`SAT-01` to `SAT-05`). Each satellite calculates its telemetry independently and communicates over separate network ports.

### Backend Implementation
- **FILE**: `satellites/satellite_node.py`
- **CLASS/FUNCTION**: `SatelliteNode` / `start_autonomous_loop()`
- **PORTS**: `5001-5005` (gRPC), `6001-6005` (P2P)
- **PROTOCOL**: HTTP / gRPC / Socket

### Frontend Location
- **PAGE**: `Constellation Topology` (`http://localhost:3000/topology`)
- **BUTTON**: View SVG Node Graph

### Terminal Command (PowerShell)
```powershell
docker compose ps
```

### What I Should See
```text
NAME                        STATUS              PORTS
mission-control-backend     running (healthy)   0.0.0.0:8000->8000/tcp
mission-control-frontend    running             0.0.0.0:3000->3000/tcp
satellite-01                running             0.0.0.0:5001->5001/tcp, 0.0.0.0:6001->6001/tcp
satellite-02                running             0.0.0.0:5002->5002/tcp, 0.0.0.0:6002->6002/tcp
satellite-03                running             0.0.0.0:5003->5003/tcp, 0.0.0.0:6003->6003/tcp
satellite-04                running             0.0.0.0:5004->5004/tcp, 0.0.0.0:6004->6004/tcp
satellite-05                running             0.0.0.0:5005->5005/tcp, 0.0.0.0:6005->6005/tcp
satellite-postgres          running (healthy)   0.0.0.0:5432->5432/tcp
satellite-rabbitmq          running (healthy)   0.0.0.0:5672->5672/tcp, 0.0.0.0:15672->15672/tcp
```

### What I Should Say
> *"Professor, this command proves our system is not a single server. We have 9 independent containerized services: Mission Control, RabbitMQ, Postgres, React Frontend, and 5 distinct satellite nodes running on separate ports."*

---

## DEMO 2 — SERVICE DISCOVERY & NAMING

### Distributed Systems Concept
Service discovery enables distributed components to dynamically locate peer network addresses (IP/port) at runtime without hardcoding fixed socket parameters in source code.

### What Is Implemented in Our Project?
Satellites register dynamically with `SatelliteRegistry` on startup. Mission Control looks up hostnames and ports dynamically when initiating gRPC or P2P requests.

### Backend Implementation
- **FILE**: `backend/registry/service_registry.py`
- **CLASS/FUNCTION**: `SatelliteRegistry` / `register()` & `lookup()`
- **PORT**: `8000`
- **PROTOCOL**: HTTP REST

### Frontend Location
- **PAGE**: `Satellite Registry` (`http://localhost:3000/registry`)
- **BUTTON**: View Registry Table

### Terminal Command (PowerShell)
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/satellites" | ConvertTo-Json -Depth 5
```

### What I Should See
```json
{
  "satellites": [
    {
      "satellite_id": "SAT-01",
      "hostname": "sat-01.orbital.local",
      "address": "satellite-01",
      "grpc_port": 5001,
      "p2p_port": 6001,
      "status": "HEALTHY",
      "health_score": 100.0
    }
  ],
  "count": 5
}
```

### What I Should Say
> *"Professor, here is our dynamic Service Registry. When `SAT-01` boots up, it registers its gRPC port 5001 and P2P port 6001. Mission Control resolves symbolic names like `SAT-01` to actual network endpoints dynamically."*

---

## DEMO 3 — REMOTE PROCEDURE CALL (gRPC & PROTOBUF)

### Distributed Systems Concept
Remote Procedure Call (RPC) allows a process to invoke a subroutine on another machine over a network as if it were a local function call. Protocol Buffers provide strong, typed binary serialization.

### What Is Implemented in Our Project?
Mission Control executes `GetHealth()`, `Ping()`, or `GetSatelliteInfo()` calls directly against satellite gRPC servers listening on ports 5001-5005 using compiled `satellite.proto` contracts.

### Backend Implementation
- **FILE**: `proto/satellite.proto` & `backend/communication/grpc_client.py`
- **CLASS/FUNCTION**: `GRPCClientManager.invoke_rpc()`
- **PORTS**: `5001-5005`
- **PROTOCOL**: gRPC / Protocol Buffers (HTTP/2)

### Frontend Location
- **PAGE**: `Communication Observatory` (`http://localhost:3000/observatory`)
- **BUTTON**: Select `SAT-03`, Method `GetHealth` -> Click **EXECUTE gRPC REQUEST**

### Terminal Command (PowerShell)
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/rpc/invoke" -Method Post -ContentType "application/json" -Body '{"target_satellite_id":"SAT-03","method":"GetHealth"}' | ConvertTo-Json -Depth 5
```

### What I Should See
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
    "battery_level": 98.5
  }
}
```

### What I Should Say
> *"Professor, this demonstrates synchronous gRPC RPC. Mission Control sent a binary Protocol Buffer `GetHealth` request over gRPC to SAT-03 on port 5003, returning a structured response with a measured latency of 14ms."*

---

## DEMO 4 — MESSAGE-ORIENTED MIDDLEWARE (RABBITMQ)

### Distributed Systems Concept
Message-Oriented Middleware (MOM) provides asynchronous, decoupled communication using message queues, guaranteeing message persistence and buffering telemetry spikes.

### What Is Implemented in Our Project?
Satellites publish telemetry to RabbitMQ `telemetry.exchange` (fanout type). Mission Control's background consumer processes the queue (`telemetry.queue`) asynchronously.

### Backend Implementation
- **FILE**: `backend/communication/rabbitmq_manager.py`
- **CLASS/FUNCTION**: `RabbitMQManager` / `publish_telemetry()` & `_start_consumer()`
- **PORTS**: `5672` (AMQP), `15672` (Management UI)
- **PROTOCOL**: AMQP 0-9-1

### Frontend Location
- **PAGE**: `Communication Observatory` -> `RabbitMQ` Tab
- **BROWSER URL**: `http://localhost:15672` (guest / guest)

### Terminal Command (PowerShell)
```powershell
docker compose exec rabbitmq rabbitmqctl list_queues name messages consumers
```

### What I Should See
```text
Listing queues for vhost / ...
name            messages        consumers
telemetry.queue 0               1
```

### What I Should Say
> *"Professor, this demonstrates asynchronous message-oriented middleware. Satellites publish telemetry frames into RabbitMQ `telemetry.queue`. The active consumer count of 1 proves Mission Control is asynchronously processing the queue."*

---

## DEMO 5 — DIRECT PEER-TO-PEER (P2P) SATELLITE LINK

### Distributed Systems Concept
Peer-to-Peer (P2P) architecture enables direct communication between equivalent network nodes without routing data through a central server or backend relay.

### What Is Implemented in Our Project?
`SAT-01` opens a direct HTTP/socket connection across the network directly to `SAT-04` at `http://satellite-04:6004/p2p/receive`. Mission Control triggers the request but does **NOT** relay the message payload.

### Backend Implementation
- **FILE**: `satellites/satellite_node.py`
- **CLASS/FUNCTION**: `send_to_peer()` / `/p2p/receive`
- **PORTS**: `6001` -> `6004`
- **PROTOCOL**: Direct HTTP/Socket Network Link

### Frontend Location
- **PAGE**: `Communication Observatory` -> `P2P Messaging` Tab
- **BUTTON**: Select Source `SAT-01`, Destination `SAT-04` -> Click **SEND DIRECT P2P MESSAGE**

### Terminal Command (PowerShell)
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/p2p/send" -Method Post -ContentType "application/json" -Body '{"source_satellite_id":"SAT-01","destination_satellite_id":"SAT-04","payload":"P2P_DIRECT_HANDSHAKE"}' | ConvertTo-Json -Depth 5
```

### What I Should See
```json
{
  "success": true,
  "source": "SAT-01",
  "destination": "SAT-04",
  "direct_link": "SAT-01 (satellite-01:6001) -> SAT-04 (satellite-04:6004)",
  "relay_status": "DIRECT_SATELLITE_TO_SATELLITE (No Mission Control Relay)",
  "latency_ms": 11.8
}
```

### What I Should Say
> *"Professor, this is actual direct P2P communication. Notice the `relay_status` confirms Mission Control did NOT relay the message. SAT-01 opened a direct network link on port 6001 straight to SAT-04 on port 6004."*

---

## DEMO 6 — FAILURE DETECTION & AUTONOMOUS RECOVERY

### Distributed Systems Concept
Failure detection mechanisms monitor node liveness using periodic heartbeats. When a node stops sending heartbeats past a configured threshold (TTL), the system marks it failed and continues operating (Fault Tolerance). When it restarts, it dynamically recovers (Recovery).

### What Is Implemented in Our Project?
Satellites send heartbeats every 2s. Mission Control's background sweeper (`heartbeat_sweeper_task()`) checks node timestamps every 3s. If a heartbeat is missing for >10s, status transitions `HEALTHY` -> `OFFLINE`. Upon restart, the satellite re-registers and recovers to `HEALTHY`.

### Backend Implementation
- **FILE**: `backend/registry/service_registry.py` & `backend/main.py`
- **CLASS/FUNCTION**: `sweep_failures()` / `heartbeat_sweeper_task()`
- **TIMEOUT**: `10.0` Seconds TTL

### Frontend Location
- **PAGE**: `Fault Simulator` (`http://localhost:3000/faults`)
- **BUTTON**: Select `SAT-03` -> Click **INJECT NODE STOP**

### Terminal Command Sequence (PowerShell)

```powershell
# 1. Verify all 5 healthy
Invoke-RestMethod -Uri "http://localhost:8000/api/health" | ConvertTo-Json -Depth 3

# 2. Stop Satellite 03 container
docker compose stop satellite-03

# 3. Wait 12 seconds and check health again
Start-Sleep -Seconds 12
Invoke-RestMethod -Uri "http://localhost:8000/api/health" | ConvertTo-Json -Depth 3

# 4. Restart Satellite 03 container (Recovery)
docker compose start satellite-03
Start-Sleep -Seconds 4
Invoke-RestMethod -Uri "http://localhost:8000/api/health" | ConvertTo-Json -Depth 3
```

### What I Should See
1. Before stop: `healthy: 5`, `offline: 0`.
2. After 12s stop: `healthy: 4`, `offline: 1` (`SAT-03` OFFLINE). Satellites 01, 02, 04, 05 continue running!
3. After restart: `healthy: 5`, `offline: 0` (`SAT-03` HEALTHY).

### What I Should Say
> *"Professor, this proves fault tolerance and recovery. When SAT-03 stopped, the 10-second heartbeat sweeper detected the outage and marked SAT-03 OFFLINE while the remaining 4 nodes kept operating normally. When we restarted SAT-03, it re-registered dynamically and recovered to HEALTHY state."*

---

# PART 4 — VIVA CODE LOOKUP TABLE

| If Professor Asks | Open File | Class / Function | What to Explain |
| :--- | :--- | :--- | :--- |
| **"Where is the satellite process?"** | [`satellites/satellite_node.py`](file:///c:/Users/Anushka/Downloads/DS-Project/satellites/satellite_node.py#L30-L150) | `SatelliteNode` | Autonomous orbit calculation loop & heartbeat thread |
| **"Where is gRPC implemented?"** | [`proto/satellite.proto`](file:///c:/Users/Anushka/Downloads/DS-Project/proto/satellite.proto#L60-L75) & [`backend/communication/grpc_client.py`](file:///c:/Users/Anushka/Downloads/DS-Project/backend/communication/grpc_client.py#L20-L70) | `GRPCClientManager` | Proto binary service contract & async gRPC stub invocation |
| **"Where is RabbitMQ integration?"** | [`backend/communication/rabbitmq_manager.py`](file:///c:/Users/Anushka/Downloads/DS-Project/backend/communication/rabbitmq_manager.py#L15-L80) | `RabbitMQManager` | AMQP connection, `telemetry.exchange` fanout, & consumer loop |
| **"Where is P2P direct transmission?"** | [`satellites/satellite_node.py`](file:///c:/Users/Anushka/Downloads/DS-Project/satellites/satellite_node.py#L220-L260) | `send_to_peer()` | Direct HTTP/socket post from source satellite to peer port |
| **"Where is failure detection?"** | [`backend/main.py`](file:///c:/Users/Anushka/Downloads/DS-Project/backend/main.py#L40-L60) & [`backend/registry/service_registry.py`](file:///c:/Users/Anushka/Downloads/DS-Project/backend/registry/service_registry.py#L85-L105) | `sweep_failures()` | Sweeper task checking `last_heartbeat` delta against 10s TTL |
| **"Where is Health Engine formula?"** | [`backend/services/health_engine.py`](file:///c:/Users/Anushka/Downloads/DS-Project/backend/services/health_engine.py#L15-L80) | `HealthEngine.calculate_health()` | Weighted formula combining battery, temp, CPU, memory, & signal |
| **"Where is WebSockets streaming?"** | [`backend/communication/websocket_manager.py`](file:///c:/Users/Anushka/Downloads/DS-Project/backend/communication/websocket_manager.py#L10-L45) | `ConnectionManager` | WebSocket connection pool & real-time telemetry frame broadcasting |
| **"Where is WebRTC signaling?"** | [`backend/communication/webrtc_signaling.py`](file:///c:/Users/Anushka/Downloads/DS-Project/backend/communication/webrtc_signaling.py#L10-L60) | `WebRTCSignalingManager` | SDP Offer/Answer negotiation for simulated orbital camera feed |
| **"Where is Database ORM?"** | [`backend/database/models.py`](file:///c:/Users/Anushka/Downloads/DS-Project/backend/database/models.py#L10-L60) | `CommunicationEvent` | SQLAlchemy async model definitions for persistent event logging |
| **"Where is Docker configuration?"** | [`docker-compose.yml`](file:///c:/Users/Anushka/Downloads/DS-Project/docker-compose.yml#L1-L136) | `services:` | Declarations for 5 satellites, backend, frontend, RabbitMQ, Postgres |
| **"Where is Classroom Demo Center UI?"** | [`frontend/src/pages/SystemHealthDemo.jsx`](file:///c:/Users/Anushka/Downloads/DS-Project/frontend/src/pages/SystemHealthDemo.jsx#L10-L100) | `SystemHealthDemo` | 14 single-click execution scripts for live evaluation |
| **"Where is Teacher Questions UI?"** | [`frontend/src/pages/TeacherQuestionsPage.jsx`](file:///c:/Users/Anushka/Downloads/DS-Project/frontend/src/pages/TeacherQuestionsPage.jsx#L5-L100) | `TeacherQuestionsPage` | Comprehensive viva question and evidence pointer guide |
