"""
DsyncNode: everything FA-2 runs inside one satellite process, plus its HTTP API.

  /dsync/msg                    satellite-to-satellite messages (all algorithms)
  /dsync/state, /dsync/events   what this satellite knows (read by Mission Control)
  /dsync/control/...            commands from Mission Control: start an algorithm, inject a fault

Mission Control only starts things and reads results; every decision (who leads, who may enter the
critical section, how much to adjust a clock) is taken here, from messages between satellites.
"""

import asyncio
import logging
import time
from typing import Any, Awaitable, Callable, Dict, List, Optional

from .beacon import BeaconService
from .clocks import PhysicalClock
from .clocksync import ClockSyncService
from .election import ElectionService
from .events import EventReporter
from .mutex import ALGORITHMS as MUTEX_ALGORITHMS, MutexError, MutexService
from .transport import HttpNetwork, PeerDirectory, PeerUnreachable, Transport

logger = logging.getLogger("dsync.node")

ALL_SATELLITES = ["SAT-01", "SAT-02", "SAT-03", "SAT-04", "SAT-05"]
LEADER_CHECK_INTERVAL = 3.0
STARTUP_GRACE = 6.0


class DsyncNode:
    def __init__(self, node_id: str, info: Callable[[], Dict[str, Any]], *, network: Any = None,
                 event_sink: Optional[Callable[[List[Dict[str, Any]]], Awaitable[bool]]] = None,
                 all_nodes: Optional[List[str]] = None, directory_clock: Callable[[], float] = time.monotonic,
                 beacon_interval: float = 2.0, election_algorithm: str = "bully"):
        self.node_id = node_id
        self.info = info
        self.started_at = time.time()
        self.physical = PhysicalClock()
        self.directory = PeerDirectory(node_id, clock=directory_clock)
        self.reporter = EventReporter(node_id, sink=event_sink)
        self.transport = Transport(node_id, self.directory, network or HttpNetwork(), self.reporter,
                                   self.physical, all_nodes or ALL_SATELLITES)
        self.partition_groups: Optional[List[List[str]]] = None
        self.election = ElectionService(self, default_algorithm=election_algorithm)
        self.beacons = BeaconService(self, interval=beacon_interval)
        self.clocksync = ClockSyncService(self)
        self.mutex = MutexService(self)
        self.beacons.on_peer_dead += [self.election.on_peer_dead, self.mutex.on_peer_dead]
        self.transport.on("CROSSLINK", self._on_crosslink)
        self._tasks: List[asyncio.Task] = []

    # ------------------------------------------------------------ lifecycle
    def start(self) -> None:
        loop = asyncio.get_running_loop()
        self._tasks = [loop.create_task(self.reporter.run()), loop.create_task(self.beacons.run()),
                       loop.create_task(self._leader_watch())]

    async def stop(self) -> None:
        for t in self._tasks:
            t.cancel()

    async def _leader_watch(self) -> None:
        await asyncio.sleep(STARTUP_GRACE)
        while True:
            try:
                await self.election.ensure_leader()
            except asyncio.CancelledError:
                break
            except Exception as exc:  # pragma: no cover
                logger.warning("leader watch error: %s", exc)
            await asyncio.sleep(LEADER_CHECK_INTERVAL)

    # ------------------------------------------------------------ faults (enforced here)
    def apply_fault(self, fault: str, params: Dict[str, Any]) -> Dict[str, Any]:
        fault = fault.upper()
        t = self.transport
        if fault == "CLOCK_DRIFT":
            self.physical.inject_fault(float(params.get("offset_ms", 0.0)),
                                       None if params.get("drift_ppm") is None else float(params["drift_ppm"]))
        elif fault == "CLOCK_RESET":
            self.physical.reset()
        elif fault == "PARTITION":
            groups = params.get("groups") or []
            mine = next((g for g in groups if self.node_id in g), [self.node_id])
            everyone = set(ALL_SATELLITES) | set(self.directory.known_ids())
            t.blocked = {n for n in everyone if n not in mine}
            self.partition_groups = groups
        elif fault == "HEAL":
            t.blocked = set()
            self.partition_groups = None
        elif fault == "CRASH":
            t.silent = True
        elif fault == "RECOVER":
            was_silent, t.silent = t.silent, False
            if was_silent:
                asyncio.ensure_future(self._after_recovery())
        else:
            raise ValueError(f"unknown fault {fault}")
        # recorded even while silent: it is this satellite's own log
        t.local_event(f"FAULT_{fault}", algo="fault", detail=params or None)
        logger.warning("[%s FAULT] %s %s", self.node_id, fault, params or "")
        return self.state()

    async def _after_recovery(self) -> None:
        """Classic Bully: a recovered satellite holds an election (it may outrank the current leader).
        It first waits for a beacon round so it knows who is alive again."""
        await asyncio.sleep(self.beacons.interval * 1.5)
        if self.election.default_algorithm == "bully" and not self.transport.silent:
            await self.election.start("bully", reason="RECOVERED")

    async def _on_crosslink(self, env: Dict[str, Any]) -> None:
        return None

    # ------------------------------------------------------------ state
    def state(self) -> Dict[str, Any]:
        return {
            "node": self.node_id,
            "silent": self.transport.silent,
            "blocked": sorted(self.transport.blocked),
            "partition_groups": self.partition_groups,
            "clock": self.physical.to_dict(),
            "lamport": self.transport.lamport.value,
            "vector": self.transport.vector.to_dict(),
            "election": self.election.to_dict(),
            "mutex": self.mutex.to_dict(),
            "peers": self.directory.snapshot(),
            "beacons": self.beacons.stats(),
            "transport": self.transport.stats(),
            "events": self.reporter.stats(),
            "clock_sync_history": self.clocksync.history[-5:],
        }


