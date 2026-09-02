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

# Background sweep loop to detect heartbeat timeout / satellite failures
async def heartbeat_sweeper_task():
    while True:
        try:
            await asyncio.sleep(settings.SWEEP_INTERVAL_SECONDS)
            failed_nodes = global_registry.sweep_failures()
            if failed_nodes:
                for fn in failed_nodes:
                    logger.warning(f"[FAILURE DETECTOR] Satellite {fn} heartbeat timed out! Status marked OFFLINE.")
                    await websocket_manager.broadcast({
                        "event_type": "NODE_DISCONNECTED",
                        "satellite_id": fn,
                        "status": "OFFLINE",
                        "timestamp": time.time(),
                        "message": f"Satellite {fn} heartbeat lost (> {settings.HEARTBEAT_TIMEOUT_SECONDS}s)."
                    })
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
    logger.info(f"Registered Satellite {req.satellite_id} at {req.address}:{req.grpc_port}")
    await websocket_manager.broadcast({
        "event_type": "NODE_REGISTERED",
        "satellite_id": req.satellite_id,
        "data": global_registry.to_dict_list(),
        "timestamp": time.time()
    })
    return {"status": "SUCCESS", "registration": reg}

@app.post("/api/satellites/heartbeat")
async def receive_heartbeat(req: HeartbeatRequest):
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

    await websocket_manager.broadcast({
        "event_type": "RPC_EXECUTED",
        "result": res,
        "timestamp": time.time()
    })
    return res

@app.post("/api/p2p/send")
async def send_p2p_message(req: P2PSendRequest, db: AsyncSession = Depends(get_db)):
    start_time = time.time()
    source_reg = global_registry.lookup(req.source_satellite_id)
    dest_reg = global_registry.lookup(req.destination_satellite_id)

    if not source_reg or not dest_reg:
        raise HTTPException(status_code=404, detail="Source or Destination Satellite not found in registry")

    if source_reg.status == "OFFLINE" or dest_reg.status == "OFFLINE":
        return {
            "success": False,
            "error": "P2P connection failed: One or both satellites are OFFLINE",
            "latency_ms": round((time.time() - start_time) * 1000, 2)
        }

    # Simulate network latency fault if configured
    faults = fault_simulator.get_node_faults(req.source_satellite_id)
    for f in faults:
        if f["fault_type"] == "HIGH_LATENCY":
            await asyncio.sleep(f["parameters"].get("latency_ms", 500) / 1000.0)

    # Instruct Source Satellite to perform direct P2P transmission to Destination Satellite
    import httpx
    source_trigger_url = f"http://{source_reg.address}:{source_reg.p2p_port}/p2p/send_to_peer"
    trigger_payload = {
        "message_id": f"p2p-{int(time.time()*1000)}",
        "destination_satellite_id": req.destination_satellite_id,
        "destination_address": dest_reg.address,
        "destination_p2p_port": dest_reg.p2p_port,
        "message_type": req.message_type,
        "payload": req.payload
    }

    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.post(source_trigger_url, json=trigger_payload)
            latency = round((time.time() - start_time) * 1000, 2)
            
            if resp.status_code == 200:
                sat_res = resp.json()
                p2p_result = {
                    "success": sat_res.get("success", True),
                    "message_id": trigger_payload["message_id"],
                    "source": req.source_satellite_id,
                    "destination": req.destination_satellite_id,
                    "direct_link": sat_res.get("direct_link"),
                    "latency_ms": sat_res.get("latency_ms", latency),
                    "relay_status": "DIRECT_SATELLITE_TO_SATELLITE (No Mission Control Relay)",
                    "response": sat_res.get("ack_response")
                }
            else:
                p2p_result = {
                    "success": False,
                    "error": f"Source satellite returned status {resp.status_code}",
                    "latency_ms": latency
                }
    except Exception as ex:
        latency = round((time.time() - start_time) * 1000, 2)
        p2p_result = {
            "success": False,
            "error": f"Direct P2P execution error: {ex}",
            "source": req.source_satellite_id,
            "destination": req.destination_satellite_id,
            "latency_ms": latency
        }

    # Persist P2P event log
    evt = CommunicationEvent(
        event_id=trigger_payload["message_id"],
        source=req.source_satellite_id,
        destination=req.destination_satellite_id,
        protocol="P2P Messaging (Direct Link)",
        method=req.message_type,
        latency_ms=p2p_result["latency_ms"],
        status="SUCCESS" if p2p_result["success"] else "FAILED",
        payload_summary=req.payload
    )
    db.add(evt)
    await db.commit()

    await websocket_manager.broadcast({
        "event_type": "P2P_MESSAGE_DELIVERED",
        "result": p2p_result,
        "timestamp": time.time()
    })
    return p2p_result

@app.post("/api/webrtc/offer")
async def handle_webrtc_offer(req: WebRTCOfferRequest):
    res = webrtc_manager.process_offer(offer_sdp=req.offer_sdp, peer=req.peer)
    await websocket_manager.broadcast({
        "event_type": "WEBRTC_CONNECTED",
        "session": res,
        "timestamp": time.time()
    })
    return res

@app.post("/api/webrtc/ice-candidate")
async def add_ice_candidate(req: WebRTCICECandidateRequest):
    ok = webrtc_manager.add_ice_candidate(req.session_id, req.candidate)
    return {"success": ok}

@app.get("/api/webrtc/status")
async def get_webrtc_status():
    return webrtc_manager.get_status()

# ------------------- FAULT SIMULATOR REST APIs -------------------

@app.post("/api/faults/inject")
async def inject_fault(req: FaultInjectRequest):
    record = fault_simulator.inject_fault(
        fault_type=req.fault_type,
        target_node=req.target_node,
        parameters=req.parameters
    )
    await websocket_manager.broadcast({
        "event_type": "FAULT_INJECTED",
        "fault": record,
        "timestamp": time.time()
    })
    return {"status": "SUCCESS", "fault": record}

@app.post("/api/faults/clear")
async def clear_faults(target_node: Optional[str] = Query(None)):
    cleared = fault_simulator.clear_faults(target_node)
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
        "history": fault_simulator.get_history()
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

# ------------------- SYSTEM HEALTH & WEBSOCKET STREAM -------------------

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
