# FA-1 Distributed Systems Syllabus Coverage

## UNIT 1 — Introduction to Distributed Systems

| Concept | Project Implementation | Technology | Evidence File / Route |
| :--- | :--- | :--- | :--- |
| **Definition of Distributed Systems** | 5 independent satellite microservice processes (`SAT-01` to `SAT-05`) owning local state | Python Microservices, Docker | `satellites/satellite_node.py` |
| **Goals of Distributed Systems** | Resource sharing (telemetry), Concurrency, Scalability, Availability (node crash survival) | FastAPI, Health Engine | `backend/services/health_engine.py` |
| **Types of Distributed Systems** | Client-Server (React/FastAPI), Peer-to-Peer (SAT-01 -> SAT-04), Info System (RabbitMQ/DB), Multimedia (WebRTC) | gRPC, RabbitMQ, WebRTC | `backend/main.py` |
| **Distributed Architectures** | Hybrid layered architecture + direct P2P satellite cross-links | FastAPI, P2P Sockets | `frontend/src/pages/ConstellationMap.jsx` |
| **Design Issues** | Latency injection, packet loss, heartbeat timeouts, partial failures | Fault Simulator | `backend/faults/fault_simulator.py` |
| **Middleware** | gRPC Protobuf RPCs, RabbitMQ async exchanges, WebSocket broadcasters | gRPC, RabbitMQ, WebSockets | `backend/communication/` |
| **Distributed Multimedia** | Simulated satellite orbital camera feed streamed live over WebRTC SDP offer/answer | WebRTC, SDP, VP8 | `backend/communication/webrtc_signaling.py` |
| **Model of Computations** | Structured event model (`TELEMETRY_GENERATED`, `RPC_EXECUTED`, `P2P_SENT`, `NODE_DISCONNECTED`) | Async Event Bus, DB | `backend/database/models.py` |
| **Virtualization** | Docker containerization of backend, database, message broker, satellites, frontend | Docker, Docker Compose | `docker-compose.yml` |

---

## UNIT 2 — Communication

| Concept | Project Implementation | Technology | Evidence File / Route |
| :--- | :--- | :--- | :--- |
| **Fundamentals of Communication** | Network request/response, connection state handling, latency measurement, timeout handling | gRPC, HTTP/2, WebSockets | `/api/rpc/invoke` |
| **RPC (Remote Procedure Call)** | gRPC Protocol Buffers for `GetHealth()`, `Ping()`, `GetSatelliteInfo()` | gRPC, Protobuf | `proto/satellite.proto` |
| **Message-Oriented Communication** | Decoupled telemetry queue publishing and background consumer processing | RabbitMQ, AMQP, aio-pika | `backend/communication/rabbitmq_manager.py` |
| **Stream-Oriented Communication** | High-frequency continuous JSON frame broadcasting (~10 msg/s) to React charts | WebSockets | `backend/communication/websocket_manager.py` |
| **Peer-to-Peer (P2P)** | Direct satellite-to-satellite socket communication bypassing Mission Control routing | HTTP P2P Direct Sockets | `/api/p2p/send` |
| **WebRTC** | Real browser WebRTC peer connection & SDP exchange for camera streaming | WebRTC, SDP | `frontend/src/pages/MultimediaPage.jsx` |
| **Names, Identifiers & Addresses** | Satellite Registry mapping satellite IDs to hostnames, IP, gRPC & P2P endpoints | Dynamic Satellite Registry | `backend/registry/service_registry.py` |
| **Fault Tolerance** | Periodic heartbeat sweep (>10s TTL), node crash detection, re-registration on restart | Sweeper Task, Fault Sim | `/api/satellites/heartbeat` |
