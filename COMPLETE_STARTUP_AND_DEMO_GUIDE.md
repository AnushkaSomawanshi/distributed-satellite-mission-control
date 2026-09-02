# COMPLETE STARTUP & DEMONSTRATION GUIDE
## Distributed Satellite Constellation Health Engine

**Status**: ✅ **FULLY OPERATIONAL & TESTED**

All systems verified, failure detection tested, recovery confirmed. Ready for viva.

---

## PART 1: STARTUP INSTRUCTIONS

### Quick Start (One Command)

From project root directory (`C:\Users\Anushka\Downloads\DS-Project`):

```bash
docker compose up -d
```

**Wait 15-20 seconds for all services to start.**

Verify all containers are running:
```bash
docker compose ps -a
```

Expected output: 9 containers all showing "Up" status:
- postgres (healthy)
- rabbitmq (healthy)
- mission-control-backend
- mission-control-frontend
- satellite-01 through satellite-05

### Port Reference

| Service | Port | Purpose |
|---------|------|---------|
| Frontend (React) | 3000 | Web UI |
| Backend (FastAPI) | 8000 | REST/WebSocket API |
| PostgreSQL | 5432 | Database |
| RabbitMQ AMQP | 5672 | Message broker |
| RabbitMQ UI | 15672 | Management console |
| SAT-01 gRPC | 5001 | Satellite 1 RPC |
| SAT-01 P2P | 6001 | Satellite 1 Direct Link |
| SAT-02 gRPC | 5002 | Satellite 2 RPC |
| SAT-02 P2P | 6002 | Satellite 2 Direct Link |
| (etc for SAT-03, SAT-04, SAT-05) | | |

---

## PART 2: FRONTEND DEMONSTRATION

### Access the Application

**Open in browser:**
```
http://localhost:3000
```

You will see:
- Dark space-themed UI with orbital aesthetic
- Navigation sidebar on the left
- Main content area showing "Mission Overview"
- Real-time WebSocket connection status indicator

### DEMO 1: Mission Overview (Main Dashboard)

**Path:** Home page (default)

**What You'll See:**
- System health status card (should show HEALTHY)
- Satellite constellation overview (5 satellites listed)
- Real-time telemetry metrics
- WebSocket connection status

**What It Proves:**
- System architecture is operational
- Multiple independent nodes exist
- Real-time communication established

---

## PART 3: CORE FUNCTIONALITY DEMONSTRATIONS

### DEMO 2: Service Discovery & Dynamic Registry

**Frontend Path:** `http://localhost:3000/registry`

Click: **"Satellite Registry"** in the sidebar

**What You'll See:**
A table displaying all 5 satellites with:
- **satellite_id**: SAT-01, SAT-02, etc.
- **node_id**: NODE-SAT-01-xxxx (unique identifier)
- **hostname**: sat-01.orbital.local (DNS name)
- **address**: satellite-01 (Docker network address)
- **grpc_port**: 5001, 5002, etc. (RPC port)
- **p2p_port**: 6001, 6002, etc. (direct link port)
- **status**: HEALTHY
- **health_score**: 90-100
- **battery, temperature, cpu_usage, memory_usage, signal_strength**

**What It Proves:**
- Service Discovery: Names map to addresses
- Dynamic Registry: All satellites registered with Mission Control
- Distributed Naming: Each node has unique internal ID (NODE-xxxx-xxxx)

**Code Location:**
- Frontend: `frontend/src/pages/SatelliteRegistryPage.jsx`
- Backend: `backend/registry/service_registry.py`

---

### DEMO 3: Satellite Topology & Independent Nodes

**Frontend Path:** `http://localhost:3000/topology`

Click: **"Constellation Topology"** in sidebar

**What You'll See:**
- Visual diagram showing 5 satellite nodes
- Each node independent with separate processes
- Orbital positions changing in real-time
- Network connections visualized

**What It Proves:**
- 5 independent microservices (separate processes/containers)
- Each has own isolated state
- Autonomous operation without central control
- Constellation formation

