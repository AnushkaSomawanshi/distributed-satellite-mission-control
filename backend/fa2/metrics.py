"""
Measured metrics for the Algorithm Arena, computed only from events the satellites reported.
Nothing here is estimated or hardcoded: if an event is missing, the metric says so.
"""

from typing import Any, Dict, List, Optional, Tuple


def _sends(events: List[Dict[str, Any]], algos: Optional[set] = None) -> List[Dict[str, Any]]:
    return [e for e in events if e.get("kind") == "SEND" and (algos is None or e.get("algo") in algos)]


def _count_by_type(sends: List[Dict[str, Any]]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for e in sends:
        out[e.get("msg_type", "?")] = out.get(e.get("msg_type", "?"), 0) + 1
    return dict(sorted(out.items()))


def cs_intervals(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    opened: Dict[str, Dict[str, Any]] = {}
    intervals = []
    for e in sorted(events, key=lambda e: e.get("true_ts", 0)):
        label = e.get("label")
        if label == "CS_ENTER":
            opened[e["node"]] = e
        elif label == "CS_EXIT" and e["node"] in opened:
            start = opened.pop(e["node"])
            detail = start.get("detail") or {}
            intervals.append({"node": e["node"], "enter": start["true_ts"], "exit": e["true_ts"],
                              "request_lamport": detail.get("request_lamport"), "wait_ms": detail.get("wait_ms")})
    return intervals


def mutex_metrics(events: List[Dict[str, Any]], algo: str) -> Dict[str, Any]:
    intervals = cs_intervals(events)
    entries = len(intervals)
    sends = _sends(events, {algo})
    delivered = [e for e in sends if e.get("delivered", True)]

    ordered = sorted(intervals, key=lambda i: i["enter"])
    overlaps = []
    for a, b in zip(ordered, ordered[1:]):
        if b["enter"] < a["exit"]:
            overlaps.append({"first": a["node"], "second": b["node"], "overlap_ms": round((a["exit"] - b["enter"]) * 1000, 3)})

    # Fairness: when a satellite enters, was an OLDER request (smaller Lamport, ID) still waiting?
    requests: Dict[Tuple[str, int], float] = {}
    for e in events:
        if e.get("label") == "CS_REQUEST":
            requests[(e["node"], e["lamport"])] = e["true_ts"]
    inversions = 0
    for ent in ordered:
        mine = (ent["request_lamport"], ent["node"])
        for other in ordered:
            theirs = (other["request_lamport"], other["node"])
            asked = requests.get((other["node"], other["request_lamport"]))
            if asked is not None and theirs < mine and asked < ent["enter"] < other["enter"]:
                inversions += 1
                break
    waits = [i["wait_ms"] for i in intervals if i["wait_ms"] is not None]
    first = min((e["true_ts"] for e in events), default=None)
    last = max((e["true_ts"] for e in events), default=None)
    return {
        "algorithm": algo,
        "entries": entries,
        "messages": len(sends),
        "messages_delivered": len(delivered),
        "messages_per_entry": round(len(sends) / entries, 2) if entries else None,
        "messages_by_type": _count_by_type(sends),
        "avg_wait_ms": round(sum(waits) / len(waits), 2) if waits else None,
        "max_wait_ms": round(max(waits), 2) if waits else None,
        "safety_violations": overlaps,
        "fairness_inversions": inversions,
        "duration_ms": round((last - first) * 1000, 2) if first and last else None,
        "entry_order": [{"node": i["node"], "request_lamport": i["request_lamport"]} for i in ordered],
    }


def election_metrics(events: List[Dict[str, Any]], algo_filter: Optional[set] = None) -> Dict[str, Any]:
    algos = algo_filter or {"bully", "ring"}
    relevant = [e for e in events if e.get("algo") in algos]
    sends = _sends(relevant)
    starts = [e for e in relevant if e.get("label") == "ELECTION_START"]
    decided = [e for e in relevant if e.get("label") in ("LEADER_ELECTED", "LEADER_ACCEPTED")]
    winner = next((e.get("detail", {}).get("leader") for e in sorted(decided, key=lambda e: e["true_ts"])
                   if e.get("label") == "LEADER_ELECTED"), None)
    t0 = min((e["true_ts"] for e in starts), default=None)
    t1 = max((e["true_ts"] for e in decided), default=None)
    return {
        "messages": len(sends),
        "messages_by_type": _count_by_type(sends),
        "election_starts": len(starts),
        "initiators": sorted({e["node"] for e in starts}),
        "winner": winner,
        "event_duration_ms": round((t1 - t0) * 1000, 2) if t0 and t1 else None,
        "skipped_dead_successors": sum(1 for e in relevant if e.get("label") == "RING_SKIP"),
    }
