"""In-process network for tests: several DsyncNodes in one event loop, messages as JSON copies."""

import asyncio
import json
from typing import Any, Dict, Tuple


class InMemoryNetwork:
    def __init__(self, latency_s: float = 0.002):
        self.nodes: Dict[Tuple[str, int], Any] = {}
        self.latency_s = latency_s
        self.down: set = set()  # node ids whose process is "killed" (connection refused)

    def attach(self, node: Any, address: str, port: int) -> None:
        self.nodes[(address, port)] = node

    async def post(self, address: str, port: int, path: str, body: Dict[str, Any], timeout: float) -> Dict[str, Any]:
        node = self.nodes.get((address, port))
        if node is None or node.node_id in self.down:
            raise ConnectionError(f"connection refused {address}:{port}")
        await asyncio.sleep(self.latency_s)
        reply = await asyncio.wait_for(node.transport.receive(json.loads(json.dumps(body))), timeout)
        await asyncio.sleep(self.latency_s)
        return json.loads(json.dumps(reply))
