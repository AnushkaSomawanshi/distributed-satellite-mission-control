import time
import random
import threading
from typing import Dict, Any, Optional

_lock = threading.Lock()
_event_counter = random.randint(100, 999)

def generate_correlation_id(prefix: str = "EVT") -> str:
    """
    Generates unified distributed event correlation ID in format:
    EVT-YYYYMMDD-XXXXX (e.g. EVT-20260906-00482)
    """
    global _event_counter
    with _lock:
        _event_counter += 1
        cnt = _event_counter
    date_str = time.strftime("%Y%m%d", time.gmtime())
    return f"{prefix}-{date_str}-{cnt:05d}"

def create_event(
    event_type: str,
    source: str,
    destination: str,
    protocol: str,
    message: str,
    correlation_id: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
    status: str = "SUCCESS",
    latency_ms: float = 0.0
) -> Dict[str, Any]:
    """
    Creates a standardized distributed event dictionary.
    """
    cid = correlation_id or generate_correlation_id()
    now = time.time()
    return {
        "event_id": cid,
        "correlation_id": cid,
        "event_type": event_type,
        "source": source,
        "destination": destination,
        "protocol": protocol,
        "message": message,
        "status": status,
        "latency_ms": round(latency_ms, 2),
        "payload": payload or {},
        "timestamp": now,
        "formatted_time": time.strftime("%H:%M:%S", time.localtime(now))
    }