**Code Location:**
- `frontend/src/pages/ConstellationMap.jsx`
- `satellites/satellite_node.py` (each runs independently)

---

### DEMO 4: Autonomous Telemetry Generation

**Frontend Path:** `http://localhost:3000/telemetry`

Click: **"Live Telemetry Charts"** in sidebar

**What You'll See:**
- Real-time line charts updating every few seconds
- Battery levels changing (charging in sunlight, draining in eclipse)
- Temperature fluctuating
- CPU/Memory usage varying
- Signal strength oscillating
- Satellite orbit positions changing

**What It Proves:**
- Each satellite generates autonomous local state
- Not dummy data - calculated based on orbital mechanics
- Real-time streaming to frontend
- WebSocket working for continuous updates

**Code Location:**
- Backend: `satellites/satellite_node.py` → `step_telemetry()`
- Method calculates latitude, longitude, battery, temperature based on orbit angle

**Backend API Test:**
```bash
curl http://localhost:8000/api/observatory/stats
```

---

### DEMO 5: Remote Procedure Call (gRPC)

**Frontend Path:** `http://localhost:3000/observatory`

Click: **"Communication Observatory"** → **"gRPC Tab"**

**What You'll See:**
A button labeled **"EXECUTE gRPC REQUEST"**

Click it to invoke `GetHealth()` on a satellite

**Expected Response:**
```json
{
  "success": true,
  "method": "GetHealth",
  "target": "SAT-03",
  "latency_ms": 250.45,
  "data": {
    "satellite_id": "SAT-03",
    "status": "HEALTHY",
    "health_score": 95.5,
    "battery_level": 88.2,
    "temperature": 24.5,
    "cpu_usage": 18.3,
    "memory_usage": 32.1,
    "signal_strength": 94.8,
    "uptime_seconds": 124
  }
}
```

**What It Proves:**
- Synchronous RPC over gRPC
- Protocol Buffers serialization
- Remote method invocation to satellite
- Network latency measured

**Code Location:**
- Protocol definition: `proto/satellite.proto`
- Backend client: `backend/communication/grpc_client.py` → `invoke_rpc()`
- Satellite server: `satellites/satellite_node.py` → gRPC service handler

**Terminal Test:**
```bash
curl -X POST http://localhost:8000/api/rpc/invoke \
  -H "Content-Type: application/json" \
  -d '{"target_satellite_id":"SAT-01","method":"GetHealth"}'
```

**Expected latency:** 100-400ms depending on system load

---

### DEMO 6: Message-Oriented Middleware (RabbitMQ)

**Frontend Path:** `http://localhost:3000/observatory`

**What You'll See:**
- RabbitMQ connection status
- Message queue statistics
- Published/consumed message counts

**What It Proves:**
- Asynchronous message-oriented communication
- Pub/Sub pattern via exchange/queue
- Telemetry messages flowing through broker

**Backend API Test:**
```bash
curl http://localhost:8000/api/health
```

Response shows:
```json
{
  "rabbitmq": "HEALTHY" or "IN_MEMORY_FALLBACK"
}
```

**Code Location:**
- Implementation: `backend/communication/rabbitmq_manager.py`
- Uses: `aio_pika` for async AMQP
- Exchange: `telemetry.exchange` (fanout)
- Queue: `telemetry.queue`

**Note:** System has built-in fallback to in-memory event bus if RabbitMQ is unavailable, ensuring 100% uptime.

---

### DEMO 7: Stream-Oriented Communication (WebSockets)

**Frontend Path:** Any page (background connection)

**What You'll See:**
- Real-time data updates without page refresh
- Telemetry charts continuously updating
- Status changes appearing immediately
- Live metrics flowing

**What It Proves:**
- Low-latency bidirectional communication
- Real-time streaming from backend to frontend
- WebSocket connection active in browser

**Browser Developer Tools:**
- Open DevTools (F12)
- Go to Network tab
- Filter for "WS" (WebSocket)
- You'll see connection to `/ws` endpoint

