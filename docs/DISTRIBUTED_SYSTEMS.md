# Distributed Systems Concepts & Viva Guide

A detailed academic mapping connecting core Distributed Systems theoretical concepts to the concrete source code, communication protocols, and visual frontend evidence in the **Distributed Satellite Monitoring System**.

---

## UNIT 1 — Introduction to Distributed Systems

### 1. Distributed System Definition
A distributed system is a collection of autonomous computing entities that communicate over a network to present a coherent, single system to users.

#### Project Demonstration:
- **Autonomous Entities**: 5 independent satellite processes (`SAT-01` to `SAT-05`) executing isolated asyncio event loops in separate Docker containers.
- **Network Communication**: Nodes communicate over Docker container bridges using gRPC, RabbitMQ AMQP, WebSockets, and P2P HTTP/TCP.
- **Single System Image**: The React frontend presents a unified Mission Control dashboard aggregating state from all distributed nodes.
- **Implementation**: [`satellites/satellite_node.py`](../satellites/satellite_node.py) and [`backend/main.py`](../backend/main.py).

---

### 2. Goals of Distributed Systems

| Goal | System Implementation | Evidence Location |
| :--- | :--- | :--- |
| **Resource Sharing** | Mission Control shares central registry lookup and database storage across satellite nodes. | [`backend/registry/service_registry.py`](../backend/registry/service_registry.py) |
| **Transparency** | Access transparency via gRPC stubs (`grpc_client.py`); location transparency via hostname resolution (`satellite-01`). | [`backend/communication/grpc_client.py`](../backend/communication/grpc_client.py) |
| **Scalability** | Microservice container architecture permits scaling from 5 to N satellite instances by updating `docker-compose.yml`. | [`docker-compose.yml`](../docker-compose.yml) |
| **Reliability & Availability** | Continuous heartbeat TTL sweeper marks unresponsive nodes `OFFLINE` without crashing Mission Control. | [`backend/main.py`](../backend/main.py#L34-L53) |
| **Concurrency** | Non-blocking `asyncio` event loops process concurrent heartbeats, RPC requests, and WebSocket pushes. | [`satellites/satellite_node.py`](../satellites/satellite_node.py) |

---

### 3. Types of Distributed Systems
The project represents a **Distributed Pervasive / Sensor & Mission Control System**, combining:
1. **Distributed Control Systems**: Mission Control orchestrates autonomous satellite microservices.
2. **Distributed Information Systems**: RabbitMQ message queues ingest telemetry logs asynchronously into PostgreSQL.

---

### 4. Distributed Architecture Models
- **Client-Server Model**: React UI (client) requests status from Mission Control FastAPI backend (server).
- **Service-Oriented Microservices**: Mission Control and 5 satellites operate as decoupled HTTP/gRPC services.
- **Peer-to-Peer (P2P) Model**: Satellites initiate direct cross-link transmissions (`SAT-01` ➔ `SAT-04`) bypassing Mission Control.

---

### 5. Key Distributed Design Issues
- **Partial Failures**: One satellite container crashing (`docker compose stop satellite-02`) does not disrupt remaining nodes.
- **Communication Latency**: Network delays simulated via `FaultSimulator` (`HIGH_LATENCY` injection).
- **Naming & Addressing**: Solved via `SatelliteRegistry` dynamic endpoint mapping (`gRPC:5001`, `P2P:6001`).
- **State Consistency**: Heartbeat timestamps reconcile active constellation state across WebSockets.

---

### 6. Middleware Layer
Middleware abstracts heterogeneous network layers into uniform programming interfaces.
- **FastAPI / Uvicorn**: Web & WebSocket middleware.
- **gRPC**: RPC middleware for structured binary protocol serialization.
- **RabbitMQ AMQP**: Message-oriented middleware for decoupled queue processing.

---

### 7. Model of Distributed Computation
Nodes compute locally by stepping metric simulation functions (`step_telemetry()`) and exchange explicit messages over network channels. No shared memory exists between containers.

---

### 8. Virtualization & Containerization
- **Docker Compose Blueprint**: Defines 9 isolated containers operating on a virtual bridge network (`ds-project_default`).
- **Containerization vs Distributed System**: Containerization provides process isolation and network virtual bridges; distributed system concepts (RPC, consensus, heartbeat Liveness) govern inter-process communication logic across those bridges.

---

### 9. Distributed Multimedia / Real-Time Streams
Demonstrated via **WebRTC Signaling Manager** ([`backend/communication/webrtc_signaling.py`](../backend/communication/webrtc_signaling.py)), processing SDP offer/answer exchanges and ICE candidates for peer-to-peer real-time telemetry streaming channels.

---

## UNIT 2 — Communication & Advanced Concepts

### 10. Remote Procedure Calls (RPC / gRPC)

#### Concept & Need:
RPC abstracts network calls to resemble local function calls, providing strong typing and high-performance binary serialization.

#### Project Implementation:
- **Proto Schema**: [`proto/satellite.proto`](../proto/satellite.proto) defining `SatelliteService`.
- **Servicer**: `SatelliteNode` in [`satellites/satellite_node.py`](../satellites/satellite_node.py#L165-L220).
- **Client Manager**: `GRPCClientManager` in [`backend/communication/grpc_client.py`](../backend/communication/grpc_client.py).

#### Data Flow:
$$\text{React UI} \xrightarrow{\text{POST /api/rpc/invoke}} \text{FastAPI } \texttt{invoke\_rpc()} \xrightarrow{\text{gRPC Binary Protocol}} \text{Satellite Container (Port 5001)} \xrightarrow{} \text{GetHealth() Response}$$

#### Evidence & Viva Explanation:
- **Frontend Evidence**: Triggering gRPC invocations on the Communication Observatory (`/observatory`) page displays live latency (ms) and protobuf response data.
- **Viva Prompt**: *"How does gRPC differ from HTTP REST in this project?"*  
  **Answer**: *"gRPC uses HTTP/2 transport and Protocol Buffer binary serialization, reducing payload overhead and latency compared to text-based JSON over HTTP/1.1."*

---

### 11. Message-Oriented Communication (RabbitMQ)

#### Concept & Need:
Asynchronous messaging decouples telemetry producers from consumers, preventing telemetry bursts from overloading Mission Control.

#### Project Implementation:
- **Broker**: RabbitMQ 3.9 container running AMQP on port `5672`.
- **Manager**: `RabbitMQManager` in [`backend/communication/rabbitmq_manager.py`](../backend/communication/rabbitmq_manager.py).
- **Data Flow**: Satellite publishes telemetry ➔ RabbitMQ Exchange `telemetry_exchange` ➔ Ingestion queue ➔ FastAPI callback ➔ WebSocket broadcast.

---

### 12. Stream-Oriented Communication (WebSockets)

#### Concept & Need:
Push-based full-duplex communication allows Mission Control to update live UI charts instantly without HTTP polling.

#### Project Implementation:
- **Manager**: `ConnectionManager` in [`backend/communication/websocket_manager.py`](../backend/communication/websocket_manager.py).
- **Endpoint**: `@app.websocket("/ws")` in [`backend/main.py`](../backend/main.py#L443-L452).
- **Events**: `TELEMETRY_UPDATED`, `NODE_REGISTERED`, `NODE_DISCONNECTED`, `FAULT_INJECTED`, `LEADER_ELECTION_COMPLETED`.

---

### 13. Peer-to-Peer Communication (P2P)

#### Concept & Need:
Satellites in orbit require direct cross-links to exchange cross-track telemetry and emergency alerts without relaying through ground stations.

#### Project Implementation:
- **Endpoint**: `POST /api/p2p/send` triggers `POST /p2p/send_to_peer` on source satellite container.
- **Execution**: Source satellite opens direct HTTP/TCP connection to target satellite's P2P port (`6001-6005`), receiving a peer acknowledgment object.

---

### 14. Naming, Addressing & Service Discovery
- **Naming**: Satellites identified by logical `satellite_id` (`SAT-01`) and node ID (`NODE-SAT-01-xxxx`).
- **Addressing**: Hostnames (`sat-01.orbital.local`), IP addresses (`satellite-01`), gRPC ports (`5001-5005`), and P2P ports (`6001-6005`).
- **Discovery**: In-memory `SatelliteRegistry` lookup table ([`backend/registry/service_registry.py`](../backend/registry/service_registry.py)).

---

### 15. Leader Election (Ring Algorithm)
- **Algorithm**: Logical Ring traversal (`SAT-01 ➔ SAT-02 ➔ SAT-03 ➔ SAT-04 ➔ SAT-05 ➔ SAT-01`).
- **Highest ID Wins**: Traverses active nodes, bypasses `OFFLINE` nodes, and elects max ID as leader (`SAT-05`).
- **Implementation**: `run_ring_election()` in [`backend/registry/service_registry.py`](../backend/registry/service_registry.py#L140-L195).

---

## Concept-to-Implementation Master Matrix

| Distributed Systems Concept | Project Feature | Implementation File | Verification Command / URL |
| :--- | :--- | :--- | :--- |
| **Microservice Architecture** | 5 Satellite Nodes + Mission Control | [`docker-compose.yml`](../docker-compose.yml) | `docker compose ps` |
| **Dynamic Naming & Discovery** | Service Registration & Discovery Table | [`backend/registry/service_registry.py`](../backend/registry/service_registry.py) | `http://localhost:3000/registry` |
| **Liveness & Failure Sweeper** | Heartbeat TTL Timeout Sweeper | [`backend/main.py`](../backend/main.py#L34-L53) | `docker compose stop satellite-02` |
| **Remote Procedure Calls (RPC)** | Unary gRPC `SatelliteService` | [`backend/communication/grpc_client.py`](../backend/communication/grpc_client.py) | `http://localhost:3000/observatory` |
| **Message-Oriented Queue** | RabbitMQ Telemetry Exchange | [`backend/communication/rabbitmq_manager.py`](../backend/communication/rabbitmq_manager.py) | `http://localhost:15672/` |
| **Stream-Oriented Updates** | Live WebSockets `/ws` Push | [`backend/communication/websocket_manager.py`](../backend/communication/websocket_manager.py) | `http://localhost:3000/telemetry` |
| **Peer-to-Peer Cross-Links** | Direct Inter-Satellite Messaging | [`satellites/satellite_node.py`](../satellites/satellite_node.py#L225-L260) | `http://localhost:3000/observatory` |
| **Consensus & Election** | Ring Leader Election Algorithm | [`backend/registry/service_registry.py`](../backend/registry/service_registry.py#L140-L195) | `http://localhost:3000/observatory` |

---

## Practical Panel Viva Questions & Concise Answers

### Q1: What makes this project a distributed system rather than a monolith?
> **Answer**: *"The system consists of 6 distinct application processes (Mission Control + 5 satellites) running in isolated Docker containers with independent memory spaces. They communicate exclusively across virtual network bridges using gRPC, AMQP, WebSockets, and P2P HTTP protocols."*

### Q2: How does Mission Control know when a satellite node crashes?
> **Answer**: *"Each satellite sends HTTP heartbeats every 2 seconds. Mission Control runs an asynchronous background sweeper task every 3 seconds. If `current_time - last_heartbeat > 10.0 seconds`, the sweeper marks the satellite `OFFLINE` and broadcasts a `NODE_DISCONNECTED` event over WebSockets."*

### Q3: Why is gRPC used alongside WebSockets and RabbitMQ?
> **Answer**: *"Each protocol satisfies a distinct communication requirement: gRPC provides strongly-typed synchronous control actions; RabbitMQ provides resilient asynchronous queuing for telemetry streams; WebSockets provide low-latency server-to-client push updates to the React frontend."*

### Q4: How does direct P2P messaging bypass Mission Control?
> **Answer**: *"When P2P transmission is triggered, Mission Control provides endpoint discovery metadata from `SatelliteRegistry`. The source satellite container then opens a direct HTTP/TCP client socket to the destination container's P2P port (`6001-6005`), transmitting the payload directly between satellite containers."*

### Q5: How is the leader elected if a satellite node fails?
> **Answer**: *"The Ring Leader Election algorithm constructs an ordered ring of active node IDs. It bypasses nodes marked `OFFLINE` by the failure detector, passes candidate IDs along active links, and elects the node with the highest ID (`SAT-05` nominally, or `SAT-04` if `SAT-05` fails) as the new coordinator."*
