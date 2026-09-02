# MULTI-PROTOCOL COMMUNICATION SYSTEM

## Communication Models Implemented

### 1. Remote Procedure Call (RPC / gRPC)
- Protocol: `gRPC` / `HTTP/2` via `Protocol Buffers` (`proto/satellite.proto`).
- Methods: `GetHealth()`, `Ping()`, `GetSatelliteInfo()`, `ExecuteCommand()`, `SendP2PMessage()`.
- Measured Metrics: Request ID, Source, Target, Latency (ms), Response Payload.

### 2. Message-Oriented Communication (RabbitMQ)
- Protocol: `AMQP 0-9-1` via `aio-pika` with automatic in-memory fallback.
- Exchange: `telemetry.exchange` (fanout type).
- Queue: `telemetry.queue` (durable).
- Consumer: Async listener processing telemetry and broadcasting to WebSockets.

### 3. Stream-Oriented Communication (WebSockets)
- Protocol: `WebSockets` (`ws://localhost:8000/ws`).
- Data Format: JSON telemetry frames at ~10 msg/sec.
- Metrics: Active client count, Uptime, Message rate.

### 4. Direct Peer-to-Peer (P2P) Communication
- Protocol: Direct HTTP/Socket link directly between satellite processes.
- Execution Path: `SAT-01 (port 6001) -> SAT-04 (port 6004)`.
- Compliance: Mission Control NEVER relays the message. Mission Control only triggers the source satellite, which opens a direct network socket to the destination satellite.

### 5. Distributed Multimedia (WebRTC)
- Protocol: `WebRTC` / `SRTP` / `VP8`.
- Signaling: SDP Offer/Answer exchange via `/api/webrtc/offer`.
- Stream: Live animated 1080p orbital camera feed rendered onto a HTML5 canvas player.
