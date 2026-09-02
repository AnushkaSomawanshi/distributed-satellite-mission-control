# REST API & WebSocket Interface Specification

A complete reference documentation for the FastAPI endpoints, WebSocket event streams, and request/response payloads in the **Distributed Satellite Monitoring System**.

---

## 1. Base URLs & Protocol Endpoints

- **REST API Base URL**: `http://localhost:8000/api`
- **WebSocket Endpoint**: `ws://localhost:8000/ws`
- **OpenAPI Swagger UI**: `http://localhost:8000/docs`
- **ReDoc API Documentation**: `http://localhost:8000/redoc`

---

## 2. API Endpoint Summary Matrix

| Category | Method | Endpoint Path | Description |
| :--- | :--- | :--- | :--- |
| **Registry** | `POST` | `/api/satellites/register` | Register a new satellite node or update metadata |
| **Registry** | `POST` | `/api/satellites/heartbeat` | Receive satellite heartbeat & telemetry sample |
| **Registry** | `GET` | `/api/satellites` | List all registered satellite discovery records |
| **Registry** | `GET` | `/api/satellites/{satellite_id}` | Get metadata for a specific satellite node |
| **RPC** | `POST` | `/api/rpc/invoke` | Execute unary gRPC method on target satellite |
| **P2P** | `POST` | `/api/p2p/send` | Trigger direct P2P message between two satellites |
| **Faults** | `POST` | `/api/faults/inject` | Inject anomaly (STOP, TEMP_SPIKE, LATENCY, etc.) |
| **Faults** | `POST` | `/api/faults/clear` | Clear active faults on a node or all nodes |
| **Faults** | `GET` | `/api/faults` | Get active faults and historical fault log |
| **Observatory** | `GET` | `/api/observatory/stats` | Return stats for WS, RabbitMQ, WebRTC, and nodes |
| **Consensus** | `POST` | `/api/election/ring` | Trigger Ring Leader Election algorithm |
| **Health** | `GET` | `/api/health` | Return system-wide health & liveness summary |
| **WebRTC** | `POST` | `/api/webrtc/offer` | Process WebRTC SDP offer and generate answer |
| **WebRTC** | `POST` | `/api/webrtc/ice-candidate` | Register WebRTC ICE network candidate |
| **WebRTC** | `GET` | `/api/webrtc/status` | Get active WebRTC peer connection sessions |
| **WebSocket** | `WS` | `/ws` | Full-duplex real-time state & telemetry stream |

---

## 3. Detailed Endpoint Specifications

### A. Satellite Service Registry APIs

#### 1. `POST /api/satellites/register`
Dynamic registration endpoint called by satellite nodes at startup.

##### Request Payload:
```json
{
  "satellite_id": "SAT-01",
  "node_id": "NODE-SAT-01-3325",
  "hostname": "sat-01.orbital.local",
  "address": "satellite-01",
  "grpc_port": 5001,
  "p2p_port": 6001,
  "capabilities": ["TELEMETRY", "gRPC", "P2P", "RABBITMQ", "WEBRTC"]
}
```

##### Response `200 OK`:
```json
{
  "status": "SUCCESS",
  "registration": {
    "satellite_id": "SAT-01",
    "node_id": "NODE-SAT-01-3325",
    "hostname": "sat-01.orbital.local",
    "address": "satellite-01",
    "grpc_port": 5001,
    "p2p_port": 6001,
    "status": "HEALTHY",
    "capabilities": ["TELEMETRY", "gRPC", "P2P", "RABBITMQ", "WEBRTC"],
    "last_heartbeat": 1772518400.12,
    "registered_at": 1772518400.12
  }
}
```

---

#### 2. `POST /api/satellites/heartbeat`
Periodic liveness and telemetry metric update transmitted by satellite processes every 2 seconds.

##### Request Payload:
```json
{
  "satellite_id": "SAT-01",
  "node_id": "NODE-SAT-01-3325",
  "address": "satellite-01",
  "grpc_port": 5001,
  "p2p_port": 6001,
  "battery": 95.14,
  "temperature": 30.87,
  "cpu_usage": 8.5,
  "memory_usage": 28.4,
  "signal_strength": 96.2
}
```

##### Response `200 OK`:
```json
{
  "status": "SUCCESS",
  "satellite_id": "SAT-01",
  "health_score": 100.0,
  "node_status": "HEALTHY",
  "last_heartbeat": 1772518402.15,
  "breakdown": {
    "battery_contrib": 25.0,
    "temp_contrib": 25.0,
    "cpu_contrib": 20.0,
    "mem_contrib": 15.0,
    "signal_contrib": 15.0,
    "total_score": 100.0
  }
}
```

---

#### 3. `GET /api/satellites`
Returns dynamic discovery table data for all registered satellites.

