import json
import os
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
        self.event_listeners: List[Callable[[Dict[str, Any]], Any]] = []  # FA-2 algorithm events
        self.event_batches_consumed = 0
        self.mission_listeners: List[Callable[[Dict[str, Any]], Any]] = []  # Unit 4 mission event bus
        # Every Mission Control replica gets its OWN queues on the fanout exchanges, so a standby
        # replica receives every message too instead of splitting the stream with the primary.
        instance = os.getenv("MC_INSTANCE", "primary")
        self.suffix = "" if instance == "primary" else f".{instance}"
        self.published_message_count = 0
        self.consumed_message_count = 0
        self.consumed_by_producer: Dict[str, int] = {}
        self.consumed_by_broker_mode: Dict[str, int] = {}
        self._connection = None
        self._channel = None

    async def connect(self):
        try:
            import aio_pika
            self._connection = await aio_pika.connect_robust(self.url, timeout=3.0)
            self._channel = await self._connection.channel()
            
            # Declare telemetry & events exchanges/queues
            await self._channel.declare_exchange("telemetry.exchange", type="fanout")
            queue = await self._channel.declare_queue(f"telemetry.queue{self.suffix}", durable=True)
            await queue.bind("telemetry.exchange")

            # FA-2: satellites publish algorithm events (SEND/RECV/LOCAL) to their own fanout exchange
            await self._channel.declare_exchange("dsync.events", type="fanout")
            events_queue = await self._channel.declare_queue(f"dsync.events.queue{self.suffix}", durable=True)
            await events_queue.bind("dsync.events")

            # Unit 4: Mission Control's own events (FILE_UPLOADED, SNAPSHOT_COMPLETED) for the serverless runtime
            await self._channel.declare_exchange("mission.events", type="fanout")
            mission_queue = await self._channel.declare_queue(f"mission.events.queue{self.suffix}", durable=True)
            await mission_queue.bind("mission.events")

            self.connected = True
            logger.info("Connected to RabbitMQ server successfully.")
            
            # Start background consuming loop
            asyncio.create_task(self._start_consumer(queue))
            asyncio.create_task(self._start_event_consumer(events_queue))
            asyncio.create_task(self._start_mission_consumer(mission_queue))
        except Exception as e:
            logger.warning(f"RabbitMQ server not reachable ({e}). Operating in resilient In-Memory Fallback Queue mode.")
            self.connected = False
            asyncio.create_task(self._start_in_memory_consumer())

    async def publish_telemetry(self, telemetry_data: Dict[str, Any]):
        self.published_message_count += 1
        producer = telemetry_data.get("satellite_id", "SAT-UNKNOWN")
        msg_id = f"msg-{self.published_message_count}-{int(time.time()*1000)}"
        payload = {
            "message_id": msg_id,
            "type": "TELEMETRY",
            "producer": producer,
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
                logger.info(f"[RABBITMQ PUBLISH] producer={producer} | exchange=telemetry.exchange | msg_id={msg_id} | status=SENT")
                return payload
            except Exception as ex:
                logger.error(f"[RABBITMQ ERROR] Failed to publish message to RabbitMQ: {ex}")
        
        # Fallback to in-memory async queue
        logger.info(f"[RABBITMQ PUBLISH IN-MEMORY] producer={producer} | queue=in_memory_event_bus | msg_id={msg_id} | status=QUEUED")
        await self.in_memory_queue.put(payload)
        return payload

    async def register_listener(self, callback: Callable[[Dict[str, Any]], None]):
        self.listeners.append(callback)

    async def register_event_listener(self, callback: Callable[[Dict[str, Any]], Any]):
        self.event_listeners.append(callback)

    async def register_mission_listener(self, callback: Callable[[Dict[str, Any]], Any]):
        self.mission_listeners.append(callback)

    async def publish_mission_event(self, event: Dict[str, Any]) -> bool:
        if not (self.connected and self._channel):
            return False
        try:
            import aio_pika
            exchange = await self._channel.get_exchange("mission.events")
            await exchange.publish(aio_pika.Message(body=json.dumps(event, default=str).encode()), routing_key="")
            return True
        except Exception as ex:
            logger.warning(f"[RABBITMQ MISSION EVENT] publish failed: {ex}")
            return False

    async def _start_mission_consumer(self, queue):
        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    try:
                        data = json.loads(message.body.decode())
                    except (ValueError, UnicodeDecodeError):
                        continue
                    for cb in self.mission_listeners:
                        try:
                            await cb(data)
                        except Exception as err:
                            logger.error(f"[RABBITMQ MISSION EVENT] listener failed: {err}")

    async def _start_event_consumer(self, queue):
        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    try:
                        data = json.loads(message.body.decode())
                    except (ValueError, UnicodeDecodeError) as err:
                        logger.warning(f"[RABBITMQ EVENTS] Dropping undecodable message: {err}")
                        continue
                    self.event_batches_consumed += 1
                    for cb in self.event_listeners:
                        try:
                            await cb(data)
                        except Exception as err:
                            logger.error(f"[RABBITMQ EVENTS] listener failed: {err}")

    async def _notify_listeners(self, message_payload: Dict[str, Any]):
        self.consumed_message_count += 1
        producer = message_payload.get("producer") or message_payload.get("data", {}).get("satellite_id", "SAT-UNKNOWN")
        msg_id = message_payload.get("message_id", "UNKNOWN")
        broker_mode = message_payload.get("broker_mode", "UNKNOWN")
        self.consumed_by_producer[producer] = self.consumed_by_producer.get(producer, 0) + 1
        self.consumed_by_broker_mode[broker_mode] = self.consumed_by_broker_mode.get(broker_mode, 0) + 1
        logger.info(f"[RABBITMQ CONSUME] consumer=Mission Control | producer={producer} | mode={broker_mode} | msg_id={msg_id} | status=RECEIVED")
        for listener in self.listeners:
            try:
                if asyncio.iscoroutinefunction(listener):
                    await listener(message_payload)
                else:
                    listener(message_payload)
            except Exception as err:
                logger.error(f"[RABBITMQ CONSUMER ERROR] Exception in consumer callback: {err}")

    async def _start_consumer(self, queue):
        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    try:
                        data = json.loads(message.body.decode())
                    except (ValueError, UnicodeDecodeError) as err:
                        logger.warning(f"[RABBITMQ CONSUME] Dropping undecodable message: {err}")
                        continue
                    await self._notify_listeners(data)

    async def _start_in_memory_consumer(self):
        while True:
            payload = await self.in_memory_queue.get()
            await self._notify_listeners(payload)
            self.in_memory_queue.task_done()