**Backend Code:**
- Implementation: `backend/communication/websocket_manager.py`
- Endpoint: `@app.websocket("/ws")`
- Broadcasts events to all connected clients

**Terminal Test:**
```bash
curl http://localhost:8000/api/observatory/stats
```

Shows `"active_clients": N` (number of connected browsers)

---

### DEMO 8: Peer-to-Peer Direct Linking

**Frontend Path:** `http://localhost:3000/observatory`

Click: **"Communication Observatory"** → **"P2P Section"**

**What You'll See:**
A button labeled **"SEND DIRECT P2P MESSAGE"**

Click it to send a message from SAT-01 → SAT-04 **without Mission Control relay**

**Expected Response:**
```json
{
  "success": true,
  "message_id": "p2p-1788312023204",
  "source": "SAT-01",
  "destination": "SAT-04",
  "direct_link": "SAT-01 (satellite-01:6001) -> SAT-04 (satellite-04:6004)",
  "latency_ms": 57.73,
  "relay_status": "DIRECT_SATELLITE_TO_SATELLITE (No Mission Control Relay)",
  "response": {
    "receiver_satellite_id": "SAT-04",
    "acknowledged": true,
    "status_message": "Direct P2P message received by SAT-04"
  }
}
```

**What It Proves:**
- Direct network link between satellites
- Mission Control only **triggers** source, doesn't relay
- No central message bottleneck
- P2P architecture element

**Code Location:**
- Backend trigger: `backend/main.py` → `/api/p2p/send`
- Satellite receiver: `satellites/satellite_node.py` → `/p2p/send_to_peer`
- Process: Mission Control calls SAT-01's P2P endpoint → SAT-01 connects directly to SAT-04

**Terminal Test:**
```bash
curl -X POST http://localhost:8000/api/p2p/send \
  -H "Content-Type: application/json" \
  -d '{
    "source_satellite_id": "SAT-01",
    "destination_satellite_id": "SAT-04",
    "message_type": "DIRECT_LINK_TEST",
    "payload": "Test message"
  }'
```

**Important:** The message doesn't flow back through Mission Control - SAT-01 and SAT-04 have direct socket connection.

---

### DEMO 9: WebRTC Distributed Multimedia

**Frontend Path:** `http://localhost:3000/multimedia`

Click: **"Satellite WebRTC Feed"** in sidebar

**What You'll See:**
A canvas showing simulated orbital camera feed (animated 1080p video stream)

Click: **"ESTABLISH WEBRTC CONNECTION"** button

**What It Proves:**
- WebRTC peer connection setup
- SDP Offer/Answer signaling
- Distributed multimedia capability
- Real-time video stream

**Code Location:**
- Backend signaling: `backend/communication/webrtc_signaling.py`
- Frontend consumer: Handles SDP, ICE candidates, video playback

---

### DEMO 10: Heartbeat Monitoring & Failure Detection

**Frontend Path:** `http://localhost:3000/faults`

Click: **"Fault Simulator"** in sidebar

**Step 1: Initial State**
You'll see all 5 satellites listed as HEALTHY

**Step 2: Inject Failure**
- Find the dropdown/selector for satellites
- Select "SAT-03"
- Click dropdown for fault type
- Select "STOP_NODE"
- Click "INJECT FAULT"

**Step 3: Immediate Effect**
- SAT-03 status changes to **OFFLINE** (visual indication in red)
- Health score drops to 0.0
- Status message shows node unreachable

**What Happened (Backend):**
1. Mission Control stopped accepting heartbeats from SAT-03
2. Failure sweeper runs every 3 seconds
3. After 10 seconds of no heartbeat, SAT-03 marked OFFLINE
4. WebSocket broadcast sent to all clients
5. Frontend receives and updates UI

**Code Location:**
- Backend failure detector: `backend/main.py` → `heartbeat_sweeper_task()`
- Registry check: `backend/registry/service_registry.py` → `sweep_failures()`
- Config: `backend/config.py` → `HEARTBEAT_TIMEOUT_SECONDS = 10.0`

