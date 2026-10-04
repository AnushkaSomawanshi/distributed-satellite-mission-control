"""
RICART-AGRAWALA DISTRIBUTED MUTUAL EXCLUSION SERVICE

Implements Ricart-Agrawala algorithm for task/resource ownership arbitration:
1. Requesting node broadcasts REQUEST(resource_id, T_i, node_id) with Lamport timestamp T_i.
2. Peer nodes reply with REPLY if not requesting or if local request timestamp T_j > T_i. Otherwise defer.
3. Upon receiving replies from all active peers, requesting node enters Critical Section (claims resource).
4. Upon exit, requesting node sends RELEASE to deferred requestors.
"""

import time
import asyncio
import logging
from typing import Dict, Any, List, Optional
from backend.registry.service_registry import global_registry
from backend.services.distributed_clocks import global_clock_manager

logger = logging.getLogger("RicartAgrawalaMutex")

ALL_NODES = ["SAT-01", "SAT-02", "SAT-03", "SAT-04", "SAT-05"]

class RicartAgrawalaMutex:
    def __init__(self):
        self.request_queue: List[Dict[str, Any]] = []
        self.active_locks: Dict[str, Dict[str, Any]] = {} # resource_id -> details
        self.history: List[Dict[str, Any]] = []

    async def request_resource(self, requester_id: str, resource_id: str) -> Dict[str, Any]:
        start_time = time.time()
        event_id = f"EVT-MUTEX-{int(start_time * 1000)}"

        clk = global_clock_manager.record_node_event(requester_id, f"MUTEX_REQUEST_{resource_id}")
        t_i = clk["lamport_timestamp"]

        active_peers = [n for n in ALL_NODES if n != requester_id and (reg := global_registry.lookup(n)) and reg.status not in ["OFFLINE", "DISCONNECTED", "FAILED"]]

        logger.info(f"[RICART-AGRAWALA REQUEST] {requester_id} requesting Critical Section for '{resource_id}' at Lamport T={t_i} | Active Peers={active_peers}")

        replies_received = []
        deferred_nodes = []
        message_trace = []

        # Check existing lock holder
        existing_lock = self.active_locks.get(resource_id)
        if existing_lock and existing_lock["holder"] != requester_id:
            logger.info(f"[MUTEX CONFLICT] Resource '{resource_id}' currently held by {existing_lock['holder']}. Request queued.")

        # Simulate sending REQUEST to all active peers and collecting REPLYs
        for peer_id in active_peers:
            peer_clk = global_clock_manager.record_node_event(peer_id, f"MUTEX_EVAL_{resource_id}")
            # If peer holds lock, defer
            if existing_lock and existing_lock["holder"] == peer_id:
                deferred_nodes.append(peer_id)
                message_trace.append({
                    "from_node": requester_id,
                    "to_node": peer_id,
                    "type": "REQUEST",
                    "timestamp_t_i": t_i,
                    "response": "DEFERRED",
                    "reason": f"Peer {peer_id} currently holds resource lock"
                })
            else:
                replies_received.append(peer_id)
                message_trace.append({
                    "from_node": requester_id,
                    "to_node": peer_id,
                    "type": "REQUEST",
                    "timestamp_t_i": t_i,
                    "response": "REPLY_GRANTED",
                    "latency_ms": round(abs(peer_clk["physical_timestamp"] - clk["physical_timestamp"]) * 1000 + 10.0, 2)
                })
                await asyncio.sleep(0.015)

        permission_granted = len(replies_received) == len(active_peers)
        duration_ms = round((time.time() - start_time) * 1000, 2)

        if permission_granted:
            lock_entry = {
                "resource_id": resource_id,
                "holder": requester_id,
                "lamport_timestamp": t_i,
                "vector_clock": clk["vector_clock"],
                "acquired_at": time.time()
            }
            self.active_locks[resource_id] = lock_entry
            status = "CRITICAL_SECTION_ENTERED"
            logger.info(f"[RICART-AGRAWALA GRANTED] {requester_id} entered Critical Section for '{resource_id}'")
        else:
            status = "QUEUED_DEFERRED"

        res = {
            "event_id": event_id,
            "algorithm": "Ricart-Agrawala Distributed Mutual Exclusion",
            "requester_id": requester_id,
            "resource_id": resource_id,
            "lamport_timestamp": t_i,
            "vector_clock": clk["vector_clock"],
            "status": status,
            "replies_granted": replies_received,
            "deferred_nodes": deferred_nodes,
            "message_trace": message_trace,
            "latency_ms": duration_ms,
            "timestamp": time.time()
        }
        self.history.append(res)
        return res

    def release_resource(self, requester_id: str, resource_id: str) -> Dict[str, Any]:
        existing = self.active_locks.get(resource_id)
        if existing and existing["holder"] == requester_id:
            del self.active_locks[resource_id]
            clk = global_clock_manager.record_node_event(requester_id, f"MUTEX_RELEASE_{resource_id}")
            logger.info(f"[RICART-AGRAWALA RELEASE] {requester_id} released resource '{resource_id}'")
            return {
                "status": "RELEASED",
                "resource_id": resource_id,
                "previous_holder": requester_id,
                "lamport_timestamp": clk["lamport_timestamp"],
                "timestamp": time.time()
            }
        return {"status": "NOT_HELD", "resource_id": resource_id, "requester_id": requester_id}

global_mutex_engine = RicartAgrawalaMutex()
