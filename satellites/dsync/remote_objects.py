"""
Distributed objects (Unit 4) with Pyro5: every satellite exports a PayloadController OBJECT and
registers it in the Pyro name server (run by Mission Control) as  satellite.<ID>.payload.

Contrast with the gRPC interface from FA-1:
- gRPC: stateless remote PROCEDURES (GetHealth, Ping) described by a .proto contract.
- Pyro5: a remote OBJECT with identity and state. Clients look it up by name, get a proxy, and
  method calls act on that one object: point() changes where its camera points, capture() increments
  its own capture counter, and later calls see that state.
"""

import logging
import os
import threading
import time
from typing import Any, Dict, List

logger = logging.getLogger("dsync.objects")

try:
    import Pyro5.api
    import Pyro5.errors
    HAS_PYRO = True
except Exception:  # pragma: no cover - satellites still run without Pyro5
    HAS_PYRO = False


if HAS_PYRO:
    @Pyro5.api.expose
    @Pyro5.api.behavior(instance_mode="single")
    class PayloadController:
        """The satellite's camera payload, as one remote object."""

        def __init__(self, node: Any):
            self._node = node
            self._lock = threading.Lock()
            self._pointing = {"lat": 0.0, "lon": 0.0}
            self._mode = "STANDBY"
            self._captures: List[Dict[str, Any]] = []
            self._created = time.time()

        def _alive(self) -> None:
            if self._node.transport.silent:
                raise RuntimeError(f"{self._node.node_id} is not responding (simulated crash)")

        def status(self) -> Dict[str, Any]:
            self._alive()
            with self._lock:
                return {"satellite": self._node.node_id, "object_id": id(self), "mode": self._mode,
                        "pointing": dict(self._pointing), "captures": len(self._captures),
                        "alive_since": self._created}

        def point(self, lat: float, lon: float) -> Dict[str, Any]:
            self._alive()
            if not (-90 <= float(lat) <= 90 and -180 <= float(lon) <= 180):
                raise ValueError("lat must be in [-90, 90] and lon in [-180, 180]")
            with self._lock:
                self._pointing = {"lat": float(lat), "lon": float(lon)}
                self._mode = "POINTED"
            self._node.transport.local_event("PAYLOAD_POINTED", algo="objects", detail=dict(self._pointing))
            return self.status()

        def capture(self) -> Dict[str, Any]:
            self._alive()
            with self._lock:
                cap = {"capture_id": f"{self._node.node_id}-IMG-{len(self._captures) + 1:04d}",
                       "pointing": dict(self._pointing), "at": time.time()}
                self._captures.append(cap)
                self._mode = "IMAGING"
            self._node.transport.local_event("PAYLOAD_CAPTURE", algo="objects", detail=cap)
            return {**cap, "total_captures": len(self._captures)}

        def set_mode(self, mode: str) -> Dict[str, Any]:
            self._alive()
            if mode not in ("STANDBY", "POINTED", "IMAGING", "SAFE"):
                raise ValueError("mode must be STANDBY, POINTED, IMAGING or SAFE")
            with self._lock:
                self._mode = mode
            return self.status()

        def recent_captures(self, n: int = 5) -> List[Dict[str, Any]]:
            self._alive()
            with self._lock:
                return self._captures[-int(n):]


def start_pyro(node: Any, host: str, port: int) -> None:
    """Run the Pyro daemon in a background thread and keep the name-server registration alive."""
    if not HAS_PYRO:
        logger.warning("Pyro5 not installed: distributed objects disabled")
        return
    ns_host = os.getenv("PYRO_NS_HOST", "127.0.0.1")
    ns_port = int(os.getenv("PYRO_NS_PORT", "9090"))
    name = f"satellite.{node.node_id}.payload"

    def serve() -> None:
        try:
            daemon = Pyro5.api.Daemon(host=host, port=port)
        except Exception as exc:
            logger.warning("Pyro daemon could not start on %s:%s: %s", host, port, exc)
            return
        uri = daemon.register(PayloadController(node), objectId=name)
        node.pyro_uri = str(uri)

        def keep_registered() -> None:
            while True:
                try:
                    with Pyro5.api.locate_ns(host=ns_host, port=ns_port) as ns:
                        ns.register(name, uri, safe=False)
                    node.pyro_registered = True
                except Exception:
                    node.pyro_registered = False
                time.sleep(10.0)
        threading.Thread(target=keep_registered, daemon=True, name="pyro-register").start()
        logger.info("Pyro object %s at %s", name, uri)
        daemon.requestLoop()

    threading.Thread(target=serve, daemon=True, name="pyro-daemon").start()