def create_dsync_router(node: DsyncNode, fetch_server_time: Callable[[], Awaitable[float]]):
    from fastapi import APIRouter, Body, HTTPException

    router = APIRouter(prefix="/dsync")

    @router.post("/msg")
    async def receive(env: Dict[str, Any] = Body(...)):
        return await node.transport.receive(env)

    @router.get("/state")
    async def state():
        return node.state()

    @router.get("/events")
    async def events(since: int = 0, limit: int = 500):
        return {"node": node.node_id, "events": node.reporter.since(since, limit)}

    @router.post("/control/fault")
    async def fault(body: Dict[str, Any] = Body(...)):
        try:
            return node.apply_fault(body.get("type", ""), body.get("params") or {})
        except ValueError as exc:
            raise HTTPException(422, str(exc))

    @router.post("/control/election/start")
    async def election_start(body: Dict[str, Any] = Body(default={})):
        algo = (body.get("algorithm") or node.election.default_algorithm).lower()
        if algo not in node.election.ALGORITHMS:
            raise HTTPException(422, f"algorithm must be one of {node.election.ALGORITHMS}")
        asyncio.create_task(node.election.start(algo, body.get("run_id"), reason="MISSION_CONTROL"))
        return {"started": True, "algorithm": algo, "initiator": node.node_id}

    @router.post("/control/election/config")
    async def election_config(body: Dict[str, Any] = Body(...)):
        algo = (body.get("algorithm") or "").lower()
        if algo not in node.election.ALGORITHMS:
            raise HTTPException(422, f"algorithm must be one of {node.election.ALGORITHMS}")
        node.election.default_algorithm = algo
        return node.election.to_dict()

    @router.post("/control/clock/cristian")
    async def cristian(body: Dict[str, Any] = Body(default={})):
        if node.transport.silent:
            raise HTTPException(409, "satellite is silent")
        try:
            return await node.clocksync.cristian(fetch_server_time, body.get("run_id"))
        except Exception as exc:
            raise HTTPException(502, f"time server unreachable: {exc}")

    @router.post("/control/clock/berkeley")
    async def berkeley(body: Dict[str, Any] = Body(default={})):
        try:
            return await node.clocksync.berkeley(body.get("run_id") or f"berkeley-{int(time.time())}")
        except RuntimeError as exc:
            raise HTTPException(409, str(exc))

    @router.post("/control/mutex/run")
    async def mutex_run(body: Dict[str, Any] = Body(...)):
        algo = body.get("algorithm")
        if algo not in MUTEX_ALGORITHMS:
            raise HTTPException(422, f"algorithm must be one of {MUTEX_ALGORITHMS}")
        results = await node.mutex.run_rounds(algo, body.get("run_id"), int(body.get("rounds", 3)),
                                              float(body.get("hold_ms", 100)), body.get("start_at"))
        return {"node": node.node_id, "algorithm": algo, "results": results}

    @router.post("/control/mutex/token")
    async def token(body: Dict[str, Any] = Body(...)):
        return node.mutex.token_control(body.get("action", "stop"), body.get("run_id"), body.get("ring"),
                                        bool(body.get("create")))

    @router.post("/control/send")
    async def crosslink(body: Dict[str, Any] = Body(...)):
        dest = body.get("dest")
        try:
            await node.transport.send(dest, "CROSSLINK", {"label": body.get("label", "cross-link")},
                                      algo="lens", run_id=body.get("run_id"))
            return {"delivered": True, "from": node.node_id, "to": dest}
        except PeerUnreachable as exc:
            return {"delivered": False, "from": node.node_id, "to": dest, "reason": str(exc)}

    @router.post("/control/local")
    async def local(body: Dict[str, Any] = Body(default={})):
        return node.transport.local_event(body.get("label", "LOCAL_EVENT"), algo="lens", run_id=body.get("run_id"))

    return router
