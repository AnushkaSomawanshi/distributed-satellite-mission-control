"""
BEACON PROTOCOL SERVICE

Extends heartbeat monitoring into an explicit FA-2 Beacon Protocol tracking:
BEACON, BEACON_ACK, BEACON_TIMEOUT, BEACON_SUSPECTED, BEACON_FAILED, BEACON_RECOVERED.

Distinguishes node failure vs network communication degradation:
- HEALTHY: Heartbeat age <= 5.0s
- DEGRADED: Latency/packet loss injected, but heartbeats arriving
- SUSPECTED: 5.0s < Heartbeat age <= 10.0s
- UNREACHABLE: Network partition blocking link
- FAILED / DISCONNECTED: Heartbeat age > 10.0s
- RECOVERING: First heartbeat arriving post-failure
"""

import time
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("BeaconService")

class BeaconTracker:
    def __init__(self):
        self.node_states: Dict[str, Dict[str, Any]] = {}

    def record_beacon(
        self,
        node_id: str,
        rtt_ms: float = 15.0,
        packet_loss_pct: float = 0.0,
        status: str = "HEALTHY"
    ) -> Dict[str, Any]:
        now = time.time()
        prev_state = self.node_states.get(node_id, {}).get("state", "UNKNOWN")

        if prev_state in ["SUSPECTED", "FAILED", "DISCONNECTED", "UNREACHABLE"]:
            current_state = "RECOVERING"
            logger.info(f"[BEACON STATE TRANSITION] Node {node_id}: {prev_state} -> RECOVERING")
        elif packet_loss_pct > 20.0 or rtt_ms > 200.0:
            current_state = "DEGRADED"
        else:
            current_state = "HEALTHY"

        rec = {
            "node_id": node_id,
            "state": current_state,
            "last_beacon_time": now,
            "rtt_ms": rtt_ms,
            "packet_loss_pct": packet_loss_pct,
            "missed_count": 0,
            "confidence": 1.0 if current_state == "HEALTHY" else 0.75
        }
        self.node_states[node_id] = rec
        return rec

    def get_beacon_status(self, node_id: str, heartbeat_age_seconds: float) -> Dict[str, Any]:
        rec = self.node_states.get(node_id, {
            "node_id": node_id,
            "state": "HEALTHY",
            "last_beacon_time": time.time() - heartbeat_age_seconds,
            "rtt_ms": 15.0,
            "packet_loss_pct": 0.0,
            "missed_count": 0,
            "confidence": 1.0
        })

        if heartbeat_age_seconds > 10.0:
            rec["state"] = "FAILED"
            rec["missed_count"] = int(heartbeat_age_seconds // 2)
            rec["confidence"] = 0.99
        elif heartbeat_age_seconds > 5.0:
            rec["state"] = "SUSPECTED"
            rec["missed_count"] = int(heartbeat_age_seconds // 2)
            rec["confidence"] = 0.65

        return rec

global_beacon_tracker = BeaconTracker()
