"""
Serverless function bodies (Unit 4). Each runs inside its own worker PROCESS started by the runtime
(backend/fa2/serverless.py). Functions are pure: they get the triggering event plus prepared input,
and return a JSON result that the runtime stores in OrbitFS. No network or disk access in here.
"""

import base64
import hashlib
import math
import os
import struct
import time
from collections import Counter
from typing import Any, Dict


def incident_report(event: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Triggered when satellites declare a peer DEAD: assemble an incident report from their events."""
    peer = event.get("detail", {}).get("peer") or event.get("peer")
    events = sorted(ctx.get("events", []), key=lambda e: e.get("true_ts", 0))
    detections = [e for e in events if e.get("label") == "PEER_DEAD" and (e.get("detail") or {}).get("peer") == peer]
    leaders = [e for e in events if e.get("label") == "LEADER_ELECTED"]
    moved = [e.get("detail") for e in events if e.get("label") == "TASK_REASSIGNED" and (e.get("detail") or {}).get("from") == peer]
    first = detections[0]["true_ts"] if detections else event.get("at")
    lines = [f"{peer} declared DEAD by {len(detections)} satellite(s) via beacons."]
    if leaders:
        lines.append("New leader elected: " + ", ".join(sorted({(e.get('detail') or {}).get('leader') for e in leaders})) + ".")
    if moved:
        lines.append("Tasks taken over: " + ", ".join(f"{m['task_id']}->{m['to']}" for m in moved) + ".")
    return {
        "incident": f"INC-{peer}-{int(first or time.time())}",
        "failed_satellite": peer,
        "detected_by": sorted({e["node"] for e in detections}),
        "first_detection_at": first,
        "leaders_elected": sorted({(e.get("detail") or {}).get("leader") for e in leaders}),
        "tasks_reassigned": moved,
        "summary": " ".join(lines),
        "evidence_events": len(events),
        "generated_by_pid": os.getpid(),
    }


def _png_size(data: bytes):
    if data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) >= 24:
        return struct.unpack(">II", data[16:24])
    return None


def _jpeg_size(data: bytes):
    if data[:2] != b"\xff\xd8":
        return None
    i = 2
    while i + 9 < len(data):
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker in (0xC0, 0xC1, 0xC2):
            h, w = struct.unpack(">HH", data[i + 5:i + 9])
            return w, h
        seg = struct.unpack(">H", data[i + 2:i + 4])[0]
        i += 2 + seg
    return None


def image_stats(event: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Triggered when an image is uploaded to OrbitFS under images/: format, size, entropy."""
    data = base64.b64decode(ctx["data_b64"])
    counts = Counter(data)
    n = len(data) or 1
    entropy = -sum((c / n) * math.log2(c / n) for c in counts.values())
    size = _png_size(data) or _jpeg_size(data)
    fmt = "PNG" if data[:8] == b"\x89PNG\r\n\x1a\n" else "JPEG" if data[:2] == b"\xff\xd8" else \
        "GIF" if data[:3] == b"GIF" else "unknown"
    return {
        "path": event.get("path"), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
        "format": fmt, "width": size[0] if size else None, "height": size[1] if size else None,
        "entropy_bits_per_byte": round(entropy, 3),
        "looks_compressed": entropy > 7.5,
        "generated_by_pid": os.getpid(),
    }


def snapshot_audit(event: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Triggered after every Chandy-Lamport snapshot: re-check the invariant independently."""
    snap = ctx.get("snapshot") or {}
    seen = [t["task_id"] for t in snap.get("tasks_on_satellites", [])] + \
           [t["task_id"] for t in snap.get("tasks_in_transit", [])]
    expected = set(ctx.get("expected_tasks", []))
    counts = Counter(seen)
    holds = set(counts) == expected and all(v == 1 for v in counts.values())
    claimed = (snap.get("consistency") or {}).get("holds")
    return {
        "snapshot_id": snap.get("snapshot_id"), "independent_check_holds": holds,
        "agrees_with_mission_control": holds == claimed,
        "task_counts": dict(counts), "channels_with_messages": sum(1 for v in (snap.get("channel_states") or {}).values() if v),
        "generated_by_pid": os.getpid(),
    }


HANDLERS = {"incident_report": incident_report, "image_stats": image_stats, "snapshot_audit": snapshot_audit}


def worker_main(name: str, conn) -> None:
    """Entry point of one function instance (a separate process)."""
    handler = HANDLERS[name]
    conn.send({"ready": True, "pid": os.getpid()})
    while True:
        job = conn.recv()
        if job is None:
            break
        started = time.time()
        try:
            out = handler(job["event"], job.get("input") or {})
            conn.send({"ok": True, "result": out, "exec_ms": round((time.time() - started) * 1000, 2)})
        except Exception as exc:  # report, keep the instance alive
            conn.send({"ok": False, "error": f"{exc.__class__.__name__}: {exc}"})
