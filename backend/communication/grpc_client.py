import time
import asyncio
import logging
from typing import Dict, Any, Optional, Tuple
import grpc

logger = logging.getLogger(__name__)

class GRPCClientManager:
    """
    Manages gRPC connections to satellite nodes.
    Discovers target satellite addresses from registry and issues async RPC requests.
    """
    def __init__(self, registry):
        self.registry = registry

    async def _get_channel(self, satellite_id: str) -> Tuple[Optional[grpc.aio.Channel], Optional[str]]:
        reg = self.registry.lookup(satellite_id)
        if not reg:
            return None, f"Satellite {satellite_id} not found in service registry"
        if reg.status == "OFFLINE":
            return None, f"Satellite {satellite_id} is currently OFFLINE"
        
        target = f"{reg.address}:{reg.grpc_port}"
        channel = grpc.aio.insecure_channel(target)
        return channel, target

    async def invoke_rpc(
        self,
        target_satellite_id: str,
        method_name: str,
        payload: Optional[Dict[str, Any]] = None,
        timeout: float = 3.0
    ) -> Dict[str, Any]:
        start_time = time.time()
        reg = self.registry.lookup(target_satellite_id)
        if not reg:
            return {
                "success": False,
                "error": f"Target {target_satellite_id} not in registry",
                "latency_ms": round((time.time() - start_time) * 1000, 2),
                "timestamp": time.time()
            }

        if reg.status == "OFFLINE":
            return {
                "success": False,
                "error": f"Target {target_satellite_id} is OFFLINE",
                "latency_ms": round((time.time() - start_time) * 1000, 2),
                "timestamp": time.time()
            }

        try:
            # Dynamically import generated proto or fallback to HTTP RPC endpoint
            try:
                import proto.satellite_pb2 as pb2
                import proto.satellite_pb2_grpc as pb2_grpc
                
                target_endpoint = f"{reg.address}:{reg.grpc_port}"
                async with grpc.aio.insecure_channel(target_endpoint) as channel:
                    stub = pb2_grpc.SatelliteServiceStub(channel)
                    
                    if method_name == "GetHealth":
                        req = pb2.HealthRequest(caller_id="MissionControl", timestamp=int(time.time()))
                        res = await asyncio.wait_for(stub.GetHealth(req), timeout=timeout)
                        latency = round((time.time() - start_time) * 1000, 2)
                        return {
                            "success": True,
                            "method": "GetHealth",
                            "target": target_satellite_id,
                            "latency_ms": latency,
                            "data": {
                                "satellite_id": res.satellite_id,
                                "status": res.status,
                                "health_score": res.health_score,
                                "battery_level": res.battery_level,
                                "temperature": res.temperature,
                                "cpu_usage": res.cpu_usage,
                                "memory_usage": res.memory_usage,
                                "signal_strength": res.signal_strength,
                                "uptime_seconds": res.uptime_seconds
                            },
                            "timestamp": time.time()
                        }
                    elif method_name == "Ping":
                        req = pb2.PingRequest(sender_id="MissionControl", timestamp=int(time.time() * 1000))
                        res = await asyncio.wait_for(stub.Ping(req), timeout=timeout)
                        latency = round((time.time() - start_time) * 1000, 2)
                        return {
                            "success": True,
                            "method": "Ping",
                            "target": target_satellite_id,
                            "latency_ms": latency,
                            "data": {
                                "status": res.status,
                                "echo_timestamp": res.echo_timestamp,
                                "response_timestamp": res.response_timestamp
                            },
                            "timestamp": time.time()
                        }
                    elif method_name == "GetSatelliteInfo":
                        req = pb2.InfoRequest(caller_id="MissionControl")
                        res = await asyncio.wait_for(stub.GetSatelliteInfo(req), timeout=timeout)
                        latency = round((time.time() - start_time) * 1000, 2)
                        return {
                            "success": True,
                            "method": "GetSatelliteInfo",
                            "target": target_satellite_id,
                            "latency_ms": latency,
                            "data": {
                                "satellite_id": res.satellite_id,
                                "node_id": res.node_id,
                                "hostname": res.hostname,
                                "grpc_port": res.grpc_port,
                                "p2p_port": res.p2p_port,
                                "capabilities": list(res.capabilities),
                                "status": res.status
                            },
                            "timestamp": time.time()
                        }
            except (ImportError, Exception) as py_grpc_err:
                # Fallback to direct HTTP RPC bridge endpoint exposed by satellite node
                import httpx
                http_target = f"http://{reg.address}:{reg.p2p_port + 1000}/rpc/{method_name}"
                async with httpx.AsyncClient(timeout=timeout) as client:
                    resp = await client.post(http_target, json=payload or {})
                    latency = round((time.time() - start_time) * 1000, 2)
                    if resp.status_code == 200:
                        return {
                            "success": True,
                            "method": method_name,
                            "target": target_satellite_id,
                            "latency_ms": latency,
                            "data": resp.json(),
                            "timestamp": time.time()
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"HTTP gRPC fallback returned status {resp.status_code}",
                            "latency_ms": latency,
                            "timestamp": time.time()
                        }
        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": f"RPC call to {target_satellite_id} timed out after {timeout}s",
                "latency_ms": round((time.time() - start_time) * 1000, 2),
                "timestamp": time.time()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "latency_ms": round((time.time() - start_time) * 1000, 2),
                "timestamp": time.time()
            }
