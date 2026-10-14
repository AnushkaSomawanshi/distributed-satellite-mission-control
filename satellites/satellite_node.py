import sys
import os
import time
import math
import json
import random
import argparse
import asyncio
import logging
import uuid
from collections import deque
from concurrent import futures
from typing import Any, Dict, List, Optional

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

from satellites.telemetry_publisher import TelemetryPublisher
from satellites.dsync import DsyncNode, create_dsync_router
from satellites.dsync.datanode import create_datanode_router
from satellites.dsync.remote_objects import start_pyro

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s")
logger = logging.getLogger("SatelliteNode")

# Gossip / peer-discovery tuning (overridable through environment variables)
GOSSIP_INTERVAL_SECONDS = float(os.getenv("GOSSIP_INTERVAL_SECONDS", "6.0"))
GOSSIP_MAX_HOPS = int(os.getenv("GOSSIP_MAX_HOPS", "3"))
PEER_REFRESH_SECONDS = float(os.getenv("PEER_REFRESH_SECONDS", "10.0"))

class SatelliteNode:
    def __init__(self, satellite_id: str, grpc_port: int, p2p_port: int, registry_url: str,
                 rabbitmq_url: Optional[str] = None):
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
        
        # Fault hooks & Autonomy
        self.latency_injection_ms = 0.0
        self.packet_loss_pct = 0.0
        self.power_mode = "NORMAL" # NORMAL, POWER_SAVING, THERMAL_PROTECTION
        self.telemetry_interval = 2.0
        self.neighbor_health_map: Dict[str, Dict[str, Any]] = {}
        self.gossip_history: List[Dict[str, Any]] = []

        # Peer directory learned from the registry: {satellite_id: {"address", "p2p_port", "status"}}.
        # It is cached, so gossip keeps working from the last known view if Mission Control is unreachable.
        self.peers: Dict[str, Dict[str, Any]] = {}
        self.peers_refreshed_at: Optional[float] = None
        self.gossip_stats = {"originated": 0, "forwarded": 0, "received": 0, "send_failures": 0}

        # Message-oriented telemetry (RabbitMQ, with a labelled HTTP fallback)
        self.telemetry_publisher = TelemetryPublisher(satellite_id, rabbitmq_url, self.registry_url)

        # FA-2: clocks, beacons, election, clock sync and mutual exclusion run HERE, between satellites.
        self.dsync = DsyncNode(satellite_id, info=self._dsync_info,
                               event_sink=self._ship_events,
                               election_algorithm=os.getenv("ELECTION_ALGORITHM", "bully"))

        # Ground Blackout Mode: consecutive failed heartbeats -> ground lost; telemetry is buffered
        self.heartbeat_failures = 0
        self.telemetry_buffer: deque = deque(maxlen=2000)

    async def _ship_events(self, events: list) -> bool:
        # While the ground segment is lost, events stay in the satellite's own buffer (nothing is dropped).
        if not self.dsync.ground_ok:
            return False
        return await self.telemetry_publisher.publish_events(events)

    def _ground_result(self, ok: bool) -> None:
        if ok:
            self.heartbeat_failures = 0
            if not self.dsync.ground_ok:
                self.dsync.set_ground(True)
        else:
            self.heartbeat_failures += 1
            if self.heartbeat_failures >= 3 and self.dsync.ground_ok:
                self.dsync.set_ground(False)

    async def _publish_telemetry(self) -> None:
        sample = self.get_telemetry_dict()
        if not self.dsync.ground_ok:
            sample["buffered_during_blackout"] = True
            self.telemetry_buffer.append(sample)
            return
        while self.telemetry_buffer:  # ground is back: deliver what was recorded during the blackout first
            if await self.telemetry_publisher.publish(self.telemetry_buffer[0]) == "FAILED":
                break
            self.telemetry_buffer.popleft()
        await self.telemetry_publisher.publish(sample)

    def _dsync_info(self) -> Dict[str, Any]:
        return {
            "address": self.address,
            "p2p_port": self.p2p_port,
            "health": self.calculate_health_score(),
            "battery": round(self.battery, 2),
            "signal": round(self.signal_strength, 2),
            "position": {"latitude": getattr(self, "latitude", None), "longitude": getattr(self, "longitude", None)},
        }

    @property
    def silent(self) -> bool:
        """Simulated crash (STOP fault): no heartbeats, telemetry, gossip or algorithm messages."""
        return self.dsync.transport.silent

    async def fetch_server_time(self) -> float:
        """Cristian's algorithm: Mission Control acts as the time server."""
        # One persistent connection: a fresh connection per request adds set-up delay to the outbound
        # half only, which breaks Cristian's symmetric-delay assumption.
        if getattr(self, "_time_client", None) is None:
            self._time_client = httpx.AsyncClient(timeout=3.0)
        resp = await self._time_client.get(f"{self.registry_url}/api/fa2/time")
        resp.raise_for_status()
        return float(resp.json()["server_time"])

    def calculate_health_score(self) -> float:
        b_score = min(25.0, 25.0 * (self.battery / 70.0))
        t_score = 25.0 if 15 <= self.temperature <= 45 else (10.0 if self.temperature <= 75 else 0.0)
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
            self.battery = max(15.0, self.battery - 0.25 + random.uniform(-0.05, 0.05))
            self.temperature = max(12.0, self.temperature - 0.3 + random.uniform(-0.1, 0.1))
        else:
            self.battery = min(100.0, self.battery + 0.35 + random.uniform(-0.05, 0.05))
            self.temperature = min(42.0, self.temperature + 0.25 + random.uniform(-0.1, 0.1))

        self.cpu_usage = round(max(5.0, min(99.0, 18.0 + 10.0 * math.sin(self.orbit_angle * 3) + random.uniform(-3, 3))), 1)
        self.memory_usage = round(max(10.0, min(95.0, 32.0 + 5.0 * math.cos(self.orbit_angle * 2) + random.uniform(-1, 1))), 1)
        self.signal_strength = round(max(50.0, min(100.0, 94.0 + 5.0 * math.sin(self.orbit_angle * 5) + random.uniform(-2, 2))), 1)

        # Autonomous mode adjustments based on operational telemetry
        if self.battery < 30.0:
            if self.power_mode != "POWER_SAVING":
                logger.warning(f"[{self.satellite_id} AUTONOMY] Battery low ({self.battery:.1f}%) -> Activating POWER_SAVING mode")
                self.power_mode = "POWER_SAVING"
                self.telemetry_interval = 5.0
        elif self.temperature > 80.0:
            if self.power_mode != "THERMAL_PROTECTION":
                logger.warning(f"[{self.satellite_id} AUTONOMY] Temperature spike ({self.temperature:.1f}°C) -> Activating THERMAL_PROTECTION mode")
                self.power_mode = "THERMAL_PROTECTION"
                self.telemetry_interval = 1.0
        else:
            if self.power_mode != "NORMAL":
                logger.info(f"[{self.satellite_id} AUTONOMY] Telemetry nominal -> Restoring NORMAL mode")
                self.power_mode = "NORMAL"
                self.telemetry_interval = 2.0

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
            "power_mode": self.power_mode,
            "neighbor_health_map": self.neighbor_health_map,
            "uptime_seconds": int(time.time() - self.start_time),
            "timestamp": time.time()
        }

    def get_node_state(self) -> Dict[str, Any]:
        state = self.get_telemetry_dict()
        state["known_peers"] = self.peers
        state["peers_refreshed_at"] = self.peers_refreshed_at
        state["gossip_stats"] = dict(self.gossip_stats)
        state["telemetry_publisher"] = self.telemetry_publisher.stats()
        return state

    async def refresh_peers(self) -> None:
        """Discover peer addresses from the registry instead of guessing hostnames."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{self.registry_url}/api/satellites")
            resp.raise_for_status()
            entries = resp.json().get("satellites", [])
        except Exception as exc:
            logger.debug(f"[{self.satellite_id} PEERS] Registry unreachable ({exc}); keeping cached peer list")
            return
        peers = {}
        for entry in entries:
            sid = entry.get("satellite_id")
            if not sid or sid == self.satellite_id or not entry.get("address") or not entry.get("p2p_port"):
                continue
            peers[sid] = {
                "address": entry["address"],
                "p2p_port": int(entry["p2p_port"]),
                "status": entry.get("status", "UNKNOWN"),
            }
        self.peers = peers
        self.peers_refreshed_at = time.time()
        # Seed the FA-2 peer directory too; after this, beacons keep it current even without the registry.
        self.dsync.directory.merge_registry(entries)

    def _gossip_candidates(self, exclude: List[str]) -> List[str]:
        excluded = {p.upper() for p in exclude}
        return [
            sid for sid, info in self.peers.items()
            if sid.upper() not in excluded and info.get("status") not in ("OFFLINE", "DISCONNECTED")
        ]

    def build_gossip_packet(self) -> Dict[str, Any]:
        return {
            "correlation_id": f"EVT-GOSSIP-{self.satellite_id}-{uuid.uuid4().hex[:8]}",
            "origin_satellite_id": self.satellite_id,
            "origin_status": self.status,
            "origin_health": self.calculate_health_score(),
            "origin_battery": round(self.battery, 2),
            "origin_temp": round(self.temperature, 2),
            "hops": 0,
            "path": [],
            "timestamp": time.time(),
        }

    async def propagate_gossip(self, packet: dict) -> bool:
        """Forward a gossip packet to one random peer that is not already on its path."""
        hops = packet.get("hops", 0)
        curr_path = packet.get("path", []) + [self.satellite_id]
        if hops >= GOSSIP_MAX_HOPS:
            return False

        candidates = self._gossip_candidates(exclude=curr_path + [packet.get("origin_satellite_id", "")])
        if not candidates:
            return False

        target_id = random.choice(candidates)
        target = self.peers[target_id]
        url = f"http://{target['address']}:{target['p2p_port']}/p2p/gossip"
        gossip_payload = {
            "correlation_id": packet.get("correlation_id"),
            "origin_satellite_id": packet.get("origin_satellite_id"),
            "origin_status": packet.get("origin_status"),
            "origin_health": packet.get("origin_health"),
            "origin_battery": packet.get("origin_battery"),
            "origin_temp": packet.get("origin_temp"),
            "hops": hops + 1,
            "path": curr_path,
            "timestamp": time.time()
        }
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.post(url, json=gossip_payload)
            resp.raise_for_status()
            logger.info(f"[{self.satellite_id} GOSSIP SENT] -> {target_id} | origin={packet.get('origin_satellite_id')} | hops={hops+1} | path={'->'.join(curr_path)}")
            return True
        except Exception as exc:
            self.gossip_stats["send_failures"] += 1
            logger.warning(f"[{self.satellite_id} GOSSIP FAILED] -> {target_id} at {url}: {exc.__class__.__name__}: {exc}")
            return False

    async def start_gossip_loop(self):
        """Periodically originate a gossip round with this satellite's own state."""
        await asyncio.sleep(random.uniform(1.0, GOSSIP_INTERVAL_SECONDS))  # de-synchronise the five nodes
        last_refresh = 0.0
        while True:
            if self.silent:
                await asyncio.sleep(GOSSIP_INTERVAL_SECONDS)
                continue
            try:
                if time.time() - last_refresh >= PEER_REFRESH_SECONDS or not self.peers:
                    await self.refresh_peers()
                    last_refresh = time.time()
                if await self.propagate_gossip(self.build_gossip_packet()):
                    self.gossip_stats["originated"] += 1
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error(f"[{self.satellite_id}] Error in gossip loop: {exc}")
            await asyncio.sleep(GOSSIP_INTERVAL_SECONDS)

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
                if resp.status_code == 503:
                    self._ground_result(False)  # ground station not accepting satellite traffic
                    return
                self._ground_result(True)
                if resp.status_code != 200:
                    logger.warning(f"[{self.satellite_id}] Heartbeat rejected (HTTP {resp.status_code}); re-registering")
                    await self.register_with_mission_control()
        except Exception as exc:
            self._ground_result(False)
            logger.warning(f"[{self.satellite_id}] Heartbeat to Mission Control failed: {exc.__class__.__name__}: {exc}")

    async def start_autonomous_loop(self):
        # Guarantee registration retry until Mission Control acknowledges registration
        while not getattr(self, 'is_registered', False):
            success = await self.register_with_mission_control()
            if not success:
                await asyncio.sleep(2.0)

        await self.refresh_peers()  # seed the peer directory right away so beacons can start

        while True:
            if self.silent:  # simulated crash: the satellite goes quiet towards everyone
                await asyncio.sleep(2.0)
                continue
            try:
                self.step_telemetry()
                await self.send_heartbeat()  # liveness (HTTP, registry)
                await self._publish_telemetry()  # data stream (RabbitMQ); buffered during a ground blackout
                await asyncio.sleep(2.0)  # fixed cadence: heartbeat timeouts (5s/10s) assume ~2s
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
            logger.info(f"[gRPC IN] {self.node.satellite_id} ← Mission Control | method=GetHealth | status=REQUEST_RECEIVED")
            resp = pb2.HealthResponse(
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
            logger.info(f"[gRPC OUT] {self.node.satellite_id} → Mission Control | method=GetHealth | status=SUCCESS")
            return resp

        async def Ping(self, request, context):
            logger.info(f"[gRPC IN] {self.node.satellite_id} ← Mission Control | method=Ping | status=REQUEST_RECEIVED")
            resp = pb2.PingResponse(
                satellite_id=self.node.satellite_id,
                status="PONG",
                echo_timestamp=request.timestamp,
                response_timestamp=int(time.time() * 1000)
            )
            logger.info(f"[gRPC OUT] {self.node.satellite_id} → Mission Control | method=Ping | status=SUCCESS")
            return resp

        async def GetSatelliteInfo(self, request, context):
            logger.info(f"[gRPC IN] {self.node.satellite_id} ← Mission Control | method=GetSatelliteInfo | status=REQUEST_RECEIVED")
            resp = pb2.InfoResponse(
                satellite_id=self.node.satellite_id,
                node_id=self.node.node_id,
                hostname=self.node.hostname,
                grpc_port=self.node.grpc_port,
                p2p_port=self.node.p2p_port,
                capabilities=["TELEMETRY", "gRPC", "P2P", "RABBITMQ", "WEBRTC"],
                status=self.node.status,
                start_time=int(self.node.start_time)
            )
            logger.info(f"[gRPC OUT] {self.node.satellite_id} → Mission Control | method=GetSatelliteInfo | status=SUCCESS")
            return resp

        async def SendP2PMessage(self, request, context):
            start_t = time.time()
            logger.info(f"[gRPC IN] {self.node.satellite_id} ← {request.source_satellite_id} | method=SendP2PMessage | status=REQUEST_RECEIVED")
            logger.info(f"[{self.node.satellite_id} gRPC P2P] Received message directly from {request.source_satellite_id}: {request.payload}")
            resp = pb2.P2PResponse(
                message_id=request.message_id,
                receiver_satellite_id=self.node.satellite_id,
                acknowledged=True,
                status_message=f"gRPC P2P message delivered directly to {self.node.satellite_id}",
                received_timestamp=int(time.time()),
                processing_delay_ms=round((time.time() - start_t) * 1000, 2)
            )
            logger.info(f"[gRPC OUT] {self.node.satellite_id} → {request.source_satellite_id} | method=SendP2PMessage | status=SUCCESS")
            return resp

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

    @app.post("/p2p/gossip")
    async def receive_gossip(packet: dict):
        if node.silent:
            from fastapi import HTTPException
            raise HTTPException(status_code=503, detail="satellite silent (simulated crash)")
        cid = packet.get("correlation_id", f"EVT-GOSSIP-{int(time.time()*1000)}")
        origin_id = packet.get("origin_satellite_id")
        path = packet.get("path", [])
        hops = packet.get("hops", 0)
        
        if origin_id:
            node.neighbor_health_map[origin_id] = {
                "status": packet.get("origin_status"),
                "health_score": packet.get("origin_health"),
                "battery": packet.get("origin_battery"),
                "temperature": packet.get("origin_temp"),
                "updated_at": time.time(),
                "hops": hops,
                "path": path + [node.satellite_id]
            }
        
        node.gossip_history.append({
            "correlation_id": cid,
            "origin": origin_id,
            "hops": hops,
            "path": path + [node.satellite_id],
            "received_at": time.time()
        })
        
        node.gossip_history = node.gossip_history[-200:]
        node.gossip_stats["received"] += 1
        logger.info(f"[{node.satellite_id} GOSSIP RECEIVED] origin={origin_id} via {'->'.join(path) or origin_id} (hops={hops})")

        if hops < GOSSIP_MAX_HOPS:
            async def _forward():
                if await node.propagate_gossip(packet):
                    node.gossip_stats["forwarded"] += 1
            asyncio.create_task(_forward())
            
        return {"status": "RECEIVED", "receiver": node.satellite_id, "hops": hops + 1, "correlation_id": cid}

    @app.get("/p2p/state")
    async def get_node_state():
        return node.get_node_state()

    # FA-2: satellite-to-satellite algorithm messages and Mission Control's control commands
    app.include_router(create_dsync_router(node.dsync, node.fetch_server_time))
    # Unit 4: OrbitFS DataNode + MapReduce task tracker
    app.include_router(create_datanode_router(node.dsync.datanode))

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

async def run_satellite(sat_id: str, grpc_port: int, p2p_port: int, registry_url: str,
                        rabbitmq_url: Optional[str] = None):
    node = SatelliteNode(sat_id, grpc_port, p2p_port, registry_url, rabbitmq_url=rabbitmq_url)

    # Start Autonomous Telemetry Loop (heartbeat + RabbitMQ telemetry)
    asyncio.create_task(node.start_autonomous_loop())

    # Start satellite-to-satellite gossip (peer-discovered, no Mission Control relay)
    asyncio.create_task(node.start_gossip_loop())

    # Start FA-2 services: event shipping, beacons, leader watch
    node.dsync.start()

    # Unit 4: export the payload as a Pyro5 remote object (port 7000 + satellite number by default)
    pyro_port = int(os.getenv("PYRO_PORT", str(7000 + int(sat_id.split("-")[-1]))))
    start_pyro(node.dsync, os.getenv("PYRO_HOST", node.address), pyro_port)

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
    parser.add_argument("--rabbitmq", type=str, default=os.getenv("RABBITMQ_URL"),
                        help="RabbitMQ URL for telemetry publishing (default: $RABBITMQ_URL; HTTP fallback if unset/unreachable)")

    args = parser.parse_args()
    asyncio.run(run_satellite(args.id, args.grpc_port, args.p2p_port, args.registry, rabbitmq_url=args.rabbitmq))
