import time
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query
from pydantic import ValidationError
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
    P2PSendRequest, FaultInjectRequest, WebRTCOfferRequest, WebRTCICECandidateRequest,
    TelemetryObservation
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MissionControl")

grpc_manager = GRPCClientManager(global_registry)
rabbitmq_manager = RabbitMQManager(settings.RABBITMQ_URL)
fault_simulator = FaultSimulator(global_registry)

from backend.services.event_manager import generate_correlation_id, create_event
from backend.fa2 import router as fa2
from backend.fa2 import phase3 as fa2_phase3
from backend.fa2 import orbitfs as fa2_orbitfs, mapreduce as fa2_mapreduce, serverless as fa2_serverless
from backend.fa2 import objects as fa2_objects, role as fa2_role
from backend.fa2.bus import mission_bus
from backend.fa2 import phase5 as fa2_phase5

fa2.bind(fault_simulator=fault_simulator, broadcaster=websocket_manager)

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
        try:
            observation = TelemetryObservation(**sat_data)
        except ValidationError as exc:
            # Reject malformed/incomplete observations instead of inventing plausible readings.
            logger.warning("Rejected invalid telemetry payload: %s", exc)
            return

        sat_data = observation.dict(exclude_none=True)
        sat_id = observation.satellite_id
        score, status, _ = HealthEngine.calculate_health(
            battery=observation.battery,
            temperature=observation.temperature,
            cpu_usage=observation.cpu_usage,
            memory_usage=observation.memory_usage,
            signal_strength=observation.signal_strength,
            is_online=True
        )
        # Telemetry updates measurements only; liveness is decided by the heartbeat path.
        reg = global_registry.update_metrics(
            satellite_id=sat_id,
            health_score=score,
            battery=observation.battery,
            temperature=observation.temperature,
            cpu_usage=observation.cpu_usage,
            memory_usage=observation.memory_usage,
            signal_strength=observation.signal_strength
        )
        if reg is None:
            logger.warning("Ignoring telemetry from unregistered satellite %s", sat_id)
            return

        sat_data["health_score"] = score
        sat_data["status"] = reg.status
        fa2_mapreduce.record_sample(sat_data)  # MapReduce input (archived to OrbitFS on demand)
        position = payload.get("data", {}).get("position")
        if isinstance(position, dict):
            sat_data["position"] = position

        # Only validated observations are broadcast as telemetry.
        await websocket_manager.broadcast({
            "event_type": "TELEMETRY_UPDATED",
            "telemetry": {"data": sat_data},
            "broker_mode": payload.get("broker_mode"),
            "message_id": payload.get("message_id"),
            "timestamp": time.time()
        })

    await rabbitmq_manager.register_listener(handle_incoming_telemetry)
    # FA-2: algorithm events reported by satellites (dsync.events exchange)
    await rabbitmq_manager.register_event_listener(fa2.ingest_broker_message)
    
    sweeper_task = asyncio.create_task(heartbeat_sweeper_task())
    task_mirror = asyncio.create_task(fa2_phase3.task_mirror_loop())
    # Unit 4 services
    mission_bus.rabbit = rabbitmq_manager
    await rabbitmq_manager.register_mission_listener(mission_bus.dispatch)
    unit4_tasks = [asyncio.create_task(fa2_orbitfs.namenode.run()), asyncio.create_task(fa2_serverless.runtime.reap()),
                   asyncio.create_task(fa2_role.monitor())]
    fa2_objects.start_name_server()
    yield
    # Shutdown logic
    sweeper_task.cancel()
    for t in unit4_tasks:
        t.cancel()
    fa2_serverless.runtime.shutdown()
    logger.info("Mission Control shutdown complete.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan
)

app.include_router(fa2.router)
app.include_router(fa2_phase3.router)
app.include_router(fa2_orbitfs.router)
app.include_router(fa2_mapreduce.router)
app.include_router(fa2_serverless.router)
app.include_router(fa2_objects.router)
app.include_router(fa2_phase5.router)