**Terminal Observation:**
```bash
# Watch backend logs
docker compose logs -f mission-control | grep "FAILURE DETECTOR"
```

You'll see:
```
[FAILURE DETECTOR] Satellite SAT-03 heartbeat timed out! Status marked OFFLINE.
```

**Important Observation:**
- SAT-01, SAT-02, SAT-04, SAT-05 continue operating normally
- Failure is isolated to one node
- System remains partially operational

---

### DEMO 11: Failure Recovery & Auto-Restart

**Frontend Path:** Still on Fault Simulator page

**Step 1: Clear Fault / Restart**
- Click dropdown for SAT-03
- Select fault type "RESTART_NODE"
- Click "INJECT FAULT"

**Or via terminal:**
```bash
docker compose start satellite-03
```

**Step 2: Recovery Process**
- SAT-03 container restarts
- Satellite node sends new registration
- Sends heartbeat
- Backend detects and marks HEALTHY

**Timeline:**
- t=0: SAT-03 starts
- t=2s: First heartbeat sent
- t=2.5s: Received by Mission Control
- t=3s: Next sweep cycle runs, sees healthy heartbeat
- Status changes from OFFLINE → HEALTHY

**What It Proves:**
- Autonomous failure recovery
- No manual intervention needed
- System self-heals
- Fault tolerance in action

---

### DEMO 12: Classroom Demo Center & Viva Questions

**Frontend Path:** `http://localhost:3000/demo-center`

Click: **"Classroom Demo Center"** in sidebar

**What You'll See:**
A comprehensive listing of 14 demonstration scenarios with:
- Demo title
- Concept being demonstrated
- Description
- Endpoint involved
- Code location
- Executable action button

**Each Demo Includes:**
- Executable button (runs actual backend operation)
- Result display showing real API responses
- Code references
- Distributed systems concept explained

**Examples:**
1. "Distributed Nodes & Process Health" → Executes `GET /api/health`
2. "Satellite Microservice Topology" → Lists all 5 satellites
3. "Dynamic Service Discovery" → Shows registry mappings
4. "Autonomous Telemetry Generation" → Current telemetry snapshot
5. "Remote Procedure Call (gRPC)" → Executes GetHealth RPC
6. "Message-Oriented Middleware" → Shows RabbitMQ stats
7. "Stream-Oriented Communication" → WebSocket frame count
8. "Direct P2P Satellite Link" → Sends direct message
9. "Distributed Multimedia (WebRTC)" → Establishes connection
10. "Inject Node Failure" → Stops a satellite
11. "Satellite Recovery" → Restarts a satellite
12. "Network Latency Degradation" → Adds latency
13. "Packet Loss Simulation" → Adds packet loss
14. "Communication Replay & Timeline" → Historical events

**Teacher Questions Page:** `http://localhost:3000/teacher-questions`

Click: **"Teacher Questions & Viva"** in sidebar

**What You'll See:**
Pre-compiled answers to 11 common professor questions:
1. "Where is the distributed system?"
2. "Where are the independent nodes?"
3. "Where is RPC (Remote Procedure Call)?"
4. "Where is message-oriented communication?"
5. "Where is stream-oriented communication?"
6. "Where is P2P communication?"
7. "Where is WebRTC / Distributed Multimedia?"
8. "Where are names, identifiers, and addresses?"
9. "Where is fault tolerance and failure detection?"
10. "Where is middleware?"
11. "Where is virtualization?"

Each answer includes:
- **Explanation** of the concept
- **Frontend Location** (where to show)
- **Backend Implementation** (file/function reference)
- **Live Demonstration Procedure** (exact steps)

---

## PART 4: VIVA DEMONSTRATION SCRIPT

### Opening (30 seconds)

"This is a distributed satellite constellation health monitoring system. It demonstrates core distributed systems concepts through a practical space mission scenario. The system consists of 5 independent satellite microservices running on separate containers, communicating via gRPC, message queues, WebSockets, and peer-to-peer links, with centralized Mission Control backend handling service discovery, health monitoring, and failure detection."

