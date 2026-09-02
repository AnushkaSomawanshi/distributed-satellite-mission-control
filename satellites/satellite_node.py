import sys
import os
import time
import math
import json
import random
import argparse
import asyncio
import logging
from concurrent import futures

import httpx
from fastapi import FastAPI, Request
import uvicorn

# Ensure workspace root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    import grpc
    import proto.satellite_pb2 as pb2
    import proto.satellite_pb2_grpc as pb2_grpc
    HAS_GRPC = True
except Exception:
    HAS_GRPC = False

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s")
logger = logging.getLogger("SatelliteNode")

class SatelliteNode:
    def __init__(self, satellite_id: str, grpc_port: int, p2p_port: int, registry_url: str):
        self.satellite_id = satellite_id
        self.node_id = f"NODE-{satellite_id}-{random.randint(1000, 9999)}"
        self.hostname = f"{satellite_id.lower()}.orbital.local"
        self.address = os.getenv("SAT_ADDRESS", os.getenv("HOSTNAME", "127.0.0.1"))
        self.grpc_port = grpc_port
        self.p2p_port = p2p_port
        self.registry_url = registry_url.rstrip("/")
        
        # Telemetry & Orbital State
        self.start_time = time.time()
        self.status = "HEALTHY"
        self.battery = 98.5
        self.temperature = 24.0
        self.cpu_usage = 18.2
        self.memory_usage = 32.4
        self.signal_strength = 96.0
        self.orbit_angle = random.uniform(0, 2 * math.pi)
        self.altitude_km = 550.0 + random.uniform(-10, 10)
        self.velocity_kms = 7.66
        self.sequence_number = 0
        
        # Fault hooks
        self.latency_injection_ms = 0.0
        self.packet_loss_pct = 0.0

    def calculate_health_score(self) -> float:
        b_score = min(25.0, 25.0 * (self.battery / 70.0))
        t_score = 25.0 if 15 <= self.temperature <= 45 else 10.0
        c_score = 20.0 if self.cpu_usage <= 70 else 5.0
        m_score = 15.0 if self.memory_usage <= 80 else 5.0
        s_score = min(15.0, 15.0 * (self.signal_strength / 60.0))
        return round(max(0.0, min(100.0, b_score + t_score + c_score + m_score + s_score)), 2)

    def step_telemetry(self):
        self.sequence_number += 1
        self.orbit_angle += 0.05
        if self.orbit_angle > 2 * math.pi:
            self.orbit_angle -= 2 * math.pi

        self.latitude = round(53.0 * math.sin(self.orbit_angle), 4)
        self.longitude = round(((math.degrees(self.orbit_angle * 0.8) + 180) % 360) - 180, 4)

        in_eclipse = math.cos(self.orbit_angle) < -0.3
        if in_eclipse:
            self.battery = max(35.0, self.battery - 0.25 + random.uniform(-0.05, 0.05))
            self.temperature = max(12.0, self.temperature - 0.3 + random.uniform(-0.1, 0.1))
        else:
            self.battery = min(100.0, self.battery + 0.35 + random.uniform(-0.05, 0.05))
            self.temperature = min(42.0, self.temperature + 0.25 + random.uniform(-0.1, 0.1))

        self.cpu_usage = round(max(5.0, min(99.0, 18.0 + 10.0 * math.sin(self.orbit_angle * 3) + random.uniform(-3, 3))), 1)
        self.memory_usage = round(max(10.0, min(95.0, 32.0 + 5.0 * math.cos(self.orbit_angle * 2) + random.uniform(-1, 1))), 1)
        self.signal_strength = round(max(50.0, min(100.0, 94.0 + 5.0 * math.sin(self.orbit_angle * 5) + random.uniform(-2, 2))), 1)

    def get_telemetry_dict(self):
        return {
            "satellite_id": self.satellite_id,
            "node_id": self.node_id,
            "sequence_number": self.sequence_number,
            "position": {
                "latitude": self.latitude,
                "longitude": self.longitude,
                "altitude_km": round(self.altitude_km, 2),
                "velocity_kms": self.velocity_kms
            },
            "battery": round(self.battery, 2),
            "temperature": round(self.temperature, 2),
            "cpu_usage": round(self.cpu_usage, 2),
            "memory_usage": round(self.memory_usage, 2),
            "signal_strength": round(self.signal_strength, 2),
            "health_score": self.calculate_health_score(),
            "status": self.status,
            "uptime_seconds": int(time.time() - self.start_time),
            "timestamp": time.time()
        }

    async def register_with_mission_control(self) -> bool:
        url = f"{self.registry_url}/api/satellites/register"
        payload = {
            "satellite_id": self.satellite_id,
            "node_id": self.node_id,
            "hostname": self.hostname,
            "address": self.address,
            "grpc_port": self.grpc_port,
            "p2p_port": self.p2p_port,
            "capabilities": ["TELEMETRY", "gRPC", "P2P", "RABBITMQ", "WEBRTC"]
        }
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    logger.info(f"Dynamic Registration SUCCESS: {self.satellite_id} registered with Mission Control.")
                    self.is_registered = True
                    return True
                else:
                    logger.warning(f"Registration returned status {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.warning(f"Could not connect to Mission Control Registry at {url}: {e}. Retrying in background.")
        return False

    async def send_heartbeat(self):
        url = f"{self.registry_url}/api/satellites/heartbeat"
        payload = {
            "satellite_id": self.satellite_id,
            "node_id": self.node_id,
            "address": self.address,
            "grpc_port": self.grpc_port,
            "p2p_port": self.p2p_port,
            "battery": round(self.battery, 2),
            "temperature": round(self.temperature, 2),
            "cpu_usage": round(self.cpu_usage, 2),
            "memory_usage": round(self.memory_usage, 2),
            "signal_strength": round(self.signal_strength, 2)
        }
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code != 200:
                    await self.register_with_mission_control()
        except Exception:
            pass

    async def start_autonomous_loop(self):
        # Guarantee registration retry until Mission Control acknowledges registration
        while not getattr(self, 'is_registered', False):
            success = await self.register_with_mission_control()
            if not success:
                await asyncio.sleep(2.0)

        while True:
            try:
                self.step_telemetry()
                await self.send_heartbeat()
                await asyncio.sleep(2.0)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in autonomous telemetry loop: {e}")
                await asyncio.sleep(2.0)

# gRPC Async Servicer Implementation
if HAS_GRPC:
    class SatelliteGrpcServicer(pb2_grpc.SatelliteServiceServicer):
        def __init__(self, node: SatelliteNode):
            self.node = node

        async def GetHealth(self, request, context):
            return pb2.HealthResponse(
                satellite_id=self.node.satellite_id,
                status=self.node.status,
                health_score=self.node.calculate_health_score(),
                battery_level=round(self.node.battery, 2),
                temperature=round(self.node.temperature, 2),
                cpu_usage=round(self.node.cpu_usage, 2),
                memory_usage=round(self.node.memory_usage, 2),
                signal_strength=round(self.node.signal_strength, 2),
                uptime_seconds=int(time.time() - self.node.start_time),
                timestamp=int(time.time())
            )

        async def Ping(self, request, context):
            return pb2.PingResponse(
                satellite_id=self.node.satellite_id,
                status="PONG",
                echo_timestamp=request.timestamp,
                response_timestamp=int(time.time() * 1000)
            )

        async def GetSatelliteInfo(self, request, context):
            return pb2.InfoResponse(
                satellite_id=self.node.satellite_id,
                node_id=self.node.node_id,
                hostname=self.node.hostname,
                grpc_port=self.node.grpc_port,
                p2p_port=self.node.p2p_port,
                capabilities=["TELEMETRY", "gRPC", "P2P", "RABBITMQ", "WEBRTC"],
                status=self.node.status,
                start_time=int(self.node.start_time)
            )

        async def SendP2PMessage(self, request, context):
            start_t = time.time()
            logger.info(f"[{self.node.satellite_id} gRPC P2P] Received message directly from {request.source_satellite_id}: {request.payload}")
            return pb2.P2PResponse(
                message_id=request.message_id,
                receiver_satellite_id=self.node.satellite_id,
                acknowledged=True,
                status_message=f"gRPC P2P message delivered directly to {self.node.satellite_id}",
                received_timestamp=int(time.time()),
                processing_delay_ms=round((time.time() - start_t) * 1000, 2)
            )

# FastP2P HTTP Direct Satellite-to-Satellite Service
def create_satellite_p2p_app(node: SatelliteNode) -> FastAPI:
    app = FastAPI(title=f"{node.satellite_id} P2P Node")

    @app.post("/p2p/receive")
    async def receive_p2p(req: dict):
        start_t = time.time()
        logger.info(f"[{node.satellite_id} DIRECT P2P LINK] Received direct message from {req.get('source')}: {req.get('payload')}")
        return {
            "receiver_satellite_id": node.satellite_id,
            "acknowledged": True,
            "status_message": f"Direct P2P message received by {node.satellite_id}",
            "processing_delay_ms": round((time.time() - start_t) * 1000, 2),
            "received_timestamp": time.time()
        }

    @app.post("/p2p/send_to_peer")
    async def send_to_peer(req: dict):
        """
        Executes a DIRECT P2P network transmission from THIS satellite to a peer satellite.
        Mission Control never relays this message. The network request travels directly
        from Source Satellite to Destination Satellite.
        """
        start_t = time.time()
        dest_address = req.get("destination_address", "127.0.0.1")
        dest_p2p_port = req.get("destination_p2p_port")
        payload = req.get("payload", "")
        message_id = req.get("message_id", f"p2p-{int(time.time()*1000)}")

        target_url = f"http://{dest_address}:{dest_p2p_port}/p2p/receive"
        p2p_body = {
            "message_id": message_id,
            "source": node.satellite_id,
            "destination": req.get("destination_satellite_id"),
            "message_type": req.get("message_type", "DIRECT_P2P"),
            "payload": payload,
            "timestamp": time.time()
        }

        logger.info(f"[{node.satellite_id} DIRECT P2P OUTGOING] Sending direct P2P packet to {req.get('destination_satellite_id')} at {target_url}")

        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                resp = await client.post(target_url, json=p2p_body)
                latency = round((time.time() - start_t) * 1000, 2)
                if resp.status_code == 200:
                    logger.info(f"[{node.satellite_id} DIRECT P2P ACK] Direct ACK from {req.get('destination_satellite_id')} in {latency}ms")
                    return {
                        "success": True,
                        "initiator": node.satellite_id,
                        "target": req.get("destination_satellite_id"),
                        "direct_link": f"{node.satellite_id} ({node.address}:{node.p2p_port}) -> {req.get('destination_satellite_id')} ({dest_address}:{dest_p2p_port})",
                        "latency_ms": latency,
                        "ack_response": resp.json()
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Peer returned status {resp.status_code}",
                        "latency_ms": latency
                    }
        except Exception as e:
            return {
                "success": False,
                "error": f"Direct link error: {e}",
                "latency_ms": round((time.time() - start_t) * 1000, 2)
            }

    @app.post("/rpc/GetHealth")
    async def rpc_get_health(req: dict = None):
        return {
            "satellite_id": node.satellite_id,
            "status": node.status,
            "health_score": node.calculate_health_score(),
            "battery_level": round(node.battery, 2),
            "temperature": round(node.temperature, 2),
            "cpu_usage": round(node.cpu_usage, 2),
            "memory_usage": round(node.memory_usage, 2),
            "signal_strength": round(node.signal_strength, 2),
            "uptime_seconds": int(time.time() - node.start_time)
        }

    @app.post("/rpc/Ping")
    async def rpc_ping(req: dict = None):
        return {
            "status": "PONG",
            "echo_timestamp": req.get("timestamp") if req else 0,
            "response_timestamp": int(time.time() * 1000)
        }

    @app.post("/rpc/GetSatelliteInfo")
    async def rpc_get_info(req: dict = None):
        return {
            "satellite_id": node.satellite_id,
            "node_id": node.node_id,
            "hostname": node.hostname,
            "grpc_port": node.grpc_port,
            "p2p_port": node.p2p_port,
            "capabilities": ["TELEMETRY", "gRPC", "P2P", "RABBITMQ", "WEBRTC"],
            "status": node.status
        }

    return app

async def start_grpc_server(node: SatelliteNode):
    if not HAS_GRPC:
        return
    server = grpc.aio.server()
    pb2_grpc.add_SatelliteServiceServicer_to_server(SatelliteGrpcServicer(node), server)
    listen_addr = f"0.0.0.0:{node.grpc_port}"
    server.add_insecure_port(listen_addr)
    await server.start()
    logger.info(f"gRPC Server for {node.satellite_id} started on port {node.grpc_port}")
    await server.wait_for_termination()

async def run_satellite(sat_id: str, grpc_port: int, p2p_port: int, registry_url: str):
    node = SatelliteNode(sat_id, grpc_port, p2p_port, registry_url)
    
    # Start Autonomous Telemetry Loop
    asyncio.create_task(node.start_autonomous_loop())

    # Start native async gRPC Server if available
    if HAS_GRPC:
        asyncio.create_task(start_grpc_server(node))

    # Start HTTP P2P Direct Server & Bridge
    p2p_app = create_satellite_p2p_app(node)
    config = uvicorn.Config(p2p_app, host="0.0.0.0", port=p2p_port, log_level="warning")
    server = uvicorn.Server(config)
    
    logger.info(f"Satellite {sat_id} Node active. gRPC Port: {grpc_port} | P2P Direct Endpoint: http://127.0.0.1:{p2p_port}")
    await server.serve()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Distributed Satellite Node Process")
    parser.add_argument("--id", type=str, default="SAT-01", help="Satellite ID (e.g. SAT-01)")
    parser.add_argument("--grpc-port", type=int, default=5001, help="gRPC Port")
    parser.add_argument("--p2p-port", type=int, default=6001, help="P2P HTTP Port")
    parser.add_argument("--registry", type=str, default="http://localhost:8000", help="Mission Control Registry URL")
    
    args = parser.parse_args()
    asyncio.run(run_satellite(args.id, args.grpc_port, args.p2p_port, args.registry))
