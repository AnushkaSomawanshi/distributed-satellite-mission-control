"""
FA-2 Mission Control API (/api/fa2).

Mission Control is an OBSERVER and an experiment launcher here:
- it forwards faults and "start" commands to satellites,
- it stores the events satellites report and computes measured metrics from them,
- it is the time server for Cristian's algorithm (the GPS-like reference).
It never decides an election, grants a lock or adjusts a clock itself.
"""

import asyncio
import logging
import random
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx
from fastapi import APIRouter, Body, HTTPException, Query

from backend.fa2.event_store import event_store
from backend.fa2.metrics import election_metrics, mutex_metrics
from backend.registry.service_registry import global_registry

logger = logging.getLogger("FA2")

router = APIRouter(prefix="/api/fa2", tags=["FA-2 distributed algorithms"])

MUTEX_ALGORITHMS = ("centralised", "ricart_agrawala", "token_ring", "lodha_kshemkalyani")
ELECTION_ALGORITHMS = ("bully", "ring")

_client: Optional[httpx.AsyncClient] = None
_bindings: Dict[str, Any] = {}
arena_runs: List[Dict[str, Any]] = []
clock_sync_runs: List[Dict[str, Any]] = []


def bind(fault_simulator: Any = None, broadcaster: Any = None) -> None:
    """Called once by backend.main to give this router the shared fault simulator and WebSocket hub."""
    _bindings.update({"faults": fault_simulator, "ws": broadcaster})


# ------------------------------------------------------------------ satellites
def _client_get() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient()
    return _client


def registered_ids() -> List[str]:
    return sorted(r.satellite_id for r in global_registry.list_all())


async def call(sat_id: str, method: str, path: str, body: Optional[Dict[str, Any]] = None,
               timeout: float = 5.0) -> Tuple[bool, Any]:
    reg = global_registry.lookup(sat_id)
    if reg is None:
        return False, f"{sat_id} is not registered"
    url = f"http://{reg.address}:{reg.p2p_port}{path}"
    try:
        resp = await _client_get().request(method, url, json=body, timeout=timeout)
    except Exception as exc:
        return False, f"{sat_id} unreachable: {exc.__class__.__name__}"
    try:
        data = resp.json()
    except ValueError:
        data = resp.text
    if resp.status_code >= 400:
        return False, data.get("detail", data) if isinstance(data, dict) else data
    return True, data


async def call_all(method: str, path: str, body: Optional[Dict[str, Any]] = None, ids: Optional[List[str]] = None,
                   timeout: float = 5.0) -> Dict[str, Tuple[bool, Any]]:
    ids = ids or registered_ids()
    results = await asyncio.gather(*(call(i, method, path, body, timeout) for i in ids))
    return dict(zip(ids, results))


async def states() -> Dict[str, Dict[str, Any]]:
    out = {}
    for sid, (ok, data) in (await call_all("GET", "/dsync/state", timeout=2.0)).items():
        out[sid] = data if ok else {"node": sid, "unreachable": True, "error": data}
    return out


