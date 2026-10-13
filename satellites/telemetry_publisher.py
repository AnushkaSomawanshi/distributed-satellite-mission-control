"""
Satellite-side telemetry publisher (Message-Oriented Communication).

Each satellite publishes its telemetry directly to the RabbitMQ fanout exchange
`telemetry.exchange`. Mission Control consumes from `telemetry.queue`, so producer and
consumer are fully decoupled: neither knows the other's address.

If no broker is reachable (e.g. a local run without Docker), the satellite falls back to
POSTing the sample to Mission Control's `/api/telemetry/ingest` bridge. That sample still
goes through Mission Control's message bus and consumer, but it is labelled
`broker_mode = IN_MEMORY_EVENT_BUS` so nothing claims RabbitMQ carried it.
The publisher keeps retrying the broker in the background and switches back automatically.
"""

import json
import time
import logging
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger("TelemetryPublisher")

EXCHANGE_NAME = "telemetry.exchange"
BROKER_RETRY_SECONDS = 15.0


class TelemetryPublisher:
    def __init__(self, satellite_id: str, rabbitmq_url: Optional[str], registry_url: str):
        self.satellite_id = satellite_id
        self.rabbitmq_url = rabbitmq_url
        self.registry_url = registry_url.rstrip("/")
        self._connection = None
        self._channel = None
        self._exchange = None
        self._last_connect_attempt = 0.0
        self.published_via_broker = 0
        self.published_via_fallback = 0
        self.failed_publishes = 0

    @property
    def broker_connected(self) -> bool:
        return self._exchange is not None and self._connection is not None and not self._connection.is_closed

    async def _ensure_broker(self) -> bool:
        if self.broker_connected:
            return True
        if not self.rabbitmq_url:
            return False
        now = time.time()
        if now - self._last_connect_attempt < BROKER_RETRY_SECONDS:
            return False
        self._last_connect_attempt = now
        try:
            import aio_pika  # imported lazily so local runs work without the package
            self._connection = await aio_pika.connect_robust(self.rabbitmq_url, timeout=3.0)
            self._channel = await self._connection.channel()
            # Must match the declaration in backend/communication/rabbitmq_manager.py
            self._exchange = await self._channel.declare_exchange(EXCHANGE_NAME, type="fanout")
            logger.info(f"[{self.satellite_id}] Connected to RabbitMQ; publishing telemetry to '{EXCHANGE_NAME}'")
            return True
        except Exception as exc:
            self._connection = self._channel = self._exchange = None
            logger.warning(
                f"[{self.satellite_id}] RabbitMQ unreachable ({exc.__class__.__name__}: {exc}); "
                f"using HTTP fallback, retrying broker in {BROKER_RETRY_SECONDS:.0f}s"
            )
            return False

    def _envelope(self, telemetry: Dict[str, Any], broker_mode: str) -> Dict[str, Any]:
        seq = telemetry.get("sequence_number", 0)
        return {
            "message_id": f"{self.satellite_id}-{seq}-{int(time.time() * 1000)}",
            "type": "TELEMETRY",
            "producer": self.satellite_id,
            "data": telemetry,
            "timestamp": time.time(),
            "broker_mode": broker_mode,
        }

    async def publish(self, telemetry: Dict[str, Any]) -> str:
        """Publish one telemetry sample. Returns the path used: RABBITMQ, HTTP_FALLBACK or FAILED."""
        if await self._ensure_broker():
            try:
                import aio_pika
                body = json.dumps(self._envelope(telemetry, "RABBITMQ")).encode()
                await self._exchange.publish(aio_pika.Message(body=body, content_type="application/json"), routing_key="")
                self.published_via_broker += 1
                return "RABBITMQ"
            except Exception as exc:
                logger.warning(f"[{self.satellite_id}] RabbitMQ publish failed ({exc}); falling back to HTTP")
                self._exchange = None

        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.post(f"{self.registry_url}/api/telemetry/ingest", json=telemetry)
            if resp.status_code == 200:
                self.published_via_fallback += 1
                return "HTTP_FALLBACK"
            logger.warning(f"[{self.satellite_id}] Telemetry fallback rejected: HTTP {resp.status_code} {resp.text[:200]}")
        except Exception as exc:
            logger.debug(f"[{self.satellite_id}] Telemetry fallback failed: {exc}")
        self.failed_publishes += 1
        return "FAILED"

    def stats(self) -> Dict[str, Any]:
        return {
            "broker_connected": self.broker_connected,
            "published_via_broker": self.published_via_broker,
            "published_via_fallback": self.published_via_fallback,
            "failed_publishes": self.failed_publishes,
        }

    async def close(self):
        if self._connection is not None:
            try:
                await self._connection.close()
            except Exception:
                pass
