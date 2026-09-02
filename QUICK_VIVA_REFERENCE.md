# QUICK REFERENCE GUIDE - VIVA DEMONSTRATION
## One-Page Cheat Sheet for Rapid Demonstrations

---

## STARTUP (One Command)
```bash
cd C:\Users\Anushka\Downloads\DS-Project
docker compose up -d
```
**Wait 15-20 seconds. All containers should show "Up" status.**

---

## VERIFICATION
```bash
docker compose ps -a
```
Expected: 9 containers running (postgres, rabbitmq, mission-control, frontend, satellite-01 through 05)

---

## BROWSER ACCESS
- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **RabbitMQ UI:** http://localhost:15672 (guest/guest)

---

## DEMO SEQUENCE (15 minutes total)

### DEMO 1: System Architecture (2 min)
```
Browser: http://localhost:3000
Click: "Constellation Topology"
Show: 5 independent satellite nodes
```
**Say:** "5 separate processes, each running independently"

### DEMO 2: Service Registry (1.5 min)
```
Browser: Click "Satellite Registry" 
Show: Table with all 5 satellites, addresses, ports
```
**Say:** "Names map to IP:ports - this is Service Discovery"

### DEMO 3: Heartbeat Monitoring (1.5 min)
```
Terminal: docker compose logs -f mission-control | grep heartbeat
Show: Continuous heartbeat messages every 2 seconds
```
**Say:** "Each satellite sends heartbeat every 2 seconds. Health monitoring."

### DEMO 4: gRPC Remote Call (1.5 min)
```bash
curl -X POST http://localhost:8000/api/rpc/invoke \
  -H "Content-Type: application/json" \
  -d '{"target_satellite_id":"SAT-01","method":"GetHealth"}'
```
**Say:** "Remote Procedure Call using gRPC - latency ~250ms"

### DEMO 5: P2P Direct Communication (1.5 min)
```bash
curl -X POST http://localhost:8000/api/p2p/send \
  -H "Content-Type: application/json" \
  -d '{"source_satellite_id":"SAT-01","destination_satellite_id":"SAT-04","message_type":"TEST","payload":"msg"}'
```
**Say:** "Direct P2P link, no central relay - 'DIRECT_SATELLITE_TO_SATELLITE'"

### DEMO 6: Real-Time Streaming (1 min)
```
Browser: Click "Live Telemetry Charts"
Show: Charts updating in real-time without refresh
```
**Say:** "WebSocket streaming - real-time updates via persistent TCP connection"

### DEMO 7: Failure Detection (3 min) - CRITICAL
```bash
# Terminal 1:
docker compose logs -f mission-control | grep FAILURE

# Terminal 2:
docker compose stop satellite-03
# Wait 13 seconds
curl http://localhost:8000/api/satellites/SAT-03
# Show: "status":"OFFLINE"
```
**Say:** "No heartbeat for >10 seconds → automatically marked OFFLINE"

### DEMO 8: Failure Recovery (2 min) - CRITICAL
```bash
docker compose start satellite-03
# Wait 5 seconds
curl http://localhost:8000/api/satellites/SAT-03
# Show: "status":"HEALTHY" with new Node-ID
```
**Say:** "Node restarts → sends heartbeat → automatically recovered. Resilient system."

---

## QUICK CHECKS

### All satellites healthy?
```bash
curl -s http://localhost:8000/api/satellites | grep -o '"status":"[^"]*"' | sort | uniq
```
Expected: All showing `"status":"HEALTHY"`

### Backend responding?
```bash
curl http://localhost:8000/api/health
```
Expected: `"status":"HEALTHY"`

### Frontend loading?
```bash
curl http://localhost:3000 | head -5
```
Expected: `<!DOCTYPE html>`

---

## DISTRIBUTED SYSTEMS CONCEPTS QUICK MAP

| Concept | Demo | File |
|---------|------|------|
| **Distributed Nodes** | 5 satellites topology | `satellites/satellite_node.py` |
| **Service Discovery** | Registry page | `backend/registry/service_registry.py` |
| **RPC** | gRPC GetHealth() | `proto/satellite.proto` |
| **Message Queue** | RabbitMQ stats | `backend/communication/rabbitmq_manager.py` |
| **Real-time Streaming** | Telemetry charts | `backend/communication/websocket_manager.py` |
| **P2P** | SAT-01→SAT-04 direct | `satellites/satellite_node.py` (P2P handler) |
| **Failure Detection** | Stop SAT-03 | `backend/registry/service_registry.py::sweep_failures()` |
| **Failure Recovery** | Restart SAT-03 | Auto re-registration |
| **Health Scoring** | Registry health column | `backend/services/health_engine.py` |
| **Containerization** | `docker compose ps` | 9 independent containers |

---

## BROWSER PAGES FOR SHOWING

### Page 1: Classroom Demo Center
```
Route: http://localhost:3000/demo-center
Shows: 14 interactive demos matching actual backend
```

### Page 2: Teacher Questions & Viva
```
Route: http://localhost:3000/teacher-questions
Shows: 11 common questions with answers + code references
```

### Page 3: Live Telemetry (Real-time Proof)
```
Route: http://localhost:3000/telemetry
Shows: Continuously updating charts (WebSocket working)
```

### Page 4: Satellite Registry
```
Route: http://localhost:3000/registry
Shows: All 5 satellites with service discovery table
```

