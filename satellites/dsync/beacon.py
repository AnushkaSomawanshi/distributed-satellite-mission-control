"""
Beacon protocol (Unit 3).

Every satellite sends a BEACON to every satellite it knows about, every BEACON_INTERVAL seconds.
A beacon carries the sender's identity, address, health/priority, its view of the leader and term,
and its clock reading. Receivers use beacons for:
- neighbour discovery: a beacon from an unknown satellite adds it to the directory;
- failure detection without Mission Control: no beacon for 3 s -> SUSPECTED, 5 s -> DEAD;
- clock-offset estimation: sender's clock reading vs. own clock on arrival (includes one-way delay).

Beacons are control-plane traffic: they do not tick Lamport/vector clocks (otherwise the
causality view would be flooded), but every liveness transition is a stamped local event.
"""

import asyncio
import logging
import time
from typing import Any, Awaitable, Callable, Dict, List, Optional

logger = logging.getLogger("dsync.beacon")

BEACON_INTERVAL = 2.0


class BeaconService:
    def __init__(self, node: Any, interval: float = BEACON_INTERVAL):
        self.node = node
        self.interval = interval
        self.sent = 0
        self.received = 0
        self.failures = 0
        self.detections: List[Dict[str, Any]] = []
        self.on_peer_dead: List[Callable[[str], Awaitable[None]]] = []
        self.on_peer_recovered: List[Callable[[str], Awaitable[None]]] = []
        node.transport.on("BEACON", self._handle_beacon)

    def build_payload(self) -> Dict[str, Any]:
        info = self.node.info()
        return {
            "address": info["address"],
            "p2p_port": info["p2p_port"],
            "health": info["health"],
            "battery": info.get("battery"),
            "signal": info.get("signal"),
            "tasks": self.node.tasks.summary(),
            "ledger": self.node.ledger.summary(),
            "priority": self.node.election.priority(),
            "leader": self.node.election.leader,
            "term": self.node.election.term,
            "clock_reading": self.node.physical.now(),
            "position": info.get("position"),
        }

    async def _beacon_one(self, peer_id: str, payload: Dict[str, Any]) -> None:
        try:
            await self.node.transport.send(peer_id, "BEACON", payload, tracked=False, timeout=1.0)
            self.sent += 1
        except Exception:
            self.failures += 1

    async def beacon_round(self) -> None:
        if self.node.transport.silent:
            return
        payload = self.build_payload()
        targets = self.node.directory.known_ids()
        await asyncio.gather(*(self._beacon_one(p, payload) for p in targets))
        await self.check_liveness()

    async def check_liveness(self) -> None:
        for t in self.node.directory.evaluate():
            label = {"SUSPECTED": "PEER_SUSPECTED", "DEAD": "PEER_DEAD", "ALIVE": "PEER_RECOVERED"}[t["to"]]
            self.node.transport.local_event(label, algo="beacon", detail=t)
            logger.info("[%s BEACON] %s %s -> %s after %.1fs of silence",
                        self.node.node_id, t["peer"], t["from"], t["to"], t["silence_s"])
            if t["to"] == "DEAD":
                self.detections.append({**t, "detected_at": time.time()})
                self.detections = self.detections[-50:]
                for cb in self.on_peer_dead:
                    asyncio.create_task(cb(t["peer"]))

    async def _handle_beacon(self, env: Dict[str, Any]) -> None:
        p = env.get("payload", {})
        src = env["src"]
        offset_ms = None
        if p.get("clock_reading") is not None:
            offset_ms = round((p["clock_reading"] - self.node.physical.now()) * 1000.0, 3)
        previous = self.node.directory.mark_beacon(
            src, address=p.get("address"), p2p_port=p.get("p2p_port"),
            health=p.get("health"), priority=p.get("priority"), battery=p.get("battery"), signal=p.get("signal"),
            leader=p.get("leader"), term=p.get("term"),
            clock_offset_ms=offset_ms, position=p.get("position"),
        )
        self.received += 1
        if previous in ("DEAD", "SUSPECTED"):
            self.node.transport.local_event("PEER_RECOVERED", algo="beacon", detail={"peer": src, "from": previous})
            for cb in self.on_peer_recovered:
                asyncio.create_task(cb(src))
        await self.node.election.observe_beacon(src, p)
        self.node.tasks.observe_beacon(src, p)
        self.node.ledger.observe_beacon(src, p)
        return None

    async def run(self) -> None:
        while True:
            try:
                await self.beacon_round()
            except asyncio.CancelledError:
                break
            except Exception as exc:  # pragma: no cover
                logger.warning("beacon loop error: %s", exc)
            await asyncio.sleep(self.interval)

    def stats(self) -> Dict[str, Any]:
        return {"sent": self.sent, "received": self.received, "send_failures": self.failures,
                "recent_detections": self.detections[-10:]}
