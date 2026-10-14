"""
Event log of one satellite.

Every tracked message send/receive and every algorithm milestone becomes an event stamped with
the satellite's Lamport clock, vector clock, its own (possibly skewed) physical clock and the true
time. Events are kept locally (so nothing is lost while Mission Control is unreachable) and shipped
in batches to Mission Control through a pluggable async sink (RabbitMQ, or HTTP fallback).
"""

import asyncio
import logging
import time
import uuid
from collections import deque
from typing import Any, Awaitable, Callable, Deque, Dict, List, Optional

logger = logging.getLogger("dsync.events")

Sink = Callable[[List[Dict[str, Any]]], Awaitable[bool]]


class EventReporter:
    def __init__(self, node_id: str, sink: Optional[Sink] = None, keep: int = 5000, max_pending: int = 20000):
        self.node_id = node_id
        self.sink = sink
        self.boot_id = uuid.uuid4().hex[:6]   # event IDs stay unique across process restarts
        self.seq = 0
        self.local: Deque[Dict[str, Any]] = deque(maxlen=keep)   # recent history, served at /dsync/events
        self.pending: Deque[Dict[str, Any]] = deque(maxlen=max_pending)  # not yet delivered to Mission Control
        self.delivered = 0
        self.dropped_unsent = 0
        self.listeners: List[Callable[[Dict[str, Any]], None]] = []

    def record(self, event: Dict[str, Any]) -> Dict[str, Any]:
        self.seq += 1
        event.setdefault("event_id", f"{self.node_id}-{self.boot_id}-{self.seq}")
        event["boot_id"] = self.boot_id
        event["node"] = self.node_id
        event["seq"] = self.seq
        if len(self.pending) == self.pending.maxlen:
            self.dropped_unsent += 1
        self.local.append(event)
        self.pending.append(event)
        for listener in self.listeners:
            try:
                listener(event)
            except Exception as exc:  # pragma: no cover
                logger.debug("event listener failed: %s", exc)
        return event

    def since(self, seq: int = 0, limit: int = 500) -> List[Dict[str, Any]]:
        return [e for e in self.local if e["seq"] > seq][:limit]

    async def flush(self) -> int:
        if not self.sink or not self.pending:
            return 0
        batch = list(self.pending)[:500]
        try:
            ok = await self.sink(batch)
        except Exception as exc:
            logger.debug("event sink failed: %s", exc)
            ok = False
        if ok:
            for _ in batch:
                self.pending.popleft()
            self.delivered += len(batch)
            return len(batch)
        return 0

    async def run(self, interval: float = 0.25) -> None:
        while True:
            try:
                await self.flush()
            except asyncio.CancelledError:
                break
            except Exception as exc:  # pragma: no cover
                logger.warning("event flush loop error: %s", exc)
            await asyncio.sleep(interval)

    def stats(self) -> Dict[str, Any]:
        return {
            "recorded": self.seq,
            "delivered": self.delivered,
            "pending": len(self.pending),
            "dropped_unsent": self.dropped_unsent,
        }


def now_true() -> float:
    return time.time()
