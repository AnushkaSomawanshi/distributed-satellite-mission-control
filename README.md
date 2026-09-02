# Distributed Satellite Constellation Health Monitoring & Autonomous Fault Recovery System

Academic Distributed Systems Project built for **FA-1 Distributed Systems Syllabus** (Unit 1: Introduction to Distributed Systems & Unit 2: Communication), designed to cleanly extend to **FA-2** (Lamport Clocks, Vector Clocks, Leader Election, Global Snapshots, Task Redistribution).

---

## 🚀 System Architecture Overview

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

## 🛠️ Technology Stack & Communication Protocols

- **Backend**: Python 3.11, FastAPI, Async SQLAlchemy, SQLite / PostgreSQL.
- **Microservices**: 5 independent satellite processes (`SAT-01` to `SAT-05`).
- **Communication Models**:
  - **RPC**: gRPC (`proto/satellite.proto`) for `GetHealth()`, `Ping()`, `GetSatelliteInfo()`.
  - **Message-Oriented**: RabbitMQ telemetry fanout exchange and queues (`telemetry.queue`).
  - **Stream-Oriented**: WebSockets JSON frame broadcasting at ~10 msg/sec.
  - **Peer-to-Peer**: Direct HTTP/socket cross-links between satellites without central routing.
  - **Multimedia**: WebRTC PeerConnection with SDP offer/answer signaling for camera feed.
- **Service Discovery**: Satellite Registry with address lookup and heartbeat TTL failure detection.
- **Frontend**: React 18, Vite, Tailwind CSS, Lucide Icons, Recharts, Orbitron dark space UI.

---

## ⚡ Quick Start Instructions (Local PC)

### Option A: Standard Local Execution (Zero-Docker / Standalone)

1. **Install Python & Node Dependencies**:
   ```bash
   pip install fastapi uvicorn pydantic pydantic-settings sqlalchemy aiosqlite grpcio grpcio-tools httpx aio-pika pytest
   cd frontend
   npm install
   ```

2. **Run Mission Control & 5 Satellite Microservices**:
   ```bash
   python scripts/run_local.py
   ```

3. **Run React Mission Control Frontend**:
   ```bash
   cd frontend
   npm run dev
   ```

4. Access the web interface at `http://localhost:3000`.

---

### Option B: Docker Containerized Execution

Build and run all services (Postgres, RabbitMQ, Mission Control, Satellites 01-05, Frontend) with a single command:
```bash
docker compose up --build
```

---

## 🧪 Running Automated Test Suite

Run unit and integration tests verifying health calculation, service registry TTL sweeper, gRPC, and fault injection:
```bash
$env:PYTHONPATH="."
python -m pytest tests/
```

---

## 🎓 Classroom Presentation Script (Demo 1 to 14)

Open the **Classroom Presentation Demo Center** page in the UI (`http://localhost:3000/demo-center`) for single-click execution during project evaluation:
- **Demo 1**: Verify Start System & Process Health.
- **Demo 2**: Inspect 5 Independent Microservice Processes.
- **Demo 3**: Verify Dynamic Satellite Registration & Service Discovery.
- **Demo 4**: Observe Autonomous Orbit Telemetry Generation.
- **Demo 5**: Execute gRPC Call `GetHealth(SAT-03)`.
- **Demo 6**: Observe RabbitMQ Message Publishing & Consuming.
- **Demo 7**: Inspect Live WebSocket Telemetry Streaming.
- **Demo 8**: Execute Direct P2P Satellite Cross-link (`SAT-01 -> SAT-04`).
- **Demo 9**: Establish WebRTC Video Stream for Camera Feed.
- **Demo 10**: Inject Satellite Node Crash (`STOP_NODE`) & Observe Heartbeat Timeout.
- **Demo 11**: Restart Satellite Node (`RESTART_NODE`) & Observe Dynamic Re-registration.
- **Demo 12**: Inject Network Latency & Measure Response Degradation.
- **Demo 13**: Inject Packet Loss & Observe Resilient Exception Handling.
- **Demo 14**: Replay Communication Event History Timeline.
