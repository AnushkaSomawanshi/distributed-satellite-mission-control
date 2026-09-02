# Live Demonstration & Viva Guide for Teachers

A step-by-step presentation script, demonstration checklist, and viva prompt reference for showcasing the **Distributed Satellite Monitoring System** to evaluators and academic panels.

---

## 1. Demonstration Objective

To demonstrate a fully functional, containerized Distributed System with real backend execution across 5 satellite microservices (`SAT-01`..`SAT-05`), featuring multi-protocol communication (gRPC, RabbitMQ, WebSockets, P2P, WebRTC), dynamic service discovery, heartbeat failure detection (10.0s TTL), autonomous recovery, and Ring Leader Election.

---

## 2. Pre-Demo Setup & Environment Clean Launch

Run these exact commands in PowerShell prior to presenting:

```powershell
# 1. Stop previous runs
docker compose down

# 2. Build and launch all 9 services cleanly
docker compose up -d --build

# 3. Verify all 9 containers are active
docker compose ps
```

### Expected `docker compose ps` Output:
```
NAME                       SERVICE           STATUS                    PORTS
mission-control-backend    mission-control   Up (healthy)              0.0.0.0:8000->8000/tcp
mission-control-frontend   frontend          Up                        0.0.0.0:3000->3000/tcp
satellite-01               satellite-01      Up                        0.0.0.0:5001->5001/tcp, 0.0.0.0:6001->6001/tcp
satellite-02               satellite-02      Up                        0.0.0.0:5002->5002/tcp, 0.0.0.0:6002->6002/tcp
satellite-03               satellite-03      Up                        0.0.0.0:5003->5003/tcp, 0.0.0.0:6003->6003/tcp
satellite-04               satellite-04      Up                        0.0.0.0:5004->5004/tcp, 0.0.0.0:6004->6004/tcp
satellite-05               satellite-05      Up                        0.0.0.0:5005->5005/tcp, 0.0.0.0:6005->6005/tcp
satellite-postgres         postgres          Up (healthy)              0.0.0.0:5432->5432/tcp
satellite-rabbitmq         rabbitmq          Up (healthy)              0.0.0.0:5672->5672/tcp, 0.0.0.0:15672->15672/tcp
```

---

## 3. Step-by-Step Demonstration Script

### STEP 1: Main Mission Overview (`http://localhost:3000/`)
- **What to Show**: The main constellation status banner and **Discovered Constellation Nodes** table.
- **What to Point Out**:
  1. All 5 satellites (`SAT-01` through `SAT-05`) are listed with real metric readings from the FastAPI backend.
  2. Metric cards: `Healthy Satellites: 5 / 5`, `WebSocket Stream: CONNECTED`, `Middleware Broker: RabbitMQ (5672)`.
  3. Last Heartbeat column updating live every 2 seconds (`0.4s ago`).
- **What to Say**:
  > *"Here we see Mission Control discovering all 5 satellite nodes operating in separate Docker containers. The metrics displayed—battery, core temperature, CPU utilization, and health scores—are generated dynamically by satellite microservice processes and streamed to this UI."*

---

### STEP 2: Satellite Service Registry (`http://localhost:3000/registry`)
- **What to Show**: The **Satellite Service Registry & Discovery** lookup table.
- **What to Point Out**:
  1. Detailed lookup columns: `Satellite ID`, `Internal Node ID`, `Hostname`, `Address`, `gRPC Endpoint` (`:5001-5005`), `P2P Endpoint` (`:6001-6005`), `Status`, `Last Heartbeat`, and `Capabilities`.
  2. Click **[ REFRESH REGISTRY ]** button to observe live REST API query execution to `GET /api/satellites`.
- **What to Say**:
  > *"This table demonstrates Dynamic Naming and Endpoint Discovery. Satellites do not have hardcoded IP addresses; upon booting, each satellite container registers its hostname, gRPC port, and P2P port with Mission Control's in-memory Service Registry."*

---

