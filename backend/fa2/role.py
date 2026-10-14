"""
Active / passive role of a Mission Control replica (Unit 4: web gateway with a warm standby).

The primary is always active. A standby (MC_INSTANCE != primary, PRIMARY_URL set) stays PASSIVE -
it consumes the same RabbitMQ fanout streams but does not trigger functions or repair OrbitFS -
until it cannot reach the primary twice in a row; then it becomes ACTIVE (failover). When the
primary answers again, the standby steps back.
"""

import asyncio
import logging
import os
import time

import httpx

logger = logging.getLogger("Role")

INSTANCE = os.getenv("MC_INSTANCE", "primary")
PRIMARY_URL = os.getenv("PRIMARY_URL", "")
state = {"instance": INSTANCE, "active": INSTANCE == "primary" or not PRIMARY_URL, "since": time.time(),
         "transitions": []}


def is_active() -> bool:
    return state["active"]


async def monitor() -> None:
    if INSTANCE == "primary" or not PRIMARY_URL:
        return
    misses = 0
    async with httpx.AsyncClient(timeout=2.0) as client:
        while True:
            try:
                r = await client.get(f"{PRIMARY_URL}/api/gateway/whoami")
                ok = r.status_code == 200
            except Exception:
                ok = False
            misses = 0 if ok else misses + 1
            want_active = misses >= 2
            if want_active != state["active"]:
                state.update({"active": want_active, "since": time.time()})
                state["transitions"].append({"at": time.time(), "active": want_active})
                logger.warning("[ROLE] %s is now %s", INSTANCE, "ACTIVE (primary unreachable)" if want_active else "PASSIVE")
            await asyncio.sleep(3.0)
