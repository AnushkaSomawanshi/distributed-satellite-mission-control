"""
MapReduce JobTracker (Unit 4, Apache Hadoop case study), running in Mission Control.

Input: a telemetry archive stored in OrbitFS (CSV, chunks split on line boundaries).
1. Map: one task per chunk, scheduled on a satellite that HOLDS a replica (data locality).
   Each satellite runs the mapper + combiner on its local chunks.
2. Shuffle: mappers partition their output by key (crc32 % R) and send it straight to R reducer
   satellites.
3. Reduce: reducers merge the partials and return final values.
Fault tolerance: a failed map attempt is re-executed on another replica holder; reducers ignore
output from attempts the JobTracker did not accept.
"""

import asyncio
import csv
import io
import logging
import time
import uuid
from collections import deque
from typing import Any, Deque, Dict, List

from fastapi import APIRouter, Body, HTTPException

from backend.fa2.orbitfs import namenode

logger = logging.getLogger("MapReduce")
router = APIRouter(prefix="/api/mapreduce", tags=["Unit 4: MapReduce"])

JOBS = {
    "health_stats": "Per satellite: samples, average/min battery, average/max temperature, average health, anomalies",
    "status_counts": "Per satellite and status: number of telemetry samples",
}
HEADER = ["timestamp", "satellite_id", "battery", "temperature", "cpu_usage", "signal_strength", "health_score", "status"]

ARCHIVE_CHUNK = 4 * 1024
samples: Deque[List[Any]] = deque(maxlen=100_000)
job_history: List[Dict[str, Any]] = []


def record_sample(data: Dict[str, Any]) -> None:
    """Called by the RabbitMQ telemetry consumer for every validated sample."""
    samples.append([round(float(data.get("timestamp") or time.time()), 3), data.get("satellite_id"),
                    data.get("battery"), data.get("temperature"), data.get("cpu_usage"),
                    data.get("signal_strength"), data.get("health_score"), data.get("status")])


@router.get("/jobs/types")
async def job_types():
    return {"jobs": JOBS, "samples_buffered": len(samples)}


@router.post("/archive")
async def archive():
    """Write the telemetry received so far to OrbitFS as a CSV file (the job input)."""
    if not samples:
        raise HTTPException(409, "no telemetry samples received yet")
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(HEADER)
    w.writerows(list(samples))
    path = f"telemetry/archive-{int(time.time())}.csv"
    # Small blocks (4 KB) so even a few minutes of telemetry spreads over several satellites/map tasks.
    info = await namenode.write(path, buf.getvalue().encode(), "text/csv", chunk_size=ARCHIVE_CHUNK)
    return {"path": path, "rows": len(samples), "bytes": info["size"], "chunks": len(info["chunks"])}


async def _post(sid: str, path: str, body: Dict[str, Any], timeout: float = 30.0) -> Dict[str, Any]:
    ep = namenode.endpoint(sid)
    r = await namenode.client().post(f"http://{ep['address']}:{ep['port']}{path}", json=body, timeout=timeout)
    if r.status_code != 200:
        raise RuntimeError(f"{sid}: HTTP {r.status_code} {r.text[:200]}")
    return r.json()