### Section 1: System Architecture (2 minutes)

**SHOW:**
1. Open `http://localhost:3000`
2. Click "Constellation Topology" 
3. Show the 5 independent satellite nodes

**SAY:**
"This is the distributed system. We have 5 independent satellite nodes running as separate processes. Each has its own gRPC port (5001-5005), P2P port (6001-6005), and autonomous telemetry generation. They form a constellation in orbit. Unlike a monolithic application where everything runs in one process, here each satellite is completely independent."

**DEMONSTRATE Independently Running Nodes:**
```bash
docker compose ps | grep satellite
```
"Each satellite is a separate Docker container - independent process with its own Python runtime."

---

### Section 2: Service Discovery (1 minute)

**SHOW:**
1. Navigate to "Satellite Registry" page
2. Point at the table

**SAY:**
"This is the Service Registry - the naming service. Each satellite has a human-readable name (SAT-01, SAT-02, etc.) but also a unique internal node ID (NODE-SAT-01-XXXX). The registry maps these names to IP addresses, hostnames, and port numbers. This solves the fundamental distributed systems problem: how do you find services when you don't know their addresses in advance?"

**DEMONSTRATE Dynamic Registry:**
```bash
curl -s http://localhost:8000/api/satellites/SAT-01 | grep -E "satellite_id|node_id|address|grpc_port"
```

---

### Section 3: Heartbeat & Health Monitoring (1.5 minutes)

**SHOW:**
1. Open terminal
2. Run: `docker compose logs -f mission-control | grep heartbeat`
3. Wait a few seconds

**SAY:**
"Each satellite sends a heartbeat message every 2 seconds to Mission Control. This is a critical distributed systems pattern - heartbeat monitoring. The heartbeat contains live telemetry: battery level, temperature, CPU usage, memory usage, signal strength. Mission Control uses this to calculate a health score for each node."

**SHOW Health Engine Logic:**
```bash
curl -s http://localhost:8000/api/satellites/SAT-01 | grep -E "battery|temperature|health_score|status"
```

**SAY:**
"The Health Engine calculates a score from 0-100:
- Battery level (25% weight): optimal 70-100%
- Temperature (25%): optimal 15-45°C  
- CPU usage (20%): optimal <70%
- Memory (15%): optimal <80%
- Signal strength (15%): optimal >60%

If score >= 90 → HEALTHY, 70-89 → WARNING, <70 → CRITICAL. This is how the system monitors distributed node health."

---

### Section 4: Communication Methods (3 minutes)

**A. RPC (Remote Procedure Call) - gRPC**

**SHOW:**
1. Go to "Communication Observatory" → "gRPC Tab"
2. Click "EXECUTE gRPC REQUEST"

**SAY:**
"This is a Remote Procedure Call using gRPC. We're invoking GetHealth() on a satellite 250ms away. The call uses Protocol Buffers for serialization - a compact, efficient binary format defined in satellite.proto. Under the hood, it's using the gRPC protocol built on HTTP/2 multiplexing. This is synchronous communication - Mission Control waits for the satellite to respond."

**Code demonstration:**
```bash
cat proto/satellite.proto | head -30
```

**B. Message-Oriented Middleware - RabbitMQ**

**SHOW:**
```bash
curl -s http://localhost:8000/api/observatory/stats | grep -A3 rabbitmq
```

**SAY:**
"Each satellite publishes telemetry messages to RabbitMQ using a fanout exchange. Multiple consumers can subscribe independently - no waiting. This is asynchronous publish-subscribe communication. Even if Mission Control is temporarily slow, messages queue up in RabbitMQ and are processed eventually. This decouples producers from consumers."

**C. Stream-Oriented Communication - WebSockets**

**SHOW:**
1. Go to "Live Telemetry Charts"
2. Watch charts update in real-time

**SAY:**
"These charts are updating every few seconds via WebSocket - a persistent bidirectional TCP connection. Instead of polling the backend repeatedly with HTTP, WebSocket pushes data to the frontend. This is low-latency, efficient real-time communication. The same connection handles events from all 5 satellites."

