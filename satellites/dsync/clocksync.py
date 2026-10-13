"""
Physical clock synchronisation on the satellites (Unit 3).

Cristian's algorithm (external sync, ground available):
  the satellite asks Mission Control's time server, measures the round trip on its OWN clock,
  sets its clock to  T_server + RTT/2.  Error bound: +/- RTT/2.

Berkeley algorithm (internal sync, no time server needed - runs among satellites):
  the elected leader (time daemon) polls every live satellite for its clock reading, corrects each
  reading by half the measured round trip, averages the readings that are within an outlier bound,
  and tells every satellite (itself included) by how much to adjust. Berkeley converges the clocks
  to EACH OTHER (their average), not to true time - the reports show both.
"""

import asyncio
import logging
import statistics
import time
from typing import Any, Dict, List, Optional

from .transport import PeerUnreachable

logger = logging.getLogger("dsync.clocksync")

OUTLIER_BOUND_MS = 10_000.0


class ClockSyncService:
    def __init__(self, node: Any, outlier_bound_ms: float = OUTLIER_BOUND_MS):
        self.node = node
        self.outlier_bound_ms = outlier_bound_ms
        self.history: List[Dict[str, Any]] = []
        node.transport.on("TIME_POLL", self._on_poll)
        node.transport.on("TIME_ADJUST", self._on_adjust)

    def _remember(self, record: Dict[str, Any]) -> Dict[str, Any]:
        self.history.append(record)
        self.history = self.history[-50:]
        return record

    # ------------------------------------------------------------- Cristian
    async def cristian(self, fetch_server_time, run_id: Optional[str] = None, samples: int = 3) -> Dict[str, Any]:
        """fetch_server_time: async () -> server time in seconds (Mission Control's /api/fa2/time).

        Cristian's refinement: take several samples and keep the one with the smallest round trip,
        because the RTT/2 estimate is most accurate when the delay is smallest.
        """
        clock = self.node.physical
        before = clock.skew_ms()
        best = None
        for _ in range(max(1, samples)):
            t0 = clock.now()
            server_time = await fetch_server_time()
            t1 = clock.now()
            if best is None or (t1 - t0) < best[1] - best[0]:
                best = (t0, t1, server_time)
        t0, t1, server_time = best
        rtt = t1 - t0
        # The chosen sample is older than "now": carry it forward by the time elapsed since t1.
        elapsed = clock.now() - t1
        estimate_now = server_time + rtt / 2.0 + elapsed
        adjustment = estimate_now - clock.now()
        clock.adjust(adjustment)
        after = clock.skew_ms()
        record = {
            "algorithm": "cristian", "node": self.node.node_id, "run_id": run_id, "samples": samples,
            "rtt_ms": round(rtt * 1000, 3), "error_bound_ms": round(rtt * 500, 3),
            "adjustment_ms": round(adjustment * 1000, 3),
            "skew_before_ms": round(before, 3), "skew_after_ms": round(after, 3),
            "at": time.time(),
        }
        self.node.transport.local_event("CLOCK_ADJUSTED", algo="cristian", run_id=run_id, detail=record)
        return self._remember(record)

    # ------------------------------------------------------------- Berkeley
    async def _poll(self, peer: str, run_id: str) -> Optional[Dict[str, Any]]:
        clock = self.node.physical
        t0 = clock.now()
        try:
            reply = await self.node.transport.request(peer, "TIME_POLL", {}, algo="berkeley", run_id=run_id, timeout=1.5)
        except PeerUnreachable:
            return None
        t1 = clock.now()
        rtt = t1 - t0
        # Peer's clock at the moment the reply arrived, minus our clock at that moment.
        diff_ms = ((reply["clock_reading"] + rtt / 2.0) - t1) * 1000.0
        return {"peer": peer, "rtt_ms": round(rtt * 1000, 3), "diff_ms": diff_ms, "true_skew_ms": reply.get("true_skew_ms")}

    async def berkeley(self, run_id: str) -> Dict[str, Any]:
        if self.node.election.leader != self.node.node_id:
            raise RuntimeError(f"{self.node.node_id} is not the leader (leader={self.node.election.leader})")
        me = self.node.node_id
        self.node.transport.local_event("BERKELEY_START", algo="berkeley", run_id=run_id)
        polls = [p for p in await asyncio.gather(*(self._poll(p, run_id) for p in self.node.directory.live_ids())) if p]
        readings = [{"peer": me, "rtt_ms": 0.0, "diff_ms": 0.0, "true_skew_ms": self.node.physical.skew_ms()}] + polls
        median = statistics.median(r["diff_ms"] for r in readings)
        used = [r for r in readings if abs(r["diff_ms"] - median) <= self.outlier_bound_ms]
        average = sum(r["diff_ms"] for r in used) / len(used)

        async def adjust(r: Dict[str, Any]) -> Dict[str, Any]:
            delta_ms = average - r["diff_ms"]
            entry = {"node": r["peer"], "rtt_ms": r["rtt_ms"], "offset_from_leader_ms": round(r["diff_ms"], 3),
                     "adjustment_ms": round(delta_ms, 3), "used_in_average": r in used,
                     "skew_before_ms": None if r["true_skew_ms"] is None else round(r["true_skew_ms"], 3)}
            if r["peer"] == me:
                self.node.physical.adjust(delta_ms / 1000.0)
                entry["skew_after_ms"] = round(self.node.physical.skew_ms(), 3)
                return entry
            try:
                reply = await self.node.transport.request(r["peer"], "TIME_ADJUST", {"delta_ms": delta_ms},
                                                          algo="berkeley", run_id=run_id, timeout=1.5)
                entry["skew_after_ms"] = round(reply.get("true_skew_ms"), 3) if reply else None
            except PeerUnreachable:
                entry["skew_after_ms"] = None
                entry["error"] = "unreachable during adjustment"
            return entry

        nodes = await asyncio.gather(*(adjust(r) for r in readings))
        before = [n["skew_before_ms"] for n in nodes if n["skew_before_ms"] is not None]
        after = [n["skew_after_ms"] for n in nodes if n.get("skew_after_ms") is not None]
        record = {
            "algorithm": "berkeley", "daemon": me, "run_id": run_id, "nodes": nodes,
            "participants": len(readings), "used_in_average": len(used),
            "average_offset_ms": round(average, 3),
            "spread_before_ms": round(max(before) - min(before), 3) if before else None,
            "spread_after_ms": round(max(after) - min(after), 3) if after else None,
            "max_abs_skew_before_ms": round(max(abs(x) for x in before), 3) if before else None,
            "max_abs_skew_after_ms": round(max(abs(x) for x in after), 3) if after else None,
            "at": time.time(),
        }
        self.node.transport.local_event("BERKELEY_DONE", algo="berkeley", run_id=run_id,
                                        detail={k: record[k] for k in ("spread_before_ms", "spread_after_ms", "participants")})
        return self._remember(record)

    async def _on_poll(self, env: Dict[str, Any]) -> Dict[str, Any]:
        return {"clock_reading": self.node.physical.now(), "true_skew_ms": self.node.physical.skew_ms(),
                "_reply_type": "TIME_REPLY"}

    async def _on_adjust(self, env: Dict[str, Any]) -> Dict[str, Any]:
        delta_ms = float(env.get("payload", {}).get("delta_ms", 0.0))
        before = self.node.physical.skew_ms()
        self.node.physical.adjust(delta_ms / 1000.0)
        self.node.transport.local_event("CLOCK_ADJUSTED", algo="berkeley", run_id=env.get("run_id"),
                                        detail={"adjustment_ms": round(delta_ms, 3), "skew_before_ms": round(before, 3),
                                                "skew_after_ms": round(self.node.physical.skew_ms(), 3)})
        return {"true_skew_ms": self.node.physical.skew_ms(), "_reply_type": "TIME_ADJUSTED"}
