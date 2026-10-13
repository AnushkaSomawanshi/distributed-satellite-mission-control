"""
Mission Control's FA-2 event collector.

Satellites ship their algorithm events (SEND / RECV / LOCAL, each stamped with Lamport, vector,
physical and true time) over RabbitMQ (`dsync.events`) or the HTTP fallback. Mission Control only
stores and serves them; it never edits or invents events.
"""

import time
from collections import deque
from typing import Any, Callable, Deque, Dict, Iterable, List, Optional


class EventStore:
    def __init__(self, maxlen: int = 50_000):
        self.events: Deque[Dict[str, Any]] = deque(maxlen=maxlen)
        self.seen: set = set()
        self.received = 0
        self.duplicates = 0
        self.by_mode: Dict[str, int] = {}
        self.listeners: List[Callable[[List[Dict[str, Any]]], Any]] = []

    def add_many(self, events: Iterable[Dict[str, Any]], mode: str = "UNKNOWN") -> List[Dict[str, Any]]:
        fresh = []
        for e in events:
            eid = e.get("event_id")
            if not eid or eid in self.seen:
                self.duplicates += 1
                continue
            if len(self.seen) > self.events.maxlen * 2:
                self.seen = {x["event_id"] for x in self.events}
            self.seen.add(eid)
            e["collected_at"] = time.time()
            self.events.append(e)
            fresh.append(e)
        self.received += len(fresh)
        self.by_mode[mode] = self.by_mode.get(mode, 0) + len(fresh)
        return fresh

    def query(self, run_id: Optional[str] = None, algo: Optional[str] = None, since: Optional[float] = None,
              limit: int = 500, include_background: bool = False) -> List[Dict[str, Any]]:
        out = []
        for e in reversed(self.events):
            if run_id and e.get("run_id") != run_id:
                continue
            if algo and e.get("algo") not in algo.split(","):
                continue
            if since and e.get("true_ts", 0) < since:
                continue
            if not include_background and e.get("algo") == "beacon" and e.get("kind") != "LOCAL":
                continue
            out.append(e)
            if len(out) >= limit:
                break
        out.reverse()
        return out

    def for_run(self, run_id: str) -> List[Dict[str, Any]]:
        return [e for e in self.events if e.get("run_id") == run_id]

    def stats(self) -> Dict[str, Any]:
        return {"stored": len(self.events), "received": self.received, "duplicates": self.duplicates,
                "by_delivery_mode": dict(self.by_mode)}


event_store = EventStore()