**D. Peer-to-Peer Communication**

**SHOW:**
1. Go to "Communication Observatory" → "P2P Section"
2. Click "SEND DIRECT P2P MESSAGE"

**SAY:**
"This is P2P direct satellite-to-satellite communication. Notice the response says 'DIRECT_SATELLITE_TO_SATELLITE (No Mission Control Relay)'. SAT-01 and SAT-04 have a direct network connection on their P2P ports. Mission Control only triggers the source satellite; the actual data transfer is direct. This avoids the central hub bottleneck."

**Highlight in response:** `"relay_status": "DIRECT_SATELLITE_TO_SATELLITE"`

---

### Section 5: Failure Detection (2 minutes)

**SETUP:**
```bash
# Terminal 1: Watch backend logs
docker compose logs -f mission-control | grep -E "FAILURE|OFFLINE"
```

**SHOW & DO:**
1. Open "Fault Simulator" page
2. Select SAT-03 from dropdown
3. Select fault type "STOP_NODE"
4. Click "INJECT FAULT"

**OBSERVE in real-time:**
- Frontend shows SAT-03 status changing to OFFLINE
- Backend log shows: `[FAILURE DETECTOR] Satellite SAT-03 heartbeat timed out! Status marked OFFLINE.`
- Other satellites (SAT-01, SAT-02, SAT-04, SAT-05) continue operating normally

**SAY:**
"SAT-03 has been stopped. Let's watch what happens. The system expects heartbeats every 2 seconds. If no heartbeat arrives for 10 seconds (the TTL), the failure detector marks the satellite OFFLINE. The sweeper runs every 3 seconds checking for timeouts. Notice: only SAT-03 went offline. The other 4 satellites are unaffected - this is resilience. The system degrades gracefully."

**SHOW Backend Decision:**
```bash
# In another terminal during the fault:
watch -n 1 "curl -s http://localhost:8000/api/satellites | grep -E 'SAT-0[1-5].*status' | head -10"
```

---

### Section 6: Failure Recovery (1.5 minutes)

**SHOW & DO:**
1. On Fault Simulator page, select SAT-03 again
2. Select "RESTART_NODE"
3. Click "INJECT FAULT"

**Or via terminal:**
```bash
docker compose start satellite-03
```