##### Response `200 OK`:
```json
{
  "satellites": [
    {
      "satellite_id": "SAT-01",
      "node_id": "NODE-SAT-01-3325",
      "hostname": "sat-01.orbital.local",
      "address": "satellite-01",
      "grpc_port": 5001,
      "p2p_port": 6001,
      "status": "HEALTHY",
      "health_score": 100.0,
      "battery": 95.14,
      "temperature": 30.87,
      "cpu_usage": 8.5,
      "seconds_since_heartbeat": 0.45,
      "capabilities": ["TELEMETRY", "gRPC", "P2P", "RABBITMQ", "WEBRTC"]
    }
  ],
  "count": 5,
  "timestamp": 1772518405.00
}
```

---

### B. Remote Procedure Calls (RPC API)

#### `POST /api/rpc/invoke`
Executes binary gRPC method on a target satellite node using `GRPCClientManager`.

##### Request Payload:
```json
{
  "target_satellite_id": "SAT-01",
  "method": "GetHealth",
  "payload": {},
  "timeout": 5.0
}
```

##### Response `200 OK`:
```json
{
  "success": true,
  "target_satellite_id": "SAT-01",
  "method": "GetHealth",
  "latency_ms": 3.42,
  "data": {
    "satellite_id": "SAT-01",
    "status": "HEALTHY",
    "health_score": 100.0,
    "battery_level": 95.14,
    "temperature": 30.87,
    "cpu_usage": 8.5,
    "uptime_seconds": 3420
  }
}
```

---

### C. Direct Peer-to-Peer API

#### `POST /api/p2p/send`
Triggers direct satellite-to-satellite messaging.

##### Request Payload:
```json
{
  "source_satellite_id": "SAT-01",
  "destination_satellite_id": "SAT-04",
  "message_type": "CROSS_LINK_DATA",
  "payload": "ORBITAL_METRICS_SYNC_01"
}
```

##### Response `200 OK`:
```json
{
  "success": true,
  "message_id": "p2p-1772518410000",
  "source": "SAT-01",
  "destination": "SAT-04",
  "direct_link": "satellite-01:6001 -> satellite-04:6004",
  "latency_ms": 4.15,
  "relay_status": "DIRECT_SATELLITE_TO_SATELLITE (No Mission Control Relay)",
  "response": {
    "acknowledged": true,
    "status_message": "Peer message received successfully at SAT-04"
  }
}
```

---

### D. Consensus & Ring Election API

#### `POST /api/election/ring`
Triggers Ring Leader Election algorithm across active satellite nodes.

##### Query Parameter:
- `initiator_id` (string, default: `"SAT-01"`)

##### Response `200 OK`:
```json
{
  "event_id": "EVT-ELECT-1772518415000",
  "status": "SUCCESS",
  "protocol": "Ring Leader Election (Highest ID Wins)",
  "initiator": "SAT-01",
  "current_leader": "SAT-05",
  "ring_topology": "SAT-01 -> SAT-02 -> SAT-03 -> SAT-04 -> SAT-05 -> SAT-01",
  "participating_nodes": ["SAT-01", "SAT-02", "SAT-03", "SAT-04", "SAT-05"],
  "failed_nodes": [],
  "latency_ms": 0.18
}
```

---

### E. Fault Injection API

#### `POST /api/faults/inject`
Injects metric anomalies or failure overrides into a target satellite node.

##### Request Payload:
```json
{
  "fault_type": "TEMP_SPIKE",
  "target_node": "SAT-03",
  "parameters": { "temperature": 85.0 }
}
```

##### Response `200 OK`:
```json
{
  "status": "SUCCESS",
  "fault": {
    "fault_id": "fault-TEMP_SPIKE-SAT-03-1772518420",
    "fault_type": "TEMP_SPIKE",
    "target_node": "SAT-03",
    "parameters": { "temperature": 85.0 },
    "applied_at": 1772518420.0,
    "is_active": true
  }
}
```

---

## 4. WebSocket Event Specification (`/ws`)

Clients connect to `ws://localhost:8000/ws`. Events are pushed as JSON objects:

```typescript
interface WebSocketMessage {
  event_type: "TELEMETRY_UPDATED" | "NODE_REGISTERED" | "NODE_DISCONNECTED" | "FAULT_INJECTED" | "FAULTS_CLEARED" | "LEADER_ELECTION_COMPLETED";
  timestamp: number;
  [key: string]: any;
}
```

### Sample `TELEMETRY_UPDATED` Event Payload:
```json
{
  "event_type": "TELEMETRY_UPDATED",
  "telemetry": {
    "satellite_id": "SAT-01",
    "battery": 95.14,
    "temperature": 30.87,
    "cpu_usage": 8.5,
    "memory_usage": 28.4,
    "signal_strength": 96.2,
    "health_score": 100.0,
    "status": "HEALTHY",
    "timestamp": 1772518425.0
  },
  "timestamp": 1772518425.0
}
```