def _responsive(st: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {k: v for k, v in st.items() if not v.get("unreachable") and not v.get("silent")}


async def _broadcast(message: Dict[str, Any]) -> None:
    ws = _bindings.get("ws")
    if ws is not None:
        try:
            await ws.broadcast(message)
        except Exception:  # pragma: no cover
            pass


async def _settle_events(run_id: str, max_wait: float = 4.0) -> List[Dict[str, Any]]:
    """Wait until the satellites have shipped every event of a run (count stops changing)."""
    end, last, stable_since = time.time() + max_wait, -1, time.time()
    while time.time() < end:
        n = len(event_store.for_run(run_id))
        if n != last:
            last, stable_since = n, time.time()
        elif time.time() - stable_since > 0.8:
            break
        await asyncio.sleep(0.1)
    return event_store.for_run(run_id)


# ------------------------------------------------------------------ event collection
async def ingest(events: List[Dict[str, Any]], mode: str) -> int:
    fresh = event_store.add_many(events, mode)
    for e in fresh:
        if e.get("label") == "LEADER_ELECTED":
            leader = (e.get("detail") or {}).get("leader")
            if leader:
                global_registry.current_leader = leader
    # satellite events that serverless functions may react to (they arrived via RabbitMQ dsync.events)
    from backend.fa2.bus import mission_bus
    for e in fresh:
        if e.get("kind") == "LOCAL" and e.get("label") in ("PEER_DEAD", "LEADER_ELECTED", "TASK_REASSIGNED", "DEADLOCK_DETECTED"):
            await mission_bus.dispatch({"type": e["label"], "source": "satellite", "node": e["node"],
                                        "detail": e.get("detail"), "at": e.get("true_ts")})
    visible = [e for e in fresh if e.get("algo") != "beacon" or e.get("kind") == "LOCAL"]
    if visible:
        await _broadcast({"event_type": "DSYNC_EVENTS", "events": visible, "timestamp": time.time()})
    return len(fresh)


async def ingest_broker_message(payload: Dict[str, Any]) -> None:
    await ingest(payload.get("events", []), payload.get("broker_mode", "RABBITMQ"))


@router.get("/time")
async def server_time():
    """Cristian's algorithm time server (Mission Control = ground reference clock)."""
    return {"server_time": time.time()}


@router.post("/events")
async def post_events(body: Dict[str, Any] = Body(...)):
    """HTTP fallback used by satellites when no RabbitMQ broker is reachable."""
    n = await ingest(body.get("events", []), "HTTP_FALLBACK")
    return {"accepted": n}


@router.get("/events")
async def get_events(run_id: Optional[str] = None, algo: Optional[str] = None, since: Optional[float] = None,
                     limit: int = Query(500, le=5000), include_background: bool = False):
    return {"events": event_store.query(run_id, algo, since, limit, include_background), "collector": event_store.stats()}


@router.get("/state")
async def get_state():
    return {"satellites": await states(), "collector": event_store.stats(), "timestamp": time.time()}


@router.get("/status")
async def get_status():
    st = await states()
    leaders = {sid: (s.get("election") or {}).get("leader") for sid, s in st.items() if not s.get("unreachable")}
    terms = {sid: (s.get("election") or {}).get("term") for sid, s in st.items() if not s.get("unreachable")}
    live = _responsive(st)
    agreed = {(leaders[s], terms[s]) for s in live}
    return {
        "leader_by_satellite": leaders, "term_by_satellite": terms,
        "agreed_leader": next(iter(agreed))[0] if len(agreed) == 1 else None,
        "silent": sorted(s for s, v in st.items() if v.get("silent")),
        "unreachable": sorted(s for s, v in st.items() if v.get("unreachable")),
        "partition_groups": next((v.get("partition_groups") for v in st.values() if v.get("partition_groups")), None),
        "collector": event_store.stats(),
    }


# ------------------------------------------------------------------ faults (enforced by satellites)
async def push_fault(fault: str, params: Dict[str, Any], targets: Optional[List[str]] = None) -> Dict[str, Any]:
    results = await call_all("POST", "/dsync/control/fault", {"type": fault, "params": params}, ids=targets)
    return {sid: ("APPLIED" if ok else f"FAILED: {data}") for sid, (ok, data) in results.items()}


@router.post("/faults/clock-drift")
async def fault_clock_drift(body: Dict[str, Any] = Body(...)):
    target = body.get("target")
    if not target:
        raise HTTPException(422, "target is required")
    params = {"offset_ms": float(body.get("offset_ms", 0.0))}
    if body.get("drift_ppm") is not None:
        params["drift_ppm"] = float(body["drift_ppm"])
    return {"fault": "CLOCK_DRIFT", "params": params, "result": await push_fault("CLOCK_DRIFT", params, [target])}


@router.post("/faults/clock-reset")
async def fault_clock_reset(body: Dict[str, Any] = Body(default={})):
    targets = [body["target"]] if body.get("target") else None
    return {"fault": "CLOCK_RESET", "result": await push_fault("CLOCK_RESET", {}, targets)}


@router.post("/faults/partition")
async def fault_partition(body: Dict[str, Any] = Body(...)):
    groups = body.get("groups")
    if not groups or len(groups) < 2:
        raise HTTPException(422, "groups must list at least two groups of satellite IDs")
    fs = _bindings.get("faults")
    if fs is not None:
        fs.inject_fault("NETWORK_PARTITION", "CONSTELLATION", {"partition_a": groups[0], "partition_b": groups[1]}, source="FA2")
    return {"fault": "PARTITION", "groups": groups, "result": await push_fault("PARTITION", {"groups": groups})}


@router.post("/faults/heal")
async def fault_heal():
    fs = _bindings.get("faults")
    if fs is not None and getattr(fs, "partitions", None):
        fs.clear_partition()
    return {"fault": "HEAL", "result": await push_fault("HEAL", {})}


@router.post("/faults/crash")
async def fault_crash(body: Dict[str, Any] = Body(...)):
    target = body.get("target")
    if not target:
        raise HTTPException(422, "target is required")
    return {"fault": "CRASH", "target": target, "result": await push_fault("CRASH", {}, [target])}


@router.post("/faults/recover")
async def fault_recover(body: Dict[str, Any] = Body(default={})):
    targets = [body["target"]] if body.get("target") else None
    return {"fault": "RECOVER", "result": await push_fault("RECOVER", {}, targets)}


# ------------------------------------------------------------------ causality lens traffic
@router.post("/lens/send")
async def lens_send(body: Dict[str, Any] = Body(...)):
    source, dest = body.get("source"), body.get("dest")
    if not source or not dest or source == dest:
        raise HTTPException(422, "source and dest must be two different satellites")
    ok, data = await call(source, "POST", "/dsync/control/send", {"dest": dest, "label": body.get("label"), "run_id": body.get("run_id")})
    if not ok:
        raise HTTPException(502, data)
    return data


@router.post("/lens/local")
async def lens_local(body: Dict[str, Any] = Body(...)):
    ok, data = await call(body.get("node", ""), "POST", "/dsync/control/local", {"label": body.get("label", "LOCAL_EVENT"), "run_id": body.get("run_id")})
    if not ok:
        raise HTTPException(502, data)
    return data


@router.post("/lens/traffic")
async def lens_traffic(body: Dict[str, Any] = Body(default={})):
    """Generate real cross-link messages between random pairs of responsive satellites."""
    count = max(1, min(int(body.get("messages", 8)), 40))
    run_id = body.get("run_id") or f"lens-{int(time.time() * 1000)}"
    live = sorted(_responsive(await states()))
    if len(live) < 2:
        raise HTTPException(409, "need at least two responsive satellites")
    sent = []
    for _ in range(count):
        a, b = random.sample(live, 2)
        ok, data = await call(a, "POST", "/dsync/control/send", {"dest": b, "run_id": run_id})
        sent.append({"from": a, "to": b, "delivered": bool(ok and data.get("delivered")), "reason": None if ok and data.get("delivered") else data})
        if random.random() < 0.3:
            await call(random.choice(live), "POST", "/dsync/control/local", {"label": "LOCAL_EVENT", "run_id": run_id})
        await asyncio.sleep(random.uniform(0.02, 0.12))
    return {"run_id": run_id, "messages": sent}


# ------------------------------------------------------------------ election
async def _wait_agreement(min_term: int, exclude: Tuple[str, ...] = (), timeout: float = 12.0) -> Optional[Dict[str, Any]]:
    end = time.time() + timeout
    while time.time() < end:
        st = _responsive(await states())
        st = {k: v for k, v in st.items() if k not in exclude}
        views = {((v.get("election") or {}).get("leader"), (v.get("election") or {}).get("term") or 0) for v in st.values()}
        running = any((v.get("election") or {}).get("running") for v in st.values())
        if st and len(views) == 1 and not running:
            leader, term = next(iter(views))
            if leader and term >= min_term and leader not in exclude:
                return {"leader": leader, "term": term, "agreed_by": sorted(st)}
        await asyncio.sleep(0.1)
    return None


def _store_run(run: Dict[str, Any]) -> Dict[str, Any]:
    arena_runs.append(run)
    del arena_runs[:-200]
    return run


@router.post("/election/config")
async def election_config(body: Dict[str, Any] = Body(...)):
    algo = (body.get("algorithm") or "").lower()
    if algo not in ELECTION_ALGORITHMS:
        raise HTTPException(422, f"algorithm must be one of {ELECTION_ALGORITHMS}")
    res = await call_all("POST", "/dsync/control/election/config", {"algorithm": algo})
    return {"algorithm": algo, "result": {k: ok for k, (ok, _) in res.items()}}


@router.post("/election/run")
async def election_run(body: Dict[str, Any] = Body(default={})):
    algo = (body.get("algorithm") or "bully").lower()
    if algo not in ELECTION_ALGORITHMS:
        raise HTTPException(422, f"algorithm must be one of {ELECTION_ALGORITHMS}")
    st = _responsive(await states())
    if not st:
        raise HTTPException(409, "no responsive satellites")
    initiator = body.get("initiator") or sorted(st)[0]
    if initiator not in st:
        raise HTTPException(409, f"{initiator} is not responsive")
    start_term = max(((v.get("election") or {}).get("term") or 0) for v in st.values())
    run_id = f"elect-{algo}-{int(time.time() * 1000)}"
    t0 = time.time()
    ok, data = await call(initiator, "POST", "/dsync/control/election/start", {"algorithm": algo, "run_id": run_id})
    if not ok:
        raise HTTPException(502, data)
    agreement = await _wait_agreement(start_term + 1)
    agreed_ms = round((time.time() - t0) * 1000, 2) if agreement else None
    events = await _settle_events(run_id)
    run = {"kind": "election", "run_id": run_id, "algorithm": algo, "initiator": initiator,
           "participants": sorted(st), "agreement": agreement, "agreement_observed_ms": agreed_ms,
           "status": "AGREED" if agreement else "NO_AGREEMENT_WITHIN_TIMEOUT",
           **election_metrics(events, {algo}), "started_at": t0}
    return _store_run(run)


@router.post("/election/leader-failure")
async def election_leader_failure(body: Dict[str, Any] = Body(default={})):
    """Crash the current leader and measure how the survivors detect it and elect a new one by themselves."""
    algo = (body.get("algorithm") or "bully").lower()
    if algo not in ELECTION_ALGORITHMS:
        raise HTTPException(422, f"algorithm must be one of {ELECTION_ALGORITHMS}")
    status = await get_status()
    leader = status["agreed_leader"]
    if not leader:
        raise HTTPException(409, "satellites do not agree on a leader yet; run an election first")
    await call_all("POST", "/dsync/control/election/config", {"algorithm": algo})
    start_term = max(t or 0 for t in status["term_by_satellite"].values())
    t0 = time.time()
    await push_fault("CRASH", {}, [leader])
    agreement = await _wait_agreement(start_term + 1, exclude=(leader,), timeout=25.0)
    elapsed = round((time.time() - t0) * 1000, 2) if agreement else None
    await asyncio.sleep(1.0)
    events = [e for e in event_store.query(since=t0, limit=5000, include_background=True)]
    detections = [e for e in events if e.get("label") == "PEER_DEAD" and (e.get("detail") or {}).get("peer") == leader]
    first_detect = min((e["true_ts"] for e in detections), default=None)
    if body.get("recover", True):
        await push_fault("RECOVER", {}, [leader])
    run = {"kind": "leader_failure", "run_id": f"failover-{int(t0 * 1000)}", "algorithm": algo,
           "failed_leader": leader, "agreement": agreement,
           "status": "NEW_LEADER_AGREED" if agreement else "NO_AGREEMENT_WITHIN_TIMEOUT",
           "time_to_new_leader_ms": elapsed,
           "detection_ms": round((first_detect - t0) * 1000, 2) if first_detect else None,
           "detected_by": sorted({e["node"] for e in detections}),
           **election_metrics(events, {algo}), "recovered_old_leader": bool(body.get("recover", True)),
           "started_at": t0}
    return _store_run(run)


# ------------------------------------------------------------------ clock synchronisation
@router.get("/clocks")
async def clocks():
    st = await states()
    return {"clocks": {sid: {"clock": v.get("clock"), "lamport": v.get("lamport"), "vector": v.get("vector"),
                             "silent": v.get("silent"), "unreachable": v.get("unreachable", False),
                             "peer_offsets_ms": {p: e.get("clock_offset_ms") for p, e in (v.get("peers") or {}).items()}}
                       for sid, v in st.items()},
            "runs": clock_sync_runs[-10:]}


@router.post("/clocks/cristian")
async def clocks_cristian():
    run_id = f"cristian-{int(time.time() * 1000)}"
    live = sorted(_responsive(await states()))
    res = await call_all("POST", "/dsync/control/clock/cristian", {"run_id": run_id}, ids=live)
    nodes = [data if ok else {"node": sid, "error": data} for sid, (ok, data) in res.items()]
    after = [n["skew_after_ms"] for n in nodes if "skew_after_ms" in n]
    before = [n["skew_before_ms"] for n in nodes if "skew_before_ms" in n]
    run = {"algorithm": "cristian", "run_id": run_id, "nodes": nodes, "at": time.time(),
           "max_abs_skew_before_ms": round(max(map(abs, before)), 3) if before else None,
           "max_abs_skew_after_ms": round(max(map(abs, after)), 3) if after else None,
           "spread_before_ms": round(max(before) - min(before), 3) if before else None,
           "spread_after_ms": round(max(after) - min(after), 3) if after else None}
    clock_sync_runs.append(run)
    return run


@router.post("/clocks/berkeley")
async def clocks_berkeley():
    status = await get_status()
    leader = status["agreed_leader"]
    if not leader:
        raise HTTPException(409, "Berkeley needs an agreed leader as time daemon; run an election first")
    ok, data = await call(leader, "POST", "/dsync/control/clock/berkeley", {"run_id": f"berkeley-{int(time.time() * 1000)}"}, timeout=10.0)
    if not ok:
        raise HTTPException(502, data)
    clock_sync_runs.append(data)
    return data


# ------------------------------------------------------------------ mutual exclusion arena
@router.post("/arena/mutex")
async def arena_mutex(body: Dict[str, Any] = Body(default={})):
    algo = body.get("algorithm", "ricart_agrawala")
    if algo not in MUTEX_ALGORITHMS:
        raise HTTPException(422, f"algorithm must be one of {MUTEX_ALGORITHMS}")
    rounds = max(1, min(int(body.get("rounds", 3)), 10))
    hold_ms = max(1.0, min(float(body.get("hold_ms", 100)), 2000.0))
    st = _responsive(await states())
    live = sorted(st)
    requesters = [r for r in (body.get("requesters") or live) if r in st]
    if len(requesters) < 1:
        raise HTTPException(409, "no responsive requesters")
    if algo == "centralised":
        status = await get_status()
        if not status["agreed_leader"]:
            raise HTTPException(409, "centralised mutex needs an agreed leader; run an election first")
    run_id = f"mutex-{algo}-{int(time.time() * 1000)}"
    if algo == "token_ring":
        holder = next((s for s, v in st.items() if ((v.get("mutex") or {}).get("token_ring") or {}).get("have_token")), None)
        await asyncio.gather(*(call(s, "POST", "/dsync/control/mutex/token",
                                    {"action": "start", "run_id": run_id, "ring": live, "create": holder is None and s == live[0]})
                               for s in live))
    start_at = time.time() + 0.5
    timeout = rounds * (hold_ms / 1000.0 + 25.0) + 10.0
    t0 = time.time()
    results = await call_all("POST", "/dsync/control/mutex/run",
                             {"algorithm": algo, "run_id": run_id, "rounds": rounds, "hold_ms": hold_ms, "start_at": start_at},
                             ids=requesters, timeout=timeout)
    if algo == "token_ring":
        await call_all("POST", "/dsync/control/mutex/token", {"action": "stop", "run_id": run_id}, ids=live)
    events = await _settle_events(run_id)
    errors = {sid: (data if not ok else [r for r in data.get("results", []) if "error" in r])
              for sid, (ok, data) in results.items()}
    errors = {k: v for k, v in errors.items() if v}
    run = {"kind": "mutex", "run_id": run_id, "algorithm": algo, "rounds": rounds, "hold_ms": hold_ms,
           "requesters": requesters, "participants": live, "errors": errors,
           "status": "COMPLETED" if not errors else "COMPLETED_WITH_ERRORS",
           "wall_ms": round((time.time() - t0) * 1000, 2), **mutex_metrics(events, algo), "started_at": t0}
    return _store_run(run)


@router.get("/arena/runs")
async def arena_list(kind: Optional[str] = None, limit: int = 50):
    runs = [r for r in arena_runs if not kind or r.get("kind") == kind]
    return {"runs": runs[-limit:]}


@router.get("/arena/summary")
async def arena_summary():
    """Latest measured run per algorithm (what the Arena charts compare)."""
    latest: Dict[str, Dict[str, Any]] = {}
    for r in arena_runs:
        latest[f"{r['kind']}:{r['algorithm']}"] = r
    return {"latest": latest, "total_runs": len(arena_runs)}
