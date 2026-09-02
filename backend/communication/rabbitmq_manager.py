import json
import asyncio
import logging
import time
from typing import Dict, Any, List, Callable

logger = logging.getLogger(__name__)

class RabbitMQManager:
    """
    Manages Message-Oriented Communication via RabbitMQ.
    If RabbitMQ is not available locally, automatically falls back to an async in-memory event bus
    so the system remains 100% functional on local PC.
    """
    def __init__(self, rabbitmq_url: str):
        self.url = rabbitmq_url
        self.connected = False
        self.in_memory_queue: asyncio.Queue = asyncio.Queue()
        self.listeners: List[Callable[[Dict[str, Any]], None]] = []
        self.published_message_count = 0
        self.consumed_message_count = 0
        self._connection = None
        self._channel = None

    async def connect(self):
        try:
            import aio_pika
            self._connection = await aio_pika.connect_robust(self.url, timeout=3.0)
            self._channel = await self._connection.channel()
            
            # Declare telemetry & events exchanges/queues
            await self._channel.declare_exchange("telemetry.exchange", type="fanout")
            queue = await self._channel.declare_queue("telemetry.queue", durable=True)
            await queue.bind("telemetry.exchange")
            
            self.connected = True
            logger.info("Connected to RabbitMQ server successfully.")
            
            # Start background consuming loop
            asyncio.create_task(self._start_consumer(queue))
        except Exception as e:
            logger.warning(f"RabbitMQ server not reachable ({e}). Operating in resilient In-Memory Fallback Queue mode.")
            self.connected = False
            asyncio.create_task(self._start_in_memory_consumer())

    async def publish_telemetry(self, telemetry_data: Dict[str, Any]):
        self.published_message_count += 1
        payload = {
            "message_id": f"msg-{self.published_message_count}-{int(time.time()*1000)}",
            "type": "TELEMETRY",
            "producer": telemetry_data.get("satellite_id", "SAT-UNKNOWN"),
            "data": telemetry_data,
            "timestamp": time.time(),
            "broker_mode": "RABBITMQ" if self.connected else "IN_MEMORY_EVENT_BUS"
        }
        
        if self.connected and self._channel:
            try:
                import aio_pika
                exchange = await self._channel.get_exchange("telemetry.exchange")
                message = aio_pika.Message(
                    body=json.dumps(payload).encode(),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                )
                await exchange.publish(message, routing_key="")
                return payload
            except Exception as ex:
                logger.error(f"Error publishing to RabbitMQ: {ex}")
        
        # Fallback to in-memory async queue
        await self.in_memory_queue.put(payload)
        return payload

    async def register_listener(self, callback: Callable[[Dict[str, Any]], None]):
        self.listeners.append(callback)

    async def _notify_listeners(self, message_payload: Dict[str, Any]):
        self.consumed_message_count += 1
        for listener in self.listeners:
            try:
                if asyncio.iscoroutinefunction(listener):
                    await listener(message_payload)
                else:
                    listener(message_payload)
            except Exception as err:
                logger.error(f"Error in telemetry consumer listener: {err}")

    async def _start_consumer(self, queue):
        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    data = json.loads(message.body.decode())
                    await self._notify_listeners(data)

    async def _start_in_memory_consumer(self):
        while True:
            payload = await self.in_memory_queue.get()
            await self._notify_listeners(payload)
            self.in_memory_queue.task_done()
