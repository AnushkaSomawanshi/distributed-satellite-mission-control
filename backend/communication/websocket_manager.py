import json
import time
import logging
from typing import List, Dict, Any
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

class ConnectionManager:
    """
    Manages active WebSocket connections for continuous telemetry stream broadcasting.
    """
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.total_messages_sent: int = 0
        self.start_time: float = time.time()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Total clients: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket client disconnected. Remaining clients: {len(self.active_connections)}")

    async def broadcast(self, data: Dict[str, Any]):
        if not self.active_connections:
            return

        self.total_messages_sent += 1
        payload_str = json.dumps(data)

        disconnected_clients = []
        for connection in self.active_connections:
            try:
                await connection.send_text(payload_str)
            except Exception as e:
                logger.warning(f"Failed to send to WebSocket client: {e}")
                disconnected_clients.append(connection)

        for client in disconnected_clients:
            self.disconnect(client)

    def get_stats(self) -> Dict[str, Any]:
        uptime = round(time.time() - self.start_time, 2)
        rate = round(self.total_messages_sent / max(1, uptime), 2)
        return {
            "active_clients": len(self.active_connections),
            "total_messages_sent": self.total_messages_sent,
            "uptime_seconds": uptime,
            "messages_per_second": rate
        }

websocket_manager = ConnectionManager()