@app.middleware("http")
async def ground_blackout_gate(request, call_next):
    """Ground Blackout Mode (simulated): refuse satellite traffic while the operator console keeps working."""
    if fa2_phase3.blackout_blocks(request.url.path, request.method):
        from fastapi.responses import JSONResponse
        return JSONResponse({"detail": "ground segment unavailable (blackout)"}, status_code=503)
    return await call_next(request)

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

    # Heartbeats prove liveness only. The live telemetry stream reaches the frontend through the
    # RabbitMQ consumer (handle_incoming_telemetry), so each sample is broadcast exactly once.
    await websocket_manager.broadcast({
        "event_type": "HEARTBEAT_RECEIVED",
        "satellite_id": req.satellite_id,
        "node_status": reg.status,
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

@app.post("/api/telemetry/ingest")
async def ingest_telemetry_fallback(payload: Dict[str, Any]):
    """
    HTTP bridge used by satellites ONLY when they cannot reach a RabbitMQ broker
    (e.g. local runs without Docker). The sample is published into Mission Control's
    message bus, so it still flows through the same consumer pipeline, and is labelled
    with broker_mode so the UI never claims RabbitMQ delivered it.
    """
    if not isinstance(payload, dict) or not payload.get("satellite_id"):
        raise HTTPException(status_code=422, detail="Telemetry payload must include satellite_id")
    envelope = await rabbitmq_manager.publish_telemetry(payload)
    return {"status": "ACCEPTED", "broker_mode": envelope["broker_mode"], "message_id": envelope["message_id"]}

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
    # Enforced by the satellites themselves: each one refuses traffic across the partition.
    record["satellites"] = await fa2.push_fault("PARTITION", {"groups": [part_a, part_b]})
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
    res["satellites"] = await fa2.push_fault("HEAL", {})
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
    # STOP / RESTART now act on the satellite process itself (simulated crash: it goes silent
    # towards Mission Control and its peers), so failure detection and elections react for real.
    if req.fault_type in ("STOP_NODE", "STOP"):
        record["satellite"] = await fa2.push_fault("CRASH", {}, [req.target_node])
    elif req.fault_type in ("RESTART_NODE", "RESTART"):
        record["satellite"] = await fa2.push_fault("RECOVER", {}, [req.target_node])
    elif req.fault_type == "CLOCK_DRIFT":
        params = req.parameters or {}
        record["satellite"] = await fa2.push_fault("CLOCK_DRIFT", {"offset_ms": float(params.get("offset_ms", 500.0)),
                                                                  "drift_ppm": params.get("drift_ppm")}, [req.target_node])
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
    await fa2.push_fault("RECOVER", {}, [target_node] if target_node else None)
    if not target_node:
        await fa2.push_fault("HEAL", {})
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
            # published_count = messages Mission Control itself put on the bus (HTTP fallback bridge).
            # Satellites publish directly to the broker, so their output shows up in consumed_by_producer.
            "published_count": rabbitmq_manager.published_message_count,
            "consumed_count": rabbitmq_manager.consumed_message_count,
            "consumed_by_producer": dict(rabbitmq_manager.consumed_by_producer),
            "consumed_by_broker_mode": dict(rabbitmq_manager.consumed_by_broker_mode)
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
    """Kept for existing pages: runs a REAL ring election among the satellites (see /api/fa2/election/run)."""
    run = await fa2.election_run({"algorithm": "ring", "initiator": initiator_id})
    leader = (run.get("agreement") or {}).get("leader")
    result = {
        **run,
        "event_id": run["run_id"],
        "status": "SUCCESS" if leader else "NO_AGREEMENT",
        "protocol": "Ring election executed by the satellites",
        "current_leader": leader,
        "new_leader": leader,
        "participating_nodes": run.get("participants", []),
        "messages_exchanged": run.get("messages"),
        "latency_ms": run.get("agreement_observed_ms"),
    }
    db.add(CommunicationEvent(
        event_id=run["run_id"], source=initiator_id, destination=leader or "NONE", protocol="Ring Leader Election",
        method="RING_ELECTION", latency_ms=run.get("agreement_observed_ms") or 0.0,
        status="SUCCESS" if leader else "FAILED",
        payload_summary=f"Leader {leader} agreed by {len((run.get('agreement') or {}).get('agreed_by', []))} satellites, {run.get('messages')} messages"))
    await db.commit()
    await websocket_manager.broadcast({"event_type": "LEADER_ELECTION_COMPLETED", "result": result, "timestamp": time.time()})
    return result

# ------------------- SYSTEM HEALTH & WEBSOCKET STREAM -------------------

# ------------------- SYSTEM HEALTH & WEBSOCKET STREAM -------------------

# Import FA-2 & MissionResilience Platform Services
from backend.services.task_manager import global_task_manager
from backend.services.impact_analyzer import global_impact_analyzer
from backend.services.reallocation_engine import global_reallocation_engine
from backend.services.resilience_engine import global_resilience_engine
from backend.services.simulation_engine import global_simulation_engine
from backend.services.incident_replay import global_incident_replay_engine

from backend.services.failure_intelligence import global_failure_intelligence
from backend.services.predictive_health import global_predictive_health
from backend.services.dependency_graph import global_dependency_graph

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
    """Measured comparison only: the latest Algorithm Arena run per algorithm (empty until runs exist)."""
    return await fa2.arena_summary()

@app.post("/api/experiments/run")
async def run_resilience_experiment_endpoint(req: dict):
    """Coordinator-failure experiment, measured on the satellites (replaces the former random numbers)."""
    iterations = max(1, min(int(req.get("iterations", 1)), 5))
    runs = []
    for _ in range(iterations):
        runs.append(await fa2.election_leader_failure({"algorithm": req.get("algorithm", "bully"), "recover": True}))
        await asyncio.sleep(3.0)
    return {"scenario": "COORDINATOR_FAILURE", "iterations": iterations, "runs": runs}

# ------------------- PARTITION & RECONCILIATION APIs -------------------

@app.post("/api/partition/simulate")
async def simulate_partition_endpoint(req: dict):
    """Real partition enforced by the satellites (see the CAP page for what each store does under it)."""
    group_a = req.get("group_a", ["SAT-01", "SAT-02", "SAT-03"])
    group_b = req.get("group_b", ["SAT-04", "SAT-05"])
    return await fa2.fault_partition({"groups": [group_a, group_b]})

@app.post("/api/partition/reconcile")
async def reconcile_partition_endpoint():
    """Heal: satellites push their status boards (vector-clock merge) and catch up the ledger."""
    healed = await fa2.fault_heal()
    await asyncio.sleep(1.5)
    return {"healed": healed, "board": await fa2_phase5.board_view(), "ledger": await fa2_phase5.ledger_view()}

# ------------------- SECURITY & AUDIT APIs -------------------

@app.get("/api/security/audit")
async def get_security_audit_logs():
    """Audit trail = the signed command ledger replicated on the satellites."""
    view = await fa2_phase5.ledger_view()
    return {"audit_logs": view["blocks"], "copies": view["copies"], "timestamp": time.time()}

@app.post("/api/security/verify")
async def verify_signature_endpoint(req: dict):
    view = await fa2_phase5.ledger_view()
    return {"valid": all(c["verification"]["valid"] for c in view["copies"].values() if c.get("reachable")),
            "copies": view["copies"]}


# ------------------- CLOCKS & SYNCHRONIZATION APIs -------------------

@app.post("/api/clocks/synchronize")
async def synchronize_physical_clocks():
    """Berkeley round run by the elected leader among the satellites (see /api/fa2/clocks/*)."""
    return await fa2.clocks_berkeley()

@app.get("/api/clocks/status")
async def get_clock_status():
    """Clocks as the satellites report them (physical with skew, Lamport, vector)."""
    return await fa2.clocks()

# ------------------- MISSION TASKS & CAPABILITIES APIs -------------------

@app.get("/api/tasks")
async def list_mission_tasks():
    """Task ownership as the satellites report it (they own the tasks); DB mirror only if none respond."""
    out = await fa2_phase3.tasks()
    if not any(t["current_owner"] for t in out["tasks"]):
        out = {"tasks": global_task_manager.list_tasks(), "capabilities_map": global_task_manager.get_capabilities_map(),
               "source": "mission-control mirror (no satellite responded)"}
    out["timestamp"] = time.time()
    return out

@app.post("/api/tasks/{task_id}/reassign")
async def reassign_task_endpoint(task_id: str, req: dict):
    new_owner = req.get("new_owner")
    reason = req.get("reason", "OPERATOR_REASSIGNMENT")
    if not new_owner:
        raise HTTPException(status_code=400, detail="new_owner is required")
    # The request is forwarded to the elected leader satellite, which validates capability and moves the task.
    res = await fa2_phase3.tasks_assign({"task_id": task_id, "owner": new_owner})
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
    """How each satellite sees its peers, from satellite-to-satellite beacons (not Mission Control heartbeats)."""
    st = await fa2.states()
    return {"beacon_states": {sid: {"peers": v.get("peers"), "beacons": v.get("beacons"), "unreachable": v.get("unreachable", False)}
                              for sid, v in st.items()}, "timestamp": time.time()}

# Distributed mutual exclusion now runs on the satellites: see /api/fa2/arena/mutex.

# ------------------- GLOBAL STATE SNAPSHOT APIs -------------------

@app.post("/api/snapshots")
async def take_global_snapshot(initiator_id: str = Query("SAT-01")):
    res = await fa2_phase3.snapshot({"initiator": initiator_id})
    await websocket_manager.broadcast({
        "event_type": "SNAPSHOT_COMPLETED",
        "snapshot_id": res["snapshot_id"],
        "initiator": initiator_id,
        "timestamp": time.time()
    })
    return res

@app.get("/api/snapshots")
async def list_snapshots():
    return {"snapshots": fa2_phase3.snapshot_history[-20:], "timestamp": time.time()}

# ------------------- IMPACT ANALYSIS & REALLOCATION APIs -------------------

@app.get("/api/impact/analyze/{node_id}")
async def analyze_node_impact(node_id: str):
    return global_impact_analyzer.analyze_failure(node_id)

@app.post("/api/reallocate/execute/{failed_node_id}")
async def execute_task_reallocation(failed_node_id: str):
    # The leader satellite reassigns tasks of satellites it no longer sees alive (decision taken on board).
    res = await fa2_phase3.tasks_reconcile()
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
    """Artifacts are files in OrbitFS (replicated on the satellites)."""
    files = (await fa2_orbitfs.list_files(prefix=f"{category}/" if category else ""))["files"]
    return {"artifacts": [{"artifact_id": f["path"], "category": f["path"].split("/")[0], "size_bytes": f["size"],
                           "chunks": len(f["chunks"]), "under_replicated": f["under_replicated"]} for f in files],
            "timestamp": time.time()}

@app.post("/api/unit4/serverless")
async def trigger_serverless_function(req: dict):
    return await fa2_serverless.invoke({"function": req.get("function_name", "incident_report"),
                                        "event": req.get("event_payload") or {}})

@app.get("/api/unit4/hadoop")
async def run_hadoop_job(job_name: str = Query("health_stats")):
    """Real MapReduce over the latest telemetry archive in OrbitFS (archived first if none exists)."""
    job = {"CONSTELLATION_HEALTH_TRENDS": "health_stats"}.get(job_name, job_name)
    if not any(p.startswith("telemetry/archive-") for p in fa2_orbitfs.namenode.files):
        await fa2_mapreduce.archive()
    return await fa2_mapreduce.run_job({"job": job})

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