**OBSERVE:**
- Status changes back to HEALTHY within seconds
- System auto-detects restart
- No manual intervention needed
- Gets new Node-ID (proving it's a fresh instance)

**SAY:**
"The satellite restarts automatically. Within seconds it sends a new heartbeat. The failure detector recognizes the recovery. Notice it got a new Node-ID - this is a fresh process, not the old one. The system is self-healing. This demonstrates fault tolerance - the system can survive and recover from node failures automatically."

---

### Section 7: Virtualization & Containerization (1 minute)

**SHOW:**
```bash
docker compose ps -a
```

**SAY:**
"All services are containerized - running in Docker. Each satellite is a separate container, completely isolated. The database, message broker, backend, and frontend are all containers. This provides process isolation, resource limits, and easy deployment. Virtualization allows multiple services to run on one physical machine without interfering with each other."

---

### Section 8: Middleware Architecture (1 minute)

**SHOW:**
1. Frontend page "Middleware Architecture"

**SAY:**
"The middleware layer abstracts away low-level network details. Applications use high-level APIs like gRPC, RabbitMQ, WebSockets - they don't deal with raw sockets. The middleware handles encoding, routing, reliability. This separates application logic from network infrastructure."

---

## PART 5: SUMMARY CHECKLIST

✅ **Distributed System**: 5 independent nodes operating simultaneously
✅ **Distributed Nodes**: Each satellite runs separately, autonomous state
✅ **Client-Server**: Mission Control (server) coordinates satellites (clients)
✅ **Service Discovery**: Registry maps names to addresses
✅ **Naming & Addressing**: Satellites have names (SAT-01) and unique IDs
✅ **RPC (gRPC)**: Synchronous method invocation with Protocol Buffers
✅ **Message-Oriented Middleware**: RabbitMQ pub/sub for telemetry
✅ **Asynchronous Communication**: Decoupled producer-consumer
✅ **Stream-Oriented Communication**: WebSocket real-time updates
✅ **P2P Communication**: Direct satellite-to-satellite links
✅ **WebRTC/Multimedia**: Video stream over distributed network
✅ **Heartbeat Monitoring**: Regular health check messages
✅ **Failure Detection**: Automatic timeout-based failure recognition
✅ **Fault Tolerance**: System continues operating when node fails
✅ **Failure Recovery**: Automatic restart and re-registration
✅ **Persistence**: PostgreSQL stores events and telemetry
✅ **Containerization**: Docker isolates services
✅ **Virtualization**: Multiple services on one machine
✅ **Middleware Abstraction**: gRPC, RabbitMQ, WebSockets hide network

---

## PART 6: TERMINAL COMMANDS FOR LIVE DEMONSTRATION

### Backend Health Check
```bash
curl -s http://localhost:8000/api/health | grep -o '"status":"[^"]*"'
```

### List All Satellites
```bash
curl -s http://localhost:8000/api/satellites | grep -o '"satellite_id":"[^"]*"' | sort
```

### Single Satellite Details
```bash
curl -s http://localhost:8000/api/satellites/SAT-01 | grep -E '"status"|"health_score"|"battery"|"temperature"'
```

### Invoke gRPC GetHealth
```bash
curl -X POST http://localhost:8000/api/rpc/invoke \
  -H "Content-Type: application/json" \
  -d '{"target_satellite_id":"SAT-01","method":"GetHealth"}' 2>&1 | grep -E '"success"|"latency_ms"|"health_score"'
```

### Send P2P Message
```bash
curl -X POST http://localhost:8000/api/p2p/send \
  -H "Content-Type: application/json" \
  -d '{"source_satellite_id":"SAT-01","destination_satellite_id":"SAT-04","message_type":"TEST","payload":"Direct P2P test"}' 2>&1 | grep -E '"success"|"relay_status"|"latency_ms"'
```

### Watch Heartbeats
```bash
docker compose logs -f mission-control | grep heartbeat
```

### Watch Failure Detection
```bash
docker compose logs -f mission-control | grep "FAILURE DETECTOR"
```

### Monitor Container Status
```bash
watch -n 1 'docker compose ps | grep satellite'
```

### Stop a Satellite
```bash
docker compose stop satellite-03
```

### Restart a Satellite
```bash
docker compose start satellite-03
```

### View Complete System Status
```bash
curl -s http://localhost:8000/api/health | head -20
```

---

## PART 7: EXPECTED RESULTS & INDICATORS

| Feature | Expected Behavior | Success Indicator |
|---------|-------------------|-------------------|
| **All Services Start** | Containers reach "Up" status | `docker compose ps` shows all "Up" |
| **Satellite Registration** | 5 satellites appear in registry | `/api/satellites` returns 5 objects |
| **Heartbeats** | Every 2 seconds per satellite | Backend logs show continuous POST /heartbeat |
| **Health Scoring** | Score 90-100 for HEALTHY | `/api/satellites` shows scores |
| **gRPC Working** | GetHealth() returns data | `/api/rpc/invoke` latency < 500ms |
| **P2P Direct Link** | Message arrives without relay | `relay_status` says "No Mission Control Relay" |
| **WebSocket Streaming** | Charts update without refresh | Real-time Telemetry page auto-updates |
| **Failure Detection** | Marked OFFLINE after 10s timeout | Stop satellite → wait 12s → status = OFFLINE |
| **Failure Recovery** | Auto-marked HEALTHY on restart | Restart satellite → wait 5s → status = HEALTHY |
| **Frontend Access** | Pages render correctly | `http://localhost:3000` loads all routes |
| **Demo Center** | All 14 demos executable | `/demo-center` page loads and buttons work |
| **Teacher Q&A** | All 11 questions answered | `/teacher-questions` displays all Q&A |

---

## PART 8: TROUBLESHOOTING

### If Docker services don't start:
```bash
# Check for port conflicts
netstat -ano | findstr :8000
netstat -ano | findstr :3000

# Kill process on port (Windows)
taskkill /PID <PID> /F

# Try again
docker compose up -d
```

### If backend can't connect to database:
```bash
# Check postgres container
docker compose logs postgres

# Restart postgres
docker compose restart postgres
```

### If satellites can't register:
```bash
# Check satellite logs
docker compose logs satellite-01

# Verify network connectivity
docker compose exec satellite-01 ping mission-control
```

### If frontend shows blank page:
```bash
# Check frontend logs
docker compose logs frontend

# Rebuild frontend
docker compose up --build frontend
```

### If WebSocket not updating:
```bash
# Check browser console (F12)
# Verify connection to /ws endpoint
curl -i http://localhost:8000/ws

# Restart backend
docker compose restart mission-control
```

---

## PART 9: FILES REFERENCE

### Frontend Pages
| Page | Route | File |
|------|-------|------|
| Mission Overview | `/` | `frontend/src/pages/MissionOverview.jsx` |
| Constellation Map | `/topology` | `frontend/src/pages/ConstellationMap.jsx` |
| Communication Observatory | `/observatory` | `frontend/src/pages/CommunicationObservatory.jsx` |
| Satellite Registry | `/registry` | `frontend/src/pages/SatelliteRegistryPage.jsx` |
| Live Telemetry | `/telemetry` | `frontend/src/pages/LiveTelemetryPage.jsx` |
| Fault Simulator | `/faults` | `frontend/src/pages/FaultSimulatorPage.jsx` |
| WebRTC Feed | `/multimedia` | `frontend/src/pages/MultimediaPage.jsx` |
| Classroom Demo | `/demo-center` | `frontend/src/pages/SystemHealthDemo.jsx` |
| Teacher Q&A | `/teacher-questions` | `frontend/src/pages/TeacherQuestionsPage.jsx` |

### Backend Components
| Component | Purpose | File |
|-----------|---------|------|
| Main API | FastAPI routes | `backend/main.py` |
| Health Engine | Health score calculation | `backend/services/health_engine.py` |
| Service Registry | Satellite registry | `backend/registry/service_registry.py` |
| gRPC Client | RPC invocation | `backend/communication/grpc_client.py` |
| RabbitMQ Manager | Message broker | `backend/communication/rabbitmq_manager.py` |
| WebSocket Manager | Real-time updates | `backend/communication/websocket_manager.py` |
| WebRTC Signaling | Video stream setup | `backend/communication/webrtc_signaling.py` |
| Fault Simulator | Failure injection | `backend/faults/fault_simulator.py` |
| Database Models | Data schema | `backend/database/models.py` |

### Satellite Components
| Component | Purpose | File |
|-----------|---------|------|
| Satellite Node | Core satellite logic | `satellites/satellite_node.py` |
| Protocol Definition | gRPC interface | `proto/satellite.proto` |

### Configuration
| Config | Purpose | File |
|--------|---------|------|
| Docker Compose | Container orchestration | `docker-compose.yml` |
| Backend Config | Settings | `backend/config.py` |
| Backend Dockerfile | Backend image | `docker/Dockerfile.backend` |
| Frontend Dockerfile | Frontend image | `docker/Dockerfile.frontend` |
| Satellite Dockerfile | Satellite image | `docker/Dockerfile.satellite` |

---

## FINAL NOTES

✅ **Project Status**: FULLY OPERATIONAL
✅ **All Systems**: TESTED & VERIFIED
✅ **Failure Detection**: CONFIRMED WORKING
✅ **Failure Recovery**: CONFIRMED WORKING  
✅ **Frontend Pages**: ALL ACCESSIBLE
✅ **Demo Center**: FULLY FUNCTIONAL
✅ **Teacher Q&A**: COMPREHENSIVE

**Ready for viva presentation!**

---

Generated: 2026-09-02
