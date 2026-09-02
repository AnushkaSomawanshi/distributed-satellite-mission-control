# DISTRIBUTED SATELLITE CONSTELLATION ARCHITECTURE

## System Architecture Diagram

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

## Layered Component Breakdown

1. **Mission Control Backend (`backend/`)**:
   - `FastAPI` REST orchestrator.
   - `SatelliteRegistry`: Dynamic service registry with heartbeat TTL failure detection.
   - `HealthEngine`: Calculates score (0-100%) and maps to `HEALTHY`, `WARNING`, `CRITICAL`, `OFFLINE`.
   - `GRPCClientManager`: Async gRPC client pool.
   - `RabbitMQManager`: Pub/sub message queue manager with in-memory fallback.
   - `WebSocketManager`: Continuous live telemetry broadcaster.
   - `FaultSimulator`: Latency injection, packet loss, battery drain, node crash/restart controller.

2. **Satellite Microservices (`satellites/`)**:
   - 5 independent processes (`SAT-01` to `SAT-05`).
   - Autonomous orbit physics telemetry loop.
   - Native gRPC server listening on ports 5001-5005.
   - Direct HTTP/socket P2P endpoint listening on ports 6001-6005 (`/p2p/send_to_peer` and `/p2p/receive`).