### STEP 3: Live Telemetry Line Charts (`http://localhost:3000/telemetry`)
- **What to Show**: 4 continuous stream-oriented Recharts line graphs.
- **What to Point Out**:
  1. **4 Time-Series Charts**: Battery Charge Level (%), Core Temperature (°C), CPU Utilization (%), and Health Score (%).
  2. Lines render continuously without gaps across rolling time steps via WebSocket stream push (`/ws`).
  3. Filter dropdown: Switch between `ALL Satellites` and single node (`SAT-03`).
- **What to Say**:
  > *"These charts demonstrate Stream-Oriented Real-Time Push. Mission Control broadcasts incoming satellite heartbeats over a WebSocket stream. React accumulates rolling samples and renders continuous time-series line graphs using Recharts with `connectNulls={true}`."*

---

### STEP 4: Communication Observatory (`http://localhost:3000/observatory`)

#### Feature A: gRPC Remote Procedure Call
- **What to Click**: Click **[ EXECUTE gRPC GetHealth() ]** for `SAT-01`.
- **What Happens**: FastAPI issues unary gRPC request to `satellite-01:5001`.
- **Evidence**: UI displays `Protocol: gRPC`, `Latency: ~3.4ms`, status `SUCCESS`, and protobuf payload object.

#### Feature B: Direct P2P Inter-Satellite Cross-Link
- **What to Click**: Select Source `SAT-01`, Target `SAT-04`, and click **[ EXECUTE DIRECT P2P LINK ]**.
- **What Happens**: Mission Control instructs `SAT-01` to open a direct TCP socket to `SAT-04:6004` bypassing Mission Control relay.
- **Evidence**: UI displays `Direct Link: satellite-01:6001 -> satellite-04:6004`, `Relay: DIRECT_SATELLITE_TO_SATELLITE`.

#### Feature C: Ring Leader Election
- **What to Click**: Click **[ TRIGGER RING ELECTION ]**.
- **What Happens**: Algorithm circulates logical ring `SAT-01 ➔ SAT-02 ➔ SAT-03 ➔ SAT-04 ➔ SAT-05 ➔ SAT-01`.
- **Evidence**: UI renders step-by-step ring execution trace diagram and elects `SAT-05` as leader (`current_leader: SAT-05`).

---

### STEP 5: Real Container Failure & Autonomous Recovery Demo

#### 1. Node Failure Execution:
Run in PowerShell:
```powershell
docker compose stop satellite-02
```

- **Wait 10 Seconds**: Watch the 10.0s TTL sweeper detect missing heartbeats.
- **Observe UI State**:
  - Main Overview updates to `Healthy Satellites: 4 / 5`, `System Health: DEGRADED`.
  - `SAT-02` row displays red `OFFLINE` badge across Overview, Registry, and Topology.
  - Telemetry page shows stream halt warning alert.

#### 2. Node Recovery Execution:
Run in PowerShell:
```powershell
docker compose start satellite-02
```

- **Observe UI Recovery**: `SAT-02` re-registers, heartbeats resume, and state automatically recovers to `Healthy Satellites: 5 / 5` and `System: HEALTHY`.

---

## 4. Viva Presentation Guide & Sample Questions

### Q1: How does Mission Control differentiate between network latency and a node crash?
> **Answer**: *"A node latency fault introduces delayed heartbeats, but heartbeats still arrive within the 10.0s TTL window (updating node status to `WARNING` or `CRITICAL`). A node crash halts heartbeats entirely. When `current_time - last_heartbeat > 10.0s`, the heartbeat sweeper explicitly transitions the node to `OFFLINE`."*

### Q2: What ensures that satellite P2P communications do not rely on Mission Control as a relay?
> **Answer**: *"Mission Control acts strictly as a naming directory. During P2P execution, Mission Control returns `SAT-04`'s container hostname and port (`satellite-04:6004`) to `SAT-01`. `SAT-01` then opens a direct HTTP/TCP client socket to `SAT-04`, transmitting data directly across the Docker bridge network."*

### Q3: How is state synchronized across the React UI components?
> **Answer**: *"The React root (`App.jsx`) maintains a single source of truth for satellite states fed by WebSockets. Any backend event (`NODE_DISCONNECTED`, `TELEMETRY_UPDATED`, `LEADER_ELECTION_COMPLETED`) immediately updates this centralized state, causing all child pages (Overview, Registry, Topology, Telemetry) to re-render consistently."*