### Page 5: Constellation Topology
```
Route: http://localhost:3000/topology
Shows: Visual diagram of independent nodes
```

---

## KEY EVIDENCE LOCATIONS

### Source Code
- Backend: `backend/main.py` (all endpoints)
- Satellites: `satellites/satellite_node.py`
- Protocol: `proto/satellite.proto`
- Health: `backend/services/health_engine.py`
- Registry: `backend/registry/service_registry.py`

### Configuration
- Services: `docker-compose.yml`
- Backend Config: `backend/config.py`

### Frontend
- Demo Center: `frontend/src/pages/SystemHealthDemo.jsx`
- Teacher Q&A: `frontend/src/pages/TeacherQuestionsPage.jsx`
- All Pages: `frontend/src/pages/*.jsx`

---

## FAILURE/RECOVERY TEST CHECKLIST

Before stopping SAT-03:
- [ ] Verify SAT-03 status = HEALTHY
- [ ] Have 2 terminals open
- [ ] Terminal 1: Watching backend logs
- [ ] Terminal 2: Running curl commands

After stopping SAT-03:
- [ ] Wait 13 seconds
- [ ] Check SAT-03 status = OFFLINE
- [ ] Verify other satellites remain HEALTHY
- [ ] Note health_score = 0.0

After restarting SAT-03:
- [ ] Verify status = HEALTHY within 5 seconds
- [ ] Note new node_id (proves fresh instance)
- [ ] Confirm health_score = 100.0
- [ ] Show all 5 satellites HEALTHY again

---

## PROFESSOR QUESTIONS QUICK ANSWERS

| Q | Short Answer | Demo Location |
|---|---|---|
| Where are 5 independent nodes? | Satellites running in separate containers | `docker compose ps \| grep satellite` |
| Where is RPC? | GetHealth() over gRPC | `/api/rpc/invoke` endpoint |
| Where is message queue? | RabbitMQ telemetry.exchange | Observatory stats page |
| Where is real-time streaming? | WebSocket /ws endpoint | Telemetry charts auto-update |
| Where is P2P? | SAT-01 → SAT-04 direct | `/api/p2p/send` no-relay response |
| Where is failure detection? | Heartbeat timeout 10s TTL | Stop SAT-03, wait 13s |
| Where is recovery? | Auto restart → re-register | Restart SAT-03, instant recovery |
| Where is middleware? | gRPC, RabbitMQ, WebSocket abstraction | Middleware Architecture page |
| Where are names & addresses? | Satellite Registry mapping | `/registry` page table |
| Where is persistence? | PostgreSQL storing events/telemetry | Database tables exist |
| Where is virtualization? | Docker containers | `docker compose ps` |

---

## TERMINAL COMMANDS READY-TO-PASTE

### Status Check
```bash
curl -s http://localhost:8000/api/health
```

### List Satellites
```bash
curl -s http://localhost:8000/api/satellites
```

### Watch Heartbeats
```bash
docker compose logs -f mission-control | grep heartbeat
```

### Stop SAT-03
```bash
docker compose stop satellite-03
```

### Check SAT-03 Status
```bash
curl -s http://localhost:8000/api/satellites/SAT-03 | grep -o '"status":"[^"]*"'
```

### Restart SAT-03
```bash
docker compose start satellite-03
```

### gRPC Test
```bash
curl -X POST http://localhost:8000/api/rpc/invoke \
  -H "Content-Type: application/json" \
  -d '{"target_satellite_id":"SAT-01","method":"GetHealth"}'
```

### P2P Test
```bash
curl -X POST http://localhost:8000/api/p2p/send \
  -H "Content-Type: application/json" \
  -d '{"source_satellite_id":"SAT-01","destination_satellite_id":"SAT-04","message_type":"TEST","payload":"Demo"}'
```

---

## TIMING GUIDE

- **Opening statement:** 1 min
- **System Architecture tour:** 2 min
- **Service Registry demo:** 1.5 min
- **Heartbeat monitoring:** 1.5 min
- **gRPC RPC demo:** 1.5 min
- **P2P demo:** 1.5 min
- **Real-time streaming:** 1 min
- **Failure detection (STOP):** 3 min
- **Failure recovery (RESTART):** 2 min
- **Q&A / Closeout:** 2.5 min

**Total: ~18 minutes (leaves buffer for questions)**

---

## IF SOMETHING GOES WRONG

| Problem | Solution |
|---------|----------|
| Services not starting | `docker compose down && docker compose up -d` |
| Container crashed | `docker compose restart [service]` |
| API not responding | `curl http://localhost:8000/api/health` |
| Frontend blank | Check browser console (F12) for errors |
| Ports already in use | `netstat -ano` then `taskkill /PID /F` |
| Lost satellite status | Wait 3s (sweep interval), SAT-03 still stops at 10s |

---

## REMEMBER TO SAY

- "This is NOT a monolithic application - each satellite is completely independent"
- "The system gracefully degrades - if one satellite fails, others keep working"
- "Failure detection is automatic - no human intervention needed"
- "This demonstrates real distributed systems concepts, not mocked data"
- "All communication is real - gRPC, message queues, WebSocket actually functioning"

---

**Last Updated:** September 2, 2026
**Status:** ✅ READY FOR VIVA
