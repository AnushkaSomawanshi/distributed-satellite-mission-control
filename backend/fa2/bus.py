"""
Mission event bus. Mission Control events (FILE_UPLOADED, SNAPSHOT_COMPLETED, ...) are published to the
RabbitMQ fanout exchange `mission.events`; satellite algorithm events arrive on `dsync.events`.
Subscribers (the serverless runtime) receive both. Without a broker, events are dispatched in-process.
"""

import asyncio
import logging
import time
from typing import Any, Awaitable, Callable, Dict, List

logger = logging.getLogger("MissionBus")

Subscriber = Callable[[Dict[str, Any]], Awaitable[None]]


class MissionBus:
    def __init__(self):
        self.subscribers: List[Subscriber] = []
        self.rabbit = None
        self.published = 0
        self.dispatched = 0

    def subscribe(self, cb: Subscriber) -> None:
        self.subscribers.append(cb)

    async def publish(self, event_type: str, **data: Any) -> Dict[str, Any]:
        event = {"type": event_type, "source": "mission-control", "at": time.time(), **data}
        self.published += 1
        if self.rabbit is not None and self.rabbit.connected:
            if await self.rabbit.publish_mission_event(event):
                return event
        await self.dispatch(event)
        return event

    async def dispatch(self, event: Dict[str, Any]) -> None:
        self.dispatched += 1
        for cb in self.subscribers:
            asyncio.ensure_future(self._safe(cb, event))

    async def _safe(self, cb: Subscriber, event: Dict[str, Any]) -> None:
        try:
            await cb(event)
        except Exception as exc:  # pragma: no cover
            logger.warning("bus subscriber failed: %s", exc)


mission_bus = MissionBus()
