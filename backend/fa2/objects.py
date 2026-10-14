"""
Distributed objects (Unit 4): Mission Control runs the Pyro5 NAME SERVER; each satellite registers its
PayloadController object there. Clients look objects up by name and call methods through a proxy.
Also: /api/gateway/whoami, so the UI can show which Mission Control replica the gateway picked.
"""

import asyncio
import logging
import os
import socket
import threading
import time
from typing import Any, Dict

from fastapi import APIRouter, Body, HTTPException

logger = logging.getLogger("DistributedObjects")
router = APIRouter(tags=["Unit 4: distributed objects + gateway"])

ALLOWED = {"status": [], "point": ["lat", "lon"], "capture": [], "set_mode": ["mode"], "recent_captures": ["n"]}
NS_HOST = os.getenv("PYRO_NS_BIND", "0.0.0.0")
NS_PORT = int(os.getenv("PYRO_NS_PORT", "9090"))
_ns_started = {"ok": False, "error": None}

try:
    import Pyro5.api
    import Pyro5.nameserver
    HAS_PYRO = True
except Exception:  # pragma: no cover
    HAS_PYRO = False


def start_name_server() -> None:
    if not HAS_PYRO or os.getenv("PYRO_NAMESERVER", "1") != "1":
        return

    def run() -> None:
        try:
            _ns_started["ok"] = True
            Pyro5.nameserver.start_ns_loop(host=NS_HOST, port=NS_PORT)
        except Exception as exc:
            _ns_started.update({"ok": False, "error": str(exc)})
            logger.warning("Pyro name server failed: %s", exc)
    threading.Thread(target=run, daemon=True, name="pyro-ns").start()


def _ns():
    host = "127.0.0.1" if NS_HOST == "0.0.0.0" else NS_HOST
    return Pyro5.api.locate_ns(host=os.getenv("PYRO_NS_HOST", host), port=NS_PORT)


@router.get("/api/objects")
async def list_objects():
    if not HAS_PYRO:
        raise HTTPException(501, "Pyro5 is not installed")

    def lookup():
        with _ns() as ns:
            return {name: uri for name, uri in ns.list(prefix="satellite.").items()}
    try:
        objects = await asyncio.get_running_loop().run_in_executor(None, lookup)
    except Exception as exc:
        raise HTTPException(503, f"name server unreachable: {exc}")
    return {"name_server": f"{NS_HOST}:{NS_PORT}", "objects": objects, "methods": ALLOWED}


@router.post("/api/objects/call")
async def call_object(body: Dict[str, Any] = Body(...)):
    if not HAS_PYRO:
        raise HTTPException(501, "Pyro5 is not installed")
    name, method, args = body.get("name"), body.get("method"), body.get("args") or {}
    if method not in ALLOWED:
        raise HTTPException(422, f"method must be one of {sorted(ALLOWED)}")
    kwargs = {k: args[k] for k in ALLOWED[method] if k in args}

    def invoke():
        t = time.time()
        with Pyro5.api.Proxy(f"PYRONAME:{name}@{os.getenv('PYRO_NS_HOST', '127.0.0.1')}:{NS_PORT}") as proxy:
            proxy._pyroTimeout = 5.0
            out = getattr(proxy, method)(**kwargs)
            return out, round((time.time() - t) * 1000, 2), str(proxy._pyroUri)
    try:
        result, ms, uri = await asyncio.get_running_loop().run_in_executor(None, invoke)
    except Exception as exc:
        raise HTTPException(502, f"{exc.__class__.__name__}: {exc}")
    return {"object": name, "method": method, "args": kwargs, "result": result, "latency_ms": ms, "resolved_uri": uri}


@router.get("/api/gateway/whoami")
async def whoami():
    from backend.fa2.role import state
    return {"instance": os.getenv("MC_INSTANCE", "primary"), "active": state["active"], "host": socket.gethostname(),
            "pid": os.getpid(), "role_transitions": state["transitions"][-5:], "at": time.time()}