@router.post("/jobs")
async def run_job(body: Dict[str, Any] = Body(...)):
    job = body.get("job", "health_stats")
    if job not in JOBS:
        raise HTTPException(422, f"job must be one of {list(JOBS)}")
    path = body.get("input")
    if not path:
        archives = sorted(p for p in namenode.files if p.startswith("telemetry/archive-"))
        if not archives:
            raise HTTPException(409, "no telemetry archive in OrbitFS yet: archive telemetry first")
        path = archives[-1]
    if path not in namenode.files:
        raise HTTPException(404, f"{path} not in OrbitFS")
    await namenode.refresh_block_reports()
    live = set(namenode.live())
    info = namenode.info(path)
    job_id = f"job-{job}-{uuid.uuid4().hex[:6]}"
    t0 = time.time()

    # 1. data-local map scheduling: each chunk goes to the least-loaded live holder
    load: Dict[str, int] = {}
    assignment: Dict[str, List[str]] = {}
    for c in info["chunks"]:
        holders = [s for s in c["replicas"] if s in live]
        if not holders:
            raise HTTPException(503, f"chunk {c['chunk_id']} has no live replica")
        best = min(holders, key=lambda s: (load.get(s, 0), s))
        load[best] = load.get(best, 0) + 1
        assignment.setdefault(best, []).append(c["chunk_id"])
    n_red = max(1, min(int(body.get("reducers", 2)), len(live)))
    reducers = [namenode.endpoint(s) for s in sorted(live, key=lambda s: (load.get(s, 0), s))[:n_red]]

    # 2. map (+ combiner + shuffle) on the satellites
    accepted, map_reports, retries = [], [], []

    async def map_on(sid: str, chunk_ids: List[str], attempt: int = 1) -> None:
        attempt_id = f"{job_id}-{sid}-a{attempt}"
        try:
            rep = await _post(sid, "/orbitfs/mapreduce/map", {"job_id": job_id, "job": job, "attempt_id": attempt_id,
                                                              "chunk_ids": chunk_ids, "reducers": reducers})
            accepted.append(attempt_id)
            map_reports.append(rep)
        except Exception as exc:
            if attempt >= 3:
                raise HTTPException(502, f"map task for {chunk_ids} failed {attempt} times: {exc}")
            # re-execute each chunk on another live replica holder
            for cid in chunk_ids:
                others = [s for s in namenode.chunks[cid]["replicas"] if s in live and s != sid]
                if not others:
                    raise HTTPException(503, f"no other replica of {cid} to re-run the map task")
                retries.append({"chunk_id": cid, "failed_on": sid, "rerun_on": others[0], "reason": str(exc)[:120]})
                await map_on(others[0], [cid], attempt + 1)

    t_map = time.time()
    await asyncio.gather(*(map_on(s, cids) for s, cids in assignment.items()))
    map_ms = round((time.time() - t_map) * 1000, 1)

    # 3. reduce
    t_red = time.time()
    red_reports = await asyncio.gather(*(_post(r["id"], "/orbitfs/mapreduce/reduce",
                                               {"job_id": job_id, "job": job, "accepted_attempts": accepted})
                                         for r in reducers))
    reduce_ms = round((time.time() - t_red) * 1000, 1)
    results: Dict[str, Any] = {}
    for rr in red_reports:
        results.update(rr["results"])
    if job == "status_counts":
        nested: Dict[str, Dict[str, int]] = {}
        for key, v in results.items():
            sat, status = key.split("|", 1)
            nested.setdefault(sat, {})[status] = v["count"]
        results = nested
    run = {
        "job_id": job_id, "job": job, "input": path, "input_bytes": info["size"], "chunks": len(info["chunks"]),
        "results": dict(sorted(results.items())),
        "counters": {
            "map_tasks": sum(len(r["chunks"]) for r in map_reports),
            "data_local_map_tasks": sum(len(r["chunks"]) for r in map_reports if r.get("data_local")),
            "records_read": sum(r["records"] for r in map_reports),
            "shuffle_bytes": sum(r["shuffle_bytes"] for r in map_reports),
            "reduce_tasks": len(reducers), "map_retries": len(retries),
        },
        "map_assignment": assignment, "reducers": [r["id"] for r in reducers], "retries": retries,
        "phases_ms": {"map_and_shuffle": map_ms, "reduce": reduce_ms, "total": round((time.time() - t0) * 1000, 1)},
        "engine": "OrbitFS MapReduce (Hadoop-style JobTracker, data-local map tasks on satellites)",
        "started_at": t0,
    }
    job_history.append(run)
    del job_history[:-20]
    return run


@router.get("/jobs")
async def jobs():
    return {"jobs": job_history[-10:], "samples_buffered": len(samples),
            "archives": sorted(p for p in namenode.files if p.startswith("telemetry/archive-"))}
