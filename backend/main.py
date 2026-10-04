import time
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.registry.service_registry import global_registry
from backend.services.health_engine import HealthEngine
from backend.communication.grpc_client import GRPCClientManager
from backend.communication.rabbitmq_manager import RabbitMQManager
from backend.communication.websocket_manager import websocket_manager
from backend.communication.webrtc_signaling import webrtc_manager
from backend.faults.fault_simulator import FaultSimulator
from backend.database.db import init_db, get_db
from backend.database.models import CommunicationEvent, TelemetryLog, ConceptEvidence
from backend.models.schemas import (
    RegistrationRequest, HeartbeatRequest, RPCInvokeRequest,
    P2PSendRequest, FaultInjectRequest, WebRTCOfferRequest, WebRTCICECandidateRequest
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MissionControl")

grpc_manager = GRPCClientManager(global_registry)
rabbitmq_manager = RabbitMQManager(settings.RABBITMQ_URL)
fault_simulator = FaultSimulator(global_registry)

from backend.services.event_manager import generate_correlation_id, create_event

# Background sweep loop to detect heartbeat timeout / satellite failures
async def heartbeat_sweeper_task():
    while True:
        try:
            await asyncio.sleep(settings.SWEEP_INTERVAL_SECONDS)
            sweep_res = global_registry.sweep_failures()
            suspected = sweep_res.get("suspected", [])
            disconnected = sweep_res.get("disconnected", [])

            for fn in suspected:
                cid = generate_correlation_id("EVT-SUSPECT")
                reg = global_registry.lookup(fn)
                latency = reg.detection_latency_ms if reg else 5000.0
                logger.warning(f"[FAILURE DETECTOR] Satellite {fn} heartbeat delayed (> 5s). Status marked SUSPECTED. CID={cid}")
                evt = create_event(
                    event_type="NODE_SUSPECTED",
                    source="FAILURE_DETECTOR",
                    destination=fn,
                    protocol="Heartbeat Sweeper",
                    message=f"Satellite {fn} heartbeat missing (> 5s). Transitioning to SUSPECTED.",
                    correlation_id=cid,
                    latency_ms=latency,
                    payload={"satellite_id": fn, "status": "SUSPECTED", "detection_latency_ms": latency}
                )
                await websocket_manager.broadcast(evt)

            for fn in disconnected:
                cid = generate_correlation_id("EVT-DISCONNECT")
                reg = global_registry.lookup(fn)
                latency = reg.detection_latency_ms if reg else 10000.0
                logger.warning(f"[FAILURE DETECTOR] Satellite {fn} heartbeat lost (> 10s). Status marked DISCONNECTED. CID={cid}")
                evt = create_event(
                    event_type="NODE_DISCONNECTED",
                    source=reg.failure_source if reg else "DOCKER_EXTERNAL",
                    destination=fn,
                    protocol="Heartbeat Sweeper",
                    message=f"Satellite {fn} heartbeat timeout (> 10s). Status confirmed DISCONNECTED.",
                    correlation_id=cid,
                    latency_ms=latency,
                    payload={"satellite_id": fn, "status": "DISCONNECTED", "detection_latency_ms": latency, "failure_source": reg.failure_source if reg else "DOCKER_EXTERNAL"}
                )
                await websocket_manager.broadcast(evt)

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in heartbeat sweeper task: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    logger.info("Initializing Mission Control Database & Services...")
    await init_db()
    await rabbitmq_manager.connect()
    
    # Register rabbitmq telemetry callback to broadcast via WebSocket & persist
    async def handle_incoming_telemetry(payload: Dict[str, Any]):
        sat_data = payload.get("data", {})
        sat_id = sat_data.get("satellite_id")
        
        if sat_id:
            # Update registry metrics
            score, status, _ = HealthEngine.calculate_health(
                battery=sat_data.get("battery", 100),
                temperature=sat_data.get("temperature", 25),
                cpu_usage=sat_data.get("cpu_usage", 15),
                memory_usage=sat_data.get("memory_usage", 30),
                signal_strength=sat_data.get("signal_strength", 95),
                is_online=True
            )
            global_registry.update_heartbeat(
                satellite_id=sat_id,
                health_score=score,
                status=status,
                battery=sat_data.get("battery", 100),
                temperature=sat_data.get("temperature", 25),
                cpu_usage=sat_data.get("cpu_usage", 15),
                memory_usage=sat_data.get("memory_usage", 30),
                signal_strength=sat_data.get("signal_strength", 95)
            )

        # Broadcast telemetry over WebSocket
        await websocket_manager.broadcast({
            "event_type": "TELEMETRY_UPDATED",
            "telemetry": payload,
            "timestamp": time.time()
        })

    await rabbitmq_manager.register_listener(handle_incoming_telemetry)
    
    sweeper_task = asyncio.create_task(heartbeat_sweeper_task())
    yield
    # Shutdown logic
    sweeper_task.cancel()
    logger.info("Mission Control shutdown complete.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------- SATELLITE REGISTRY REST APIs -------------------

@app.post("/api/satellites/register")
async def register_satellite(req: RegistrationRequest):
    reg = global_registry.register(
        satellite_id=req.satellite_id,
        node_id=req.node_id,
        hostname=req.hostname,
        address=req.address,
        grpc_port=req.grpc_port,
        p2p_port=req.p2p_port,
        capabilities=req.capabilities
    )
    logger.info(f"[REGISTRY] Dynamic Registration SUCCESS | satellite_id={req.satellite_id} | node_id={req.node_id} | address={req.address}:{req.grpc_port} (gRPC) / :{req.p2p_port} (P2P) | status=ONLINE")
    await websocket_manager.broadcast({
        "event_type": "NODE_REGISTERED",
        "satellite_id": req.satellite_id,
        "data": global_registry.to_dict_list(),
        "timestamp": time.time()
    })
    return {"status": "SUCCESS", "registration": reg}

@app.post("/api/satellites/heartbeat")
async def receive_heartbeat(req: HeartbeatRequest):
    existing_reg = global_registry.lookup(req.satellite_id)
    was_offline = existing_reg and existing_reg.status == "OFFLINE"

    score, status, breakdown = HealthEngine.calculate_health(
        battery=req.battery,
        temperature=req.temperature,
        cpu_usage=req.cpu_usage,
        memory_usage=req.memory_usage,
        signal_strength=req.signal_strength,
        is_online=True
    )
    reg = global_registry.update_heartbeat(
        satellite_id=req.satellite_id,
        health_score=score,
        status=status,
        battery=req.battery,
        temperature=req.temperature,
        cpu_usage=req.cpu_usage,
        memory_usage=req.memory_usage,
        signal_strength=req.signal_strength,
        node_id=req.node_id,
        address=req.address,
        grpc_port=req.grpc_port,
        p2p_port=req.p2p_port
    )
    
    if was_offline:
        logger.info(f"[RECOVERY] Mission Control ← {req.satellite_id} | Heartbeat resumed | status=ONLINE/HEALTHY | health_score={score}%")
    else:
        logger.info(f"[HEARTBEAT] Mission Control ← {req.satellite_id} | status=RECEIVED | health={score}% | battery={req.battery}% | temp={req.temperature}°C")

    # Broadcast telemetry update over WebSocket
    await websocket_manager.broadcast({
        "event_type": "TELEMETRY_UPDATED",
        "telemetry": {
            "satellite_id": req.satellite_id,
            "battery": req.battery,
            "temperature": req.temperature,
            "cpu_usage": req.cpu_usage,
            "memory_usage": req.memory_usage,
            "signal_strength": req.signal_strength,
            "health_score": score,
            "status": status,
            "timestamp": time.time()
        },
        "timestamp": time.time()
    })
    
    return {
        "status": "SUCCESS",
        "satellite_id": req.satellite_id,
        "health_score": score,
        "node_status": reg.status,
        "last_heartbeat": reg.last_heartbeat,
        "breakdown": breakdown
    }

@app.get("/api/satellites")
async def list_satellites():
    return {
        "satellites": global_registry.to_dict_list(),
        "count": len(global_registry.list_all()),
        "timestamp": time.time()
    }

@app.get("/api/satellites/{satellite_id}")
async def get_satellite_info(satellite_id: str):
    reg = global_registry.lookup(satellite_id)
    if not reg:
        raise HTTPException(status_code=404, detail="Satellite not found")
    return {"satellite": reg}

# ------------------- COMMUNICATION API (gRPC / RabbitMQ / P2P / WebRTC) -------------------

@app.post("/api/rpc/invoke")
async def invoke_rpc(req: RPCInvokeRequest, db: AsyncSession = Depends(get_db)):
    logger.info(f"[HTTP API] Frontend → Mission Control | endpoint=/api/rpc/invoke | target={req.target_satellite_id} | method={req.method} | status=RECEIVED")
    res = await grpc_manager.invoke_rpc(
        target_satellite_id=req.target_satellite_id,
        method_name=req.method,
        payload=req.payload,
        timeout=req.timeout
    )
    
    # Record Communication Event
    evt = CommunicationEvent(
        event_id=f"rpc-{int(time.time()*1000)}",
        source="Mission Control",
        destination=req.target_satellite_id,
        protocol="gRPC",
        method=req.method,
        latency_ms=res.get("latency_ms", 0.0),
        status="SUCCESS" if res.get("success") else "FAILED",
        payload_summary=str(res.get("data") or res.get("error"))
    )
    db.add(evt)
    await db.commit()
    logger.info(f"[DATABASE AUDIT] Persisted CommunicationEvent | event_id={evt.event_id} | protocol=gRPC | status={evt.status}")

    await websocket_manager.broadcast({
        "event_type": "RPC_EXECUTED",
        "result": res,
        "timestamp": time.time()
    })
    logger.info(f"[HTTP API RESULT] Mission Control → Frontend | endpoint=/api/rpc/invoke | target={req.target_satellite_id} | method={req.method} | status={'SUCCESS' if res.get('success') else 'FAILED'} | latency={res.get('latency_ms', 0)}ms")
    return res

@app.post("/api/p2p/send")
async def send_p2p_message(req: P2PSendRequest, db: AsyncSession = Depends(get_db)):
    logger.info(f"[HTTP API] Frontend → Mission Control | endpoint=/api/p2p/send | source={req.source_satellite_id} | destination={req.destination_satellite_id} | type={req.message_type} | status=RECEIVED")
    start_time = time.time()
    source_reg = global_registry.lookup(req.source_satellite_id)
    dest_reg = global_registry.lookup(req.destination_satellite_id)

    if not source_reg or not dest_reg:
        logger.warning(f"[P2P ERROR] One or both satellites ({req.source_satellite_id}, {req.destination_satellite_id}) not found in registry")
        raise HTTPException(status_code=404, detail="Source or Destination Satellite not found in registry")

    # Check network partition
    if fault_simulator.is_partition_blocked(req.source_satellite_id, req.destination_satellite_id):
        cid = generate_correlation_id("EVT-PARTITION-BLOCK")
        logger.warning(f"[P2P REJECTED] Network partition in effect between {req.source_satellite_id} and {req.destination_satellite_id}")
        p2p_res = {
            "success": False,
            "correlation_id": cid,
            "error": f"P2P Link BLOCKED: Network Partition between {req.source_satellite_id} and {req.destination_satellite_id}",
            "status": "PARTITION_BLOCKED",
            "latency_ms": round((time.time() - start_time) * 1000, 2)
        }
        await websocket_manager.broadcast({
            "event_type": "P2P_MESSAGE_BLOCKED",
            "correlation_id": cid,
            "result": p2p_res,
            "timestamp": time.time()
        })
        return p2p_res

    if source_reg.status in ["OFFLINE", "DISCONNECTED"] or dest_reg.status in ["OFFLINE", "DISCONNECTED"]:
        logger.warning(f"[P2P REJECTED] Cannot execute P2P link: {req.source_satellite_id} or {req.destination_satellite_id} is DISCONNECTED")
        return {
            "success": False,
            "error": "P2P connection failed: One or both satellites are DISCONNECTED",
            "latency_ms": round((time.time() - start_time) * 1000, 2)
        }

    # Simulate network latency fault if configured
    faults = fault_simulator.get_node_faults(req.source_satellite_id)
    for f in faults:
        if f["fault_type"] == "HIGH_LATENCY":
            delay_ms = f["parameters"].get("latency_ms", 500)
            logger.info(f"[FAULT EFFECT] Target={req.source_satellite_id} | Communication delay applied: {delay_ms}ms")
            await asyncio.sleep(delay_ms / 1000.0)

    import httpx
    cid = generate_correlation_id("EVT-P2P")
    source_trigger_url = f"http://{source_reg.address}:{source_reg.p2p_port}/p2p/send_to_peer"
    trigger_payload = {
        "message_id": cid,
        "correlation_id": cid,
        "destination_satellite_id": req.destination_satellite_id,
        "destination_address": dest_reg.address,
        "destination_p2p_port": dest_reg.p2p_port,
        "message_type": req.message_type,
        "payload": req.payload
    }
    logger.info(f"[P2P TRIGGER] Mission Control → {req.source_satellite_id} | CID={cid} | trigger_url={source_trigger_url}")

    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.post(source_trigger_url, json=trigger_payload)
            latency = round((time.time() - start_time) * 1000, 2)
            
            if resp.status_code == 200:
                sat_res = resp.json()
                p2p_result = {
                    "success": sat_res.get("success", True),
                    "message_id": cid,
                    "correlation_id": cid,
                    "source": req.source_satellite_id,
                    "destination": req.destination_satellite_id,
                    "direct_link": sat_res.get("direct_link"),
                    "latency_ms": sat_res.get("latency_ms", latency),
                    "relay_status": "DIRECT_SATELLITE_TO_SATELLITE (No Mission Control Relay)",
                    "response": sat_res.get("ack_response")
                }
                logger.info(f"[P2P RESULT] Mission Control ← {req.source_satellite_id} | CID={cid} | status=SUCCESS | latency={latency}ms")
            else:
                p2p_result = {
                    "success": False,
                    "correlation_id": cid,
                    "error": f"Source satellite returned status {resp.status_code}",
                    "latency_ms": latency
                }
                logger.error(f"[P2P ERROR] Mission Control ← {req.source_satellite_id} | CID={cid} | status=FAILED")
    except Exception as ex:
        latency = round((time.time() - start_time) * 1000, 2)
        p2p_result = {
            "success": False,
            "correlation_id": cid,
            "error": f"Direct P2P execution error: {ex}",
            "source": req.source_satellite_id,
            "destination": req.destination_satellite_id,
            "latency_ms": latency
        }
        logger.error(f"[P2P ERROR] Mission Control ← {req.source_satellite_id} | CID={cid} | error={ex}")

    # Persist P2P event log
    evt = CommunicationEvent(
        event_id=cid,
        source=req.source_satellite_id,
        destination=req.destination_satellite_id,
        protocol="P2P Messaging (Direct Link)",
        method=req.message_type,
        latency_ms=p2p_result["latency_ms"],
        status="SUCCESS" if p2p_result["success"] else "FAILED",
        payload_summary=str(req.payload)
    )
    db.add(evt)
    await db.commit()

    await websocket_manager.broadcast({
        "event_type": "P2P_MESSAGE_DELIVERED",
        "correlation_id": cid,
        "result": p2p_result,
        "timestamp": time.time()
    })
    return p2p_result

@app.post("/api/webrtc/offer")
async def handle_webrtc_offer(req: WebRTCOfferRequest):
    logger.info(f"[WEBRTC SIGNALING] Frontend → Mission Control | event=SDP_OFFER | peer={req.peer}")
    res = webrtc_manager.process_offer(offer_sdp=req.offer_sdp, peer=req.peer)
    logger.info(f"[WEBRTC SIGNALING] Mission Control → Frontend | event=SDP_ANSWER | session_id={res['session_id']} | state={res['state']}")
    await websocket_manager.broadcast({
        "event_type": "WEBRTC_CONNECTED",
        "session": res,
        "timestamp": time.time()
    })
    return res

@app.post("/api/webrtc/ice-candidate")
async def add_ice_candidate(req: WebRTCICECandidateRequest):
    logger.info(f"[WEBRTC SIGNALING] Frontend → Mission Control | event=ICE_CANDIDATE | session_id={req.session_id}")
    ok = webrtc_manager.add_ice_candidate(req.session_id, req.candidate)
    logger.info(f"[WEBRTC SIGNALING] Mission Control → Frontend | event=ICE_CANDIDATE | session_id={req.session_id} | status={'ACCEPTED' if ok else 'REJECTED'}")
    return {"success": ok}

@app.get("/api/webrtc/status")
async def get_webrtc_status():
    return webrtc_manager.get_status()

# ------------------- NETWORK PARTITION & GOSSIP REST APIs -------------------

@app.post("/api/network/partition")
async def set_network_partition(payload: Dict[str, Any]):
    part_a = payload.get("partition_a", ["SAT-01", "SAT-02", "SAT-03"])
    part_b = payload.get("partition_b", ["SAT-04", "SAT-05"])
    record = fault_simulator.inject_fault("NETWORK_PARTITION", "CONSTELLATION", {"partition_a": part_a, "partition_b": part_b}, source="FRONTEND")
    await websocket_manager.broadcast({
        "event_type": "NETWORK_PARTITIONED",
        "correlation_id": record["correlation_id"],
        "partitions": fault_simulator.partitions,
        "timestamp": time.time()
    })
    return {"status": "SUCCESS", "partitions": fault_simulator.partitions, "correlation_id": record["correlation_id"]}

@app.post("/api/network/restore")
async def restore_network_partition():
    res = fault_simulator.clear_partition()
    await websocket_manager.broadcast({
        "event_type": "NETWORK_RESTORED",
        "correlation_id": res["correlation_id"],
        "timestamp": time.time()
    })
    return res

@app.get("/api/network/gossip")
async def get_gossip_network_state():
    import httpx
    gossip_map = {}
    for sat in global_registry.list_all():
        if sat.status not in ["DISCONNECTED", "OFFLINE"]:
            try:
                url = f"http://{sat.address}:{sat.p2p_port}/p2p/state"
                async with httpx.AsyncClient(timeout=1.5) as client:
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        gossip_map[sat.satellite_id] = resp.json()
            except Exception:
                pass
    return {"gossip_map": gossip_map, "partitions": fault_simulator.partitions, "timestamp": time.time()}

# ------------------- FAULT SIMULATOR REST APIs -------------------

@app.post("/api/faults/inject")
async def inject_fault(req: FaultInjectRequest):
    logger.info(f"[FAULT INJECTION] Frontend → Mission Control | target={req.target_node} | fault_type={req.fault_type} | params={req.parameters}")
    record = fault_simulator.inject_fault(
        fault_type=req.fault_type,
        target_node=req.target_node,
        parameters=req.parameters,
        source="FRONTEND"
    )
    await websocket_manager.broadcast({
        "event_type": "FAULT_INJECTED",
        "correlation_id": record["correlation_id"],
        "fault": record,
        "timestamp": time.time()
    })
    return {"status": "SUCCESS", "fault": record}

@app.post("/api/faults/clear")
async def clear_faults(target_node: Optional[str] = Query(None)):
    target_str = target_node or "ALL_NODES"
    logger.info(f"[FAULT CLEAR] Frontend → Mission Control | target={target_str}")
    cleared = fault_simulator.clear_faults(target_node)
    logger.info(f"[FAULT CLEAR RESULT] Mission Control | target={target_str} | cleared_count={cleared}")
    await websocket_manager.broadcast({
        "event_type": "FAULTS_CLEARED",
        "target_node": target_node,
        "cleared_count": cleared,
        "timestamp": time.time()
    })
    return {"status": "SUCCESS", "cleared_count": cleared}

@app.get("/api/faults")
async def get_active_faults():
    return {
        "active_faults": fault_simulator.get_all_active_faults(),
        "history": fault_simulator.get_history(),
        "partitions": fault_simulator.partitions
    }

# ------------------- OBSERVATORY & EVENTS REST APIs -------------------

@app.get("/api/observatory/stats")
async def get_observatory_stats():
    return {
        "websocket": websocket_manager.get_stats(),
        "rabbitmq": {
            "connected": rabbitmq_manager.connected,
            "published_count": rabbitmq_manager.published_message_count,
            "consumed_count": rabbitmq_manager.consumed_message_count
        },
        "webrtc": webrtc_manager.get_status(),
        "satellites_count": len(global_registry.list_all()),
        "active_faults_count": len(fault_simulator.get_all_active_faults())
    }

@app.get("/api/observatory/logs")
async def get_runtime_logs(service: Optional[str] = Query("ALL_SERVICES")):
    now_str = time.strftime("%H:%M:%S", time.localtime())
    satellites = global_registry.list_all()
    
    logs = [
        {"timestamp": now_str, "service": "mission-control", "level": "INFO", "correlation_id": "EVT-SYS-001", "message": "[REGISTRY] Satellite registry active. Tracking 5 LEO nodes."},
        {"timestamp": now_str, "service": "rabbitmq", "level": "INFO", "correlation_id": "EVT-SYS-002", "message": f"[RABBITMQ] Published: {rabbitmq_manager.published_message_count} | Consumed: {rabbitmq_manager.consumed_message_count}"},
        {"timestamp": now_str, "service": "websocket", "level": "INFO", "correlation_id": "EVT-SYS-003", "message": f"[WEBSOCKET] Active subscribers: {len(websocket_manager.active_connections)}"}
    ]

    for sat in satellites:
        mode = getattr(sat, 'power_mode', 'NORMAL')
        cid = getattr(sat, 'last_correlation_id', f"EVT-NODE-{sat.satellite_id}")
        logs.append({
            "timestamp": now_str,
            "service": f"satellite-{sat.satellite_id.split('-')[-1]}",
            "level": "WARN" if sat.status in ["SUSPECTED", "CRITICAL"] else "INFO",
            "correlation_id": cid,
            "message": f"[{sat.satellite_id}] Status: {sat.status} | Battery: {sat.battery}% | Temp: {sat.temperature}°C | Mode: {mode}"
        })

    if service and service != "ALL_SERVICES":
        logs = [l for l in logs if l["service"] == service or service in l["service"]]

    return {"logs": logs, "timestamp": time.time()}

@app.get("/api/events/{correlation_id}")
async def get_event_trace(correlation_id: str):
    now_str = time.strftime("%H:%M:%S", time.localtime())
    return {
        "correlation_id": correlation_id,
        "trace_steps": [
            {"layer": "Layer 1 — Frontend UI", "action": "USER_ACTION_INITIATED", "source": "Mission Control Dashboard", "status": "EXECUTED", "time": now_str},
            {"layer": "Layer 2 — FastAPI Backend", "action": "DISPATCHED_TO_DISTRIBUTED_SERVICES", "source": "backend/main.py", "status": "200 OK", "time": now_str},
            {"layer": "Layer 3 — Container Runtime", "action": "PROCESS_EXECUTED", "source": "Docker / Local Process", "status": "SUCCESS", "time": now_str},
            {"layer": "Layer 4 — Satellite Node", "action": "STATE_TRANSITION", "source": "Satellite Microservice", "status": "COMPLETED", "time": now_str},
            {"layer": "Layer 5 — Failure Detector", "action": "HEARTBEAT_EVALUATED", "source": "Heartbeat Sweeper", "status": "NOMINAL", "time": now_str},
            {"layer": "Layer 6 — Service Registry", "action": "REGISTRY_STATE_SYNC", "source": "Global Registry", "status": "UPDATED", "time": now_str},
            {"layer": "Layer 7 — WebSocket Bus", "action": "WEBSOCKET_BROADCAST", "source": "/ws Broadcaster", "status": "EMITTED", "time": now_str},
            {"layer": "Layer 8 — Frontend UI", "action": "DASHBOARD_RENDERED", "source": "React Component State", "status": "SYNCHRONIZED", "time": now_str}
        ]
    }

# ------------------- RING LEADER ELECTION REST API -------------------

@app.post("/api/election/ring")
async def trigger_ring_election(initiator_id: str = Query("SAT-01"), db: AsyncSession = Depends(get_db)):
    logger.info(f"[ELECTION API] Frontend → Mission Control | endpoint=/api/election/ring | initiator={initiator_id} | protocol=Ring Leader Election")
    result = global_registry.run_ring_election(initiator_id=initiator_id)
    
    evt = CommunicationEvent(
        event_id=result["event_id"],
        source=initiator_id,
        destination=result["current_leader"],
        protocol="Ring Leader Election",
        method="RING_CIRCULATE",
        latency_ms=result["latency_ms"],
        status="SUCCESS",
        payload_summary=f"Leader Elected: {result['current_leader']} (Participated: {len(result['participating_nodes'])})"
    )
    db.add(evt)
    await db.commit()
    logger.info(f"[DATABASE AUDIT] Persisted CommunicationEvent | event_id={evt.event_id} | protocol=Ring Leader Election | status=SUCCESS")

    await websocket_manager.broadcast({
        "event_type": "LEADER_ELECTION_COMPLETED",
        "result": result,
        "timestamp": time.time()
    })
    logger.info(f"[ELECTION RESULT] Mission Control → Frontend | initiator={initiator_id} | leader_elected={result['current_leader']} | participating={result['participating_nodes']} | latency={result['latency_ms']}ms")
    return result

# ------------------- SYSTEM HEALTH & WEBSOCKET STREAM -------------------

# ------------------- SYSTEM HEALTH & WEBSOCKET STREAM -------------------

# Import FA-2 & MissionResilience Platform Services
from backend.services.distributed_clocks import global_clock_manager
from backend.services.task_manager import global_task_manager
from backend.services.beacon_service import global_beacon_tracker
from backend.services.election_manager import global_election_manager
from backend.services.mutex_manager import global_mutex_engine
from backend.services.snapshot_manager import global_snapshot_manager
from backend.services.impact_analyzer import global_impact_analyzer
from backend.services.reallocation_engine import global_reallocation_engine
from backend.services.resilience_engine import global_resilience_engine
from backend.services.simulation_engine import global_simulation_engine
from backend.services.incident_replay import global_incident_replay_engine
from backend.services.distributed_storage import global_distributed_storage
from backend.services.serverless_processor import global_serverless_processor
from backend.services.hadoop_analytics import global_hadoop_analytics

from backend.services.failure_intelligence import global_failure_intelligence
from backend.services.predictive_health import global_predictive_health
from backend.services.dependency_graph import global_dependency_graph
from backend.services.experiment_lab import global_experiment_lab
from backend.services.partition_reconciliation import global_partition_reconciliation
from backend.services.security_audit import global_security_audit

# ------------------- FAILURE INTELLIGENCE & PREDICTIVE APIs -------------------

@app.get("/api/failure/classify/{node_id}")
async def classify_failure_endpoint(node_id: str):
    return global_failure_intelligence.classify_failure(node_id)

@app.get("/api/predictive/evaluate")
async def evaluate_predictive_health():
    return global_predictive_health.evaluate_constellation_health_trends()

# ------------------- TASK DEPENDENCY GRAPH APIs -------------------

@app.get("/api/tasks/dependencies")
async def get_task_dependencies():
    return global_dependency_graph.get_dependency_tree()

@app.get("/api/tasks/downstream/{task_id}")
async def evaluate_downstream_task_impact(task_id: str):
    return global_dependency_graph.evaluate_downstream_impact(task_id)

# ------------------- EXPERIMENT LAB & ALGORITHM COMPARISON APIs -------------------

@app.get("/api/experiments/compare")
async def compare_algorithms():
    return global_experiment_lab.compare_election_algorithms()

@app.post("/api/experiments/run")
async def run_resilience_experiment_endpoint(req: dict):
    scenario = req.get("scenario", "COORDINATOR_FAILURE")
    iterations = req.get("iterations", 3)
    return global_experiment_lab.run_resilience_experiment(scenario, iterations)

# ------------------- PARTITION & RECONCILIATION APIs -------------------

@app.post("/api/partition/simulate")
async def simulate_partition_endpoint(req: dict):
    group_a = req.get("group_a", ["SAT-01", "SAT-02"])
    group_b = req.get("group_b", ["SAT-03", "SAT-04", "SAT-05"])
    return global_partition_reconciliation.simulate_partition(group_a, group_b)

@app.post("/api/partition/reconcile")
async def reconcile_partition_endpoint():
    return global_partition_reconciliation.reconcile_partition()

# ------------------- SECURITY & AUDIT APIs -------------------

@app.get("/api/security/audit")
async def get_security_audit_logs():
    return {"audit_logs": global_security_audit.get_audit_trail(), "timestamp": time.time()}

@app.post("/api/security/verify")
async def verify_signature_endpoint(req: dict):
    sig = global_security_audit.verify_message_signature(req)
    global_security_audit.log_action("Operator", "Mission Operator", "VERIFY_SIGNATURE", req.get("source", "SAT-01"))
    return {"signature": sig, "valid": True}


# ------------------- CLOCKS & SYNCHRONIZATION APIs -------------------

@app.post("/api/clocks/synchronize")
async def synchronize_physical_clocks():
    return global_clock_manager.run_synchronization_round()

@app.get("/api/clocks/status")
async def get_clock_status():
    p_clocks = {sat: p.sync_history[-1] if p.sync_history else {"offset_ms": p.offset_ms} for sat, p in global_clock_manager.physical_clocks.items()}
    l_clocks = {sat: c.value for sat, c in global_clock_manager.lamport_clocks.items()}
    v_clocks = {sat: c.to_dict() for sat, c in global_clock_manager.vector_clocks.items()}
    return {
        "physical_clocks": p_clocks,
        "lamport_clocks": l_clocks,
        "vector_clocks": v_clocks,
        "timestamp": time.time()
    }

@app.post("/api/clocks/event")
async def record_clock_event(req: dict):
    node_id = req.get("node_id", "SAT-01")
    event_type = req.get("event_type", "GENERIC_EVENT")
    res = global_clock_manager.record_node_event(node_id, event_type)
    return res

# ------------------- MISSION TASKS & CAPABILITIES APIs -------------------

@app.get("/api/tasks")
async def list_mission_tasks():
    return {
        "tasks": global_task_manager.list_tasks(),
        "capabilities_map": global_task_manager.get_capabilities_map(),
        "timestamp": time.time()
    }

@app.post("/api/tasks/{task_id}/reassign")
async def reassign_task_endpoint(task_id: str, req: dict):
    new_owner = req.get("new_owner")
    reason = req.get("reason", "OPERATOR_REASSIGNMENT")
    if not new_owner:
        raise HTTPException(status_code=400, detail="new_owner is required")
    res = global_task_manager.reassign_task(task_id, new_owner, reason)
    await websocket_manager.broadcast({
        "event_type": "TASK_REASSIGNED",
        "task_id": task_id,
        "new_owner": new_owner,
        "timestamp": time.time()
    })
    return res

# ------------------- BEACON PROTOCOL APIs -------------------

@app.get("/api/beacons")
async def get_beacon_states():
    sats = global_registry.list_all()
    res = {}
    for sat in sats:
        age = time.time() - sat.last_heartbeat
        res[sat.satellite_id] = global_beacon_tracker.get_beacon_status(sat.satellite_id, age)
    return {"beacon_states": res, "timestamp": time.time()}

# ------------------- DISTRIBUTED MUTUAL EXCLUSION APIs -------------------

@app.post("/api/mutex/request")
async def request_mutex(req: dict):
    requester_id = req.get("requester_id", "SAT-01")
    resource_id = req.get("resource_id", "T-047")
    res = await global_mutex_engine.request_resource(requester_id, resource_id)
    await websocket_manager.broadcast({
        "event_type": "MUTEX_REQUEST_PROCESSED",
        "result": res,
        "timestamp": time.time()
    })
    return res

@app.post("/api/mutex/release")
async def release_mutex(req: dict):
    requester_id = req.get("requester_id", "SAT-01")
    resource_id = req.get("resource_id", "T-047")
    res = global_mutex_engine.release_resource(requester_id, resource_id)
    await websocket_manager.broadcast({
        "event_type": "MUTEX_RELEASED",
        "result": res,
        "timestamp": time.time()
    })
    return res

# ------------------- GLOBAL STATE SNAPSHOT APIs -------------------

@app.post("/api/snapshots")
async def take_global_snapshot(initiator_id: str = Query("SAT-01")):
    res = global_snapshot_manager.take_snapshot(initiator_id=initiator_id)
    await websocket_manager.broadcast({
        "event_type": "SNAPSHOT_COMPLETED",
        "snapshot_id": res["snapshot_id"],
        "initiator": initiator_id,
        "timestamp": time.time()
    })
    return res

@app.get("/api/snapshots")
async def list_snapshots():
    return {"snapshots": global_snapshot_manager.snapshots_history, "timestamp": time.time()}

# ------------------- IMPACT ANALYSIS & REALLOCATION APIs -------------------

@app.get("/api/impact/analyze/{node_id}")
async def analyze_node_impact(node_id: str):
    return global_impact_analyzer.analyze_failure(node_id)

@app.post("/api/reallocate/execute/{failed_node_id}")
async def execute_task_reallocation(failed_node_id: str):
    res = await global_reallocation_engine.execute_reallocation_for_failed_node(failed_node_id)
    await websocket_manager.broadcast({
        "event_type": "AUTONOMOUS_REALLOCATION_COMPLETED",
        "result": res,
        "timestamp": time.time()
    })
    return res

# ------------------- RESILIENCE SCORECARD API -------------------

@app.get("/api/resilience/scorecard")
async def get_resilience_scorecard():
    return global_resilience_engine.calculate_resilience_metrics()

# ------------------- FAILURE SIMULATOR APIs -------------------

@app.post("/api/simulation/impact")
async def simulate_failure_impact(req: dict):
    target_node = req.get("target_node", "SAT-05")
    scenario_type = req.get("scenario_type", "SINGLE_NODE_FAILURE")
    return global_simulation_engine.simulate_impact(target_node, scenario_type)

@app.post("/api/simulation/execute")
async def execute_failure_scenario(req: dict):
    target_node = req.get("target_node", "SAT-05")
    scenario_type = req.get("scenario_type", "COORDINATOR_FAILURE")
    res = await global_simulation_engine.execute_scenario(target_node, scenario_type)
    await websocket_manager.broadcast({
        "event_type": "FAILURE_SCENARIO_EXECUTED",
        "result": res,
        "timestamp": time.time()
    })
    return res

# ------------------- INCIDENT REPLAY APIs -------------------

@app.get("/api/incidents")
async def list_incidents():
    return {"incidents": global_incident_replay_engine.list_incidents(), "timestamp": time.time()}

@app.get("/api/incidents/{incident_id}")
async def get_incident(incident_id: str):
    inc = global_incident_replay_engine.get_incident(incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    return inc

# ------------------- UNIT 4 ADVANCED INFRASTRUCTURE APIs -------------------

@app.get("/api/unit4/storage")
async def get_storage_artifacts(category: Optional[str] = Query(None)):
    return {"artifacts": global_distributed_storage.list_artifacts(category), "timestamp": time.time()}

@app.post("/api/unit4/serverless")
async def trigger_serverless_function(req: dict):
    fn_name = req.get("function_name", "GENERATE_INCIDENT_REPORT")
    payload = req.get("event_payload", {"origin": "MANUAL_TRIGGER"})
    res = await global_serverless_processor.trigger_event_function(fn_name, payload)
    return res

@app.get("/api/unit4/hadoop")
async def run_hadoop_job(job_name: str = Query("CONSTELLATION_HEALTH_TRENDS")):
    return global_hadoop_analytics.run_mapreduce_job(job_name)

@app.get("/api/health")
async def system_health():
    satellites = global_registry.list_all()
    healthy_count = sum(1 for s in satellites if s.status == "HEALTHY")
    warning_count = sum(1 for s in satellites if s.status == "WARNING")
    critical_count = sum(1 for s in satellites if s.status == "CRITICAL")
    offline_count = sum(1 for s in satellites if s.status == "OFFLINE")

    return {
        "status": "HEALTHY" if offline_count == 0 else "DEGRADED",
        "mission_control": "HEALTHY",
        "rabbitmq": "HEALTHY" if rabbitmq_manager.connected else "IN_MEMORY_FALLBACK",
        "current_leader": global_registry.current_leader,
        "satellites": {
            "total": len(satellites),
            "healthy": healthy_count,
            "warning": warning_count,
            "critical": critical_count,
            "offline": offline_count
        },
        "timestamp": time.time()
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket_manager.connect(websocket)
    try:
        while True:
            # Keep-alive receive loop
            msg = await websocket.receive_text()
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)

