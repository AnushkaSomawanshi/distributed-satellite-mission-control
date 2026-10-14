"""
FA-2 Phase 3 Mission Control API: task ownership mirror, Chandy-Lamport snapshots, deadlock
scenarios and Ground Blackout Mode. As in Phase 1-2, satellites decide; Mission Control starts
experiments, mirrors state and checks results.
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, HTTPException

from backend.fa2.event_store import event_store
from backend.fa2.router import _responsive, _settle_events, call, call_all, get_status, states
from backend.fa2_extensions.catalog import MISSION_TASKS, SATELLITE_CAPABILITIES, TASKS_BY_ID

logger = logging.getLogger("FA2-Phase3")
router = APIRouter(prefix="/api/fa2", tags=["FA-2 phase 3"])

snapshot_history: List[Dict[str, Any]] = []
deadlock_runs: List[Dict[str, Any]] = []
blackout: Dict[str, Any] = {"active": False, "started_at": None, "ends_at": None, "history": []}

# Satellite-facing routes that a ground blackout makes unreachable (Mission Control keeps serving the UI).
SATELLITE_FACING = ("/api/satellites/heartbeat", "/api/satellites/register", "/api/telemetry/ingest",
                    "/api/fa2/events", "/api/fa2/time")


def blackout_blocks(path: str, method: str) -> bool:
    if not blackout["active"]:
        return False
    if blackout["ends_at"] and time.time() >= blackout["ends_at"]:
        _end_blackout("timer")
        return False
    return any(path.startswith(p) for p in SATELLITE_FACING) and not (path == "/api/fa2/events" and method == "GET")


def _end_blackout(how: str) -> None:
    if blackout["active"]:
        blackout["history"].append({"started_at": blackout["started_at"], "ended_at": time.time(), "ended_by": how})
        blackout.update({"active": False, "ends_at": None})


# ------------------------------------------------------------------ tasks (owned by satellites)
def tasks_from_states(st: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    owners: Dict[str, List[Dict[str, Any]]] = {}
    for sid, s in st.items():
        if s.get("unreachable"):
            continue
        for t in (s.get("tasks") or {}).get("owned", []):
            owners.setdefault(t["task_id"], []).append({"owner": sid, "version": t["version"], "silent": s.get("silent")})
    rows = []
    for t in MISSION_TASKS:
        held = sorted(owners.get(t["task_id"], []), key=lambda x: -x["version"])
        live = [h for h in held if not h["silent"]]
        current = live[0] if live else (held[0] if held else None)
        status = "RUNNING" if live else ("OWNER_SILENT" if held else "IN_TRANSIT_OR_UNASSIGNED")
        if len(live) > 1:
            status = "DUPLICATE_PENDING_FENCING"
        rows.append({**{k: v for k, v in t.items() if k != "initial_owner"},
                     "current_owner": current["owner"] if current else None,
                     "version": current["version"] if current else None,
                     "holders": held, "status": status})
    return {"tasks": rows, "capabilities_map": SATELLITE_CAPABILITIES}


def mirror_into_db(rows: List[Dict[str, Any]]) -> None:
    """Keep Mission Control's task table (used by impact analysis / incidents) equal to the satellites' truth."""
    try:
        from backend.services.task_manager import global_task_manager
        for r in rows:
            if r["current_owner"]:
                global_task_manager.mirror(r["task_id"], r["current_owner"], r["status"], r["version"])
    except Exception as exc:  # pragma: no cover
        logger.debug("task mirror failed: %s", exc)


async def task_mirror_loop() -> None:
    while True:
        await asyncio.sleep(5.0)
        try:
            st = await states()
            if any(not s.get("unreachable") for s in st.values()):
                mirror_into_db(tasks_from_states(st)["tasks"])
        except asyncio.CancelledError:
            break
        except Exception as exc:  # pragma: no cover
            logger.debug("task mirror loop: %s", exc)


@router.get("/tasks")
async def tasks():
    st = await states()
    out = tasks_from_states(st)
    leader = (await get_status())["agreed_leader"]
    out["leader"] = leader
    out["traffic"] = any(((s.get("tasks") or {}).get("traffic")) for s in st.values() if not s.get("unreachable"))
    out["recent_reassignments"] = ((st.get(leader) or {}).get("tasks") or {}).get("recent_reassignments", []) if leader else []
    out["source"] = "satellites"
    return out


@router.post("/tasks/traffic")
async def tasks_traffic(body: Dict[str, Any] = Body(...)):
    res = await call_all("POST", "/dsync/control/tasks", {"action": "traffic", "enabled": bool(body.get("enabled"))})
    return {"enabled": bool(body.get("enabled")), "result": {k: ok for k, (ok, _) in res.items()}}


async def leader_or_409() -> str:
    leader = (await get_status())["agreed_leader"]
    if not leader:
        raise HTTPException(409, "satellites do not agree on a leader yet")
    return leader


@router.post("/tasks/assign")
async def tasks_assign(body: Dict[str, Any] = Body(...)):
    leader = await leader_or_409()
    ok, data = await call(leader, "POST", "/dsync/control/tasks", {"action": "assign", "task_id": body.get("task_id"),
                                                                     "owner": body.get("owner")})
    if not ok:
        raise HTTPException(409, data)
    return {"decided_by": leader, **data}


@router.post("/tasks/reconcile")
async def tasks_reconcile():
    leader = await leader_or_409()
    ok, data = await call(leader, "POST", "/dsync/control/tasks", {"action": "reconcile"}, timeout=15.0)
    if not ok:
        raise HTTPException(409, data)
    return {"decided_by": leader, **data}


# ------------------------------------------------------------------ Chandy-Lamport snapshots
def assemble_snapshot(snap_id: str, pieces: List[Dict[str, Any]], initiator: str) -> Dict[str, Any]:
    on_sats, in_transit, channel_states = [], [], {}
    for p in pieces:
        for t in p["state"]["tasks"]:
            on_sats.append({"task_id": t["task_id"], "at": p["node"], "version": t["version"]})
        for src, msgs in (p.get("channels") or {}).items():
            channel_states[f"{src}->{p['node']}"] = [{"msg_type": m["msg_type"], "lamport": m.get("lamport"),
                                                      "task_id": ((m.get("payload") or {}).get("task") or {}).get("task_id")}
                                                     for m in msgs]
            for m in msgs:
                task = (m.get("payload") or {}).get("task")
                if m["msg_type"] in ("TASK_HANDOFF", "TASK_ASSIGN") and task:
                    in_transit.append({"task_id": task["task_id"], "channel": f"{src}->{p['node']}", "version": task["version"]})
    seen = [x["task_id"] for x in on_sats] + [x["task_id"] for x in in_transit]
    expected = sorted(TASKS_BY_ID)
    missing = sorted(set(expected) - set(seen))
    duplicated = sorted({t for t in seen if seen.count(t) > 1})
    complete = all(p.get("complete") for p in pieces)
    return {
        "snapshot_id": snap_id, "initiator": initiator,
        "satellites": {p["node"]: {k: v for k, v in p["state"].items()} for p in pieces},
        "channel_states": channel_states,
        "tasks_on_satellites": on_sats, "tasks_in_transit": in_transit,
        "in_transit_messages_count": sum(len(v) for v in channel_states.values()),
        "consistency": {
            "invariant": "every mission task appears exactly once (on a satellite or in a channel)",
            "holds": not missing and not duplicated and complete,
            "missing": missing, "duplicated": duplicated, "all_pieces_complete": complete,
            "pieces": len(pieces),
        },
        "taken_at": time.time(),
    }


@router.post("/snapshot")
async def snapshot(body: Dict[str, Any] = Body(default={})):
    st = _responsive(await states())
    if not st:
        raise HTTPException(409, "no responsive satellites")
    initiator = body.get("initiator") or (await get_status())["agreed_leader"] or sorted(st)[0]
    snap_id = f"snap-{int(time.time() * 1000)}"
    ok, data = await call(initiator, "POST", "/dsync/control/snapshot", {"snapshot_id": snap_id})
    if not ok:
        raise HTTPException(502, data)
    expected = set(st)
    end = time.time() + 14.0
    pieces: Dict[str, Dict[str, Any]] = {}
    while time.time() < end and set(pieces) != expected:
        for e in event_store.for_run(snap_id):
            if e.get("label") in ("SNAPSHOT_LOCAL_DONE", "SNAPSHOT_LOCAL_TIMEOUT"):
                pieces[e["node"]] = e["detail"]
        await asyncio.sleep(0.2)
    result = assemble_snapshot(snap_id, list(pieces.values()), initiator)
    result["missing_pieces_from"] = sorted(expected - set(pieces))
    events = event_store.for_run(snap_id)
    result["markers_sent"] = sum(1 for e in events if e.get("kind") == "SEND" and e.get("msg_type") == "SNAP_MARKER")
    snapshot_history.append(result)
    del snapshot_history[:-30]
    from backend.fa2.bus import mission_bus
    await mission_bus.publish("SNAPSHOT_COMPLETED", snapshot_id=snap_id, snapshot=result)
    try:  # archive in OrbitFS (Phase 4) when available
        from backend.fa2.orbitfs import archive_json
        result["archived_as"] = await archive_json(f"snapshots/{snap_id}.json", result)
    except Exception:
        pass
    return result


@router.get("/snapshots")
async def snapshots():
    return {"snapshots": snapshot_history[-20:]}


# ------------------------------------------------------------------ deadlock detection
@router.get("/deadlock/graph")
async def deadlock_graph():
    st = await states()
    edges, nodes = [], {}
    for sid, s in st.items():
        d = s.get("deadlock") or {}
        nodes[sid] = {"holds": [x for x in ([sid] if d.get("transponder_holder") == sid else []) + d.get("holds_remote", [])],
                      "waiting_for": d.get("waiting_for"), "transponder_holder": d.get("transponder_holder"),
                      "queue": d.get("queue", []), "unreachable": s.get("unreachable", False)}
        if d.get("waiting_for"):
            edges.append({"from": sid, "to": d["waiting_for"], "resource": f"{d.get('wants')} transponder"})
    return {"nodes": nodes, "edges": edges}


@router.post("/deadlock/run")
async def deadlock_run(body: Dict[str, Any] = Body(default={})):
    members = body.get("members") or ["SAT-01", "SAT-02", "SAT-03"]
    mode = body.get("mode", "cycle")
    if len(members) < 2 or mode not in ("cycle", "chain"):
        raise HTTPException(422, "need >= 2 members and mode cycle|chain")
    st = _responsive(await states())
    if any(m not in st for m in members):
        raise HTTPException(409, f"all members must be responsive: {sorted(set(members) - set(st))} are not")
    targets = {m: members[(i + 1) % len(members)] for i, m in enumerate(members)}
    if mode == "chain":
        targets[members[-1]] = None
    run_id = f"deadlock-{mode}-{int(time.time() * 1000)}"
    hold = float(body.get("hold_ms", 1500 if mode == "chain" else 300))
    t0 = time.time()
    results = await asyncio.gather(*(call(m, "POST", "/dsync/control/deadlock/run",
                                          {"target": targets[m], "hold_ms": hold, "run_id": run_id}, timeout=30.0)
                                     for m in members))
    events = await _settle_events(run_id)
    wait_edges = [{"from": e["node"], "to": e["detail"]["waits_for"], "true_ts": e["true_ts"]}
                  for e in events if e.get("label") == "WAIT_FOR"]
    detections = [e["detail"] for e in events if e.get("label") == "DEADLOCK_DETECTED"]
    run = {
        "run_id": run_id, "mode": mode, "members": members, "requests": targets,
        "outcomes": {m: (data if ok else {"status": "ERROR", "error": data}) for m, (ok, data) in zip(members, results)},
        "wait_for_edges": wait_edges, "detections": detections,
        "deadlock_detected": bool(detections), "victim": detections[0]["victim"] if detections else None,
        "probes": {
            "initiated": sum(1 for e in events if e.get("label") == "PROBE_INITIATED"),
            "forwarded": sum(1 for e in events if e.get("label") == "PROBE_FORWARDED"),
            "dropped": sum(1 for e in events if e.get("label") == "PROBE_DROPPED"),
            "messages": sum(1 for e in events if e.get("kind") == "SEND" and e.get("msg_type") == "CMH_PROBE"),
        },
        "detection_ms": round((min(e["true_ts"] for e in events if e.get("label") == "DEADLOCK_DETECTED") - t0) * 1000, 1)
        if detections else None,
        "knapp_class": "edge-chasing (Chandy-Misra-Haas, AND model)",
        "started_at": t0,
    }
    deadlock_runs.append(run)
    del deadlock_runs[:-30]
    return run


@router.get("/deadlock/runs")
async def deadlock_list():
    return {"runs": deadlock_runs[-20:]}


# ------------------------------------------------------------------ Ground Blackout Mode
@router.post("/blackout/start")
async def blackout_start(body: Dict[str, Any] = Body(default={})):
    seconds = max(10, min(int(body.get("seconds", 60)), 600))
    if blackout["active"]:
        raise HTTPException(409, "a blackout is already running")
    now = time.time()
    blackout.update({"active": True, "started_at": now, "ends_at": now + seconds, "seconds": seconds})
    crash = body.get("crash")
    if crash:
        async def crash_later():
            await asyncio.sleep(float(body.get("crash_after_s", 10)))
            from backend.fa2.router import push_fault
            await push_fault("CRASH", {}, [crash])
        asyncio.ensure_future(crash_later())
    return {"active": True, "started_at": now, "ends_at": now + seconds, "crash": crash,
            "note": "Mission Control now refuses all satellite traffic (heartbeats, telemetry, events, time). "
                    "It can still query satellites for this console."}


@router.post("/blackout/stop")
async def blackout_stop():
    _end_blackout("operator")
    return {"active": False}


@router.get("/blackout/status")
async def blackout_status():
    blackout_blocks("", "GET")  # expire if due
    st = await states()
    return {**{k: v for k, v in blackout.items() if k != "history"}, "history": blackout["history"][-5:],
            "now": time.time(),
            "satellites": {sid: {"ground_ok": (s.get("ground") or {}).get("ok"),
                                 "events_waiting": (s.get("ground") or {}).get("events_waiting_for_ground"),
                                 "leader": (s.get("election") or {}).get("leader"),
                                 "term": (s.get("election") or {}).get("term"),
                                 "silent": s.get("silent"), "unreachable": s.get("unreachable", False),
                                 "tasks": [t["task_id"] for t in (s.get("tasks") or {}).get("owned", [])]}
                           for sid, s in st.items()}}


INTERESTING = {"GROUND_LOST", "GROUND_RESTORED", "PEER_SUSPECTED", "PEER_DEAD", "PEER_RECOVERED", "LEADER_LOST",
               "ELECTION_START", "LEADER_ELECTED", "LEADER_ACCEPTED", "TASK_REASSIGNED", "TASK_ASSIGNED",
               "TASK_REVOKED", "BERKELEY_DONE", "CLOCK_ADJUSTED", "FAULT_CRASH", "FAULT_RECOVER", "TASK_UNASSIGNED"}


@router.get("/blackout/report")
async def blackout_report():
    last = blackout["history"][-1] if blackout["history"] else None
    if blackout["active"]:
        window = (blackout["started_at"], time.time())
    elif last:
        window = (last["started_at"], last["ended_at"])
    else:
        return {"available": False, "reason": "no blackout has run yet"}
    events = [e for e in event_store.query(since=window[0] - 1, limit=20000, include_background=True)
              if e.get("label") in INTERESTING and e["true_ts"] <= window[1] + 20]
    # causal order: Lamport timestamp, ties by satellite ID (consistent with happened-before)
    events.sort(key=lambda e: (e.get("lamport", 0), e.get("node", "")))
    during = [e for e in events if window[0] <= e["true_ts"] <= window[1]]
    late = [e for e in during if e.get("collected_at", 0) > window[1]]
    return {
        "available": True, "window": {"start": window[0], "end": window[1], "seconds": round(window[1] - window[0], 1)},
        "active": blackout["active"],
        "timeline": [{"node": e["node"], "label": e["label"], "lamport": e.get("lamport"), "vector": e.get("vector"),
                      "true_ts": e["true_ts"], "detail": e.get("detail"),
                      "reported_after_blackout": e.get("collected_at", 0) > window[1]} for e in events],
        "summary": {
            "events_during_blackout": len(during),
            "delivered_only_after_ground_returned": len(late),
            "satellites_declared_dead": sorted({(e.get("detail") or {}).get("peer") for e in during if e["label"] == "PEER_DEAD"}),
            "leaders_elected": sorted({(e.get("detail") or {}).get("leader") for e in during if e["label"] == "LEADER_ELECTED"}),
            "tasks_reassigned": [(e.get("detail") or {}) for e in during if e["label"] == "TASK_REASSIGNED"],
            "berkeley_rounds": sum(1 for e in during if e["label"] == "BERKELEY_DONE"),
        },
    }
