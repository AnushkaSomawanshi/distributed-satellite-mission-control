"""
OrbitFS DataNode + MapReduce TaskTracker, running inside every satellite (Unit 4).

OrbitFS (modelled on HDFS):
- Files are split into chunks by the NameNode (Mission Control); each chunk is stored on 3 satellites.
- Writes use a replication PIPELINE: the NameNode sends the chunk to the first DataNode, which stores
  it and forwards it to the next one, and so on; acknowledgements travel back up the pipeline.
- Every chunk carries a SHA-256 checksum, verified on store and on read.
- When a satellite dies, the NameNode asks a surviving holder to copy the chunk to another satellite
  (satellite-to-satellite transfer), restoring 3 copies.

MapReduce (modelled on Hadoop):
- Map tasks run on a satellite that HOLDS the chunk (data locality); a combiner pre-aggregates.
- Map output is partitioned by key and shuffled directly to reducer satellites.
- Reducers merge the partials and return final values to the JobTracker (Mission Control).
"""

import asyncio
import base64
import hashlib
import logging
import time
import zlib
from typing import Any, Dict, List, Optional

logger = logging.getLogger("dsync.datanode")

MAX_BYTES = 64 * 1024 * 1024


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ------------------------------------------------------------------ MapReduce jobs (fixed, no code shipping)
def _num(v: str) -> Optional[float]:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def map_health_stats(lines: List[str]) -> Dict[str, Dict[str, float]]:
    """key = satellite_id; combiner output = partial sums/min/max/counts."""
    out: Dict[str, Dict[str, float]] = {}
    for line in lines:
        parts = line.strip().split(",")
        if len(parts) < 8 or parts[0] == "timestamp":
            continue
        _, sat, battery, temp, cpu, signal, health, status = parts[:8]
        b, t, h = _num(battery), _num(temp), _num(health)
        if b is None or t is None or h is None:
            continue
        acc = out.setdefault(sat, {"samples": 0, "battery_sum": 0.0, "battery_min": 1e9, "temp_sum": 0.0,
                                   "temp_max": -1e9, "health_sum": 0.0, "anomalies": 0})
        acc["samples"] += 1
        acc["battery_sum"] += b
        acc["battery_min"] = min(acc["battery_min"], b)
        acc["temp_sum"] += t
        acc["temp_max"] = max(acc["temp_max"], t)
        acc["health_sum"] += h
        if b < 30 or t > 45 or status not in ("HEALTHY",):
            acc["anomalies"] += 1
    return out


def reduce_health_stats(partials: List[Dict[str, float]]) -> Dict[str, float]:
    n = sum(p["samples"] for p in partials)
    if not n:
        return {"samples": 0}
    return {
        "samples": int(n),
        "avg_battery": round(sum(p["battery_sum"] for p in partials) / n, 2),
        "min_battery": round(min(p["battery_min"] for p in partials), 2),
        "avg_temperature": round(sum(p["temp_sum"] for p in partials) / n, 2),
        "max_temperature": round(max(p["temp_max"] for p in partials), 2),
        "avg_health": round(sum(p["health_sum"] for p in partials) / n, 2),
        "anomalies": int(sum(p["anomalies"] for p in partials)),
    }


def map_status_counts(lines: List[str]) -> Dict[str, Dict[str, float]]:
    out: Dict[str, Dict[str, float]] = {}
    for line in lines:
        parts = line.strip().split(",")
        if len(parts) < 8 or parts[0] == "timestamp":
            continue
        key = f"{parts[1]}|{parts[7]}"
        out.setdefault(key, {"count": 0})["count"] += 1
    return out


def reduce_status_counts(partials: List[Dict[str, float]]) -> Dict[str, float]:
    return {"count": int(sum(p["count"] for p in partials))}


JOBS = {
    "health_stats": (map_health_stats, reduce_health_stats),
    "status_counts": (map_status_counts, reduce_status_counts),
}


def partition(key: str, reducers: int) -> int:
    return zlib.crc32(key.encode()) % reducers  # stable across processes (unlike hash())


class DataNode:
    def __init__(self, node: Any):
        self.node = node
        self.chunks: Dict[str, bytes] = {}
        self.checksums: Dict[str, str] = {}
        # job_id -> attempt_id -> key -> partials (only attempts the JobTracker accepts are reduced)
        self.shuffle_inbox: Dict[str, Dict[str, Dict[str, List[Dict[str, float]]]]] = {}
        self.stats = {"stored": 0, "forwarded": 0, "replicated_out": 0, "reads": 0, "checksum_failures": 0,
                      "map_tasks": 0, "reduce_tasks": 0}

    def used_bytes(self) -> int:
        return sum(len(v) for v in self.chunks.values())

    def block_report(self) -> Dict[str, Any]:
        return {"node": self.node.node_id, "chunks": sorted(self.chunks), "used_bytes": self.used_bytes(),
                "stats": dict(self.stats)}

    def _check_alive(self) -> None:
        if self.node.transport.silent:
            raise RuntimeError("satellite is silent")

    def _ev(self, label: str, **detail: Any) -> None:
        self.node.transport.local_event(label, algo="orbitfs", detail=detail or None)

    async def _post(self, address: str, port: int, path: str, body: Dict[str, Any], timeout: float = 10.0) -> Dict[str, Any]:
        import httpx
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(f"http://{address}:{port}{path}", json=body)
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------ chunks
    async def store(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """Store a chunk and forward it down the replication pipeline."""
        self._check_alive()
        data = base64.b64decode(body["data_b64"])
        if sha256(data) != body["checksum"]:
            self.stats["checksum_failures"] += 1
            raise ValueError("checksum mismatch: chunk corrupted in transit")
        if self.used_bytes() + len(data) > MAX_BYTES:
            raise ValueError("DataNode full")
        cid = body["chunk_id"]
        self.chunks[cid], self.checksums[cid] = data, body["checksum"]
        self.stats["stored"] += 1
        acks = [self.node.node_id]
        pipeline: List[Dict[str, Any]] = body.get("pipeline") or []
        if pipeline:
            nxt, rest = pipeline[0], pipeline[1:]
            if nxt["id"] in self.node.transport.blocked:
                logger.warning("pipeline next hop %s is across a partition", nxt["id"])
            else:
                try:
                    res = await self._post(nxt["address"], nxt["port"], "/orbitfs/chunk",
                                           {**body, "pipeline": rest})
                    acks += res.get("acks", [])
                    self.stats["forwarded"] += 1
                except Exception as exc:  # downstream failed: report the acks we have; NameNode re-replicates later
                    logger.warning("pipeline forward to %s failed: %s", nxt["id"], exc)
        self._ev("CHUNK_STORED", chunk_id=cid, bytes=len(data), pipeline_acks=acks)
        return {"acks": acks}

    def read(self, cid: str) -> Dict[str, Any]:
        self._check_alive()
        data = self.chunks.get(cid)
        if data is None:
            raise KeyError(cid)
        self.stats["reads"] += 1
        return {"chunk_id": cid, "data_b64": base64.b64encode(data).decode(), "checksum": self.checksums[cid],
                "served_by": self.node.node_id}

    async def replicate(self, cid: str, target: Dict[str, Any]) -> Dict[str, Any]:
        """Copy one of my chunks to another satellite (re-replication after a failure)."""
        self._check_alive()
        if target["id"] in self.node.transport.blocked:
            raise RuntimeError(f"{target['id']} is across a partition")
        data = self.chunks[cid]
        res = await self._post(target["address"], target["port"], "/orbitfs/chunk",
                               {"chunk_id": cid, "data_b64": base64.b64encode(data).decode(),
                                "checksum": self.checksums[cid], "pipeline": []})
        self.stats["replicated_out"] += 1
        self._ev("CHUNK_REPLICATED", chunk_id=cid, to=target["id"])
        return res

    def delete(self, cid: str) -> bool:
        self.checksums.pop(cid, None)
        return self.chunks.pop(cid, None) is not None

    # ------------------------------------------------------------ MapReduce
    async def run_map(self, body: Dict[str, Any]) -> Dict[str, Any]:
        self._check_alive()
        job_id, job = body["job_id"], body["job"]
        mapper, _ = JOBS[job]
        reducers: List[Dict[str, Any]] = body["reducers"]
        started = time.time()
        merged: Dict[str, Dict[str, float]] = {}
        records = 0
        bytes_read = 0
        for cid in body["chunk_ids"]:
            data = self.chunks[cid]                       # KeyError -> JobTracker retries elsewhere
            if sha256(data) != self.checksums[cid]:
                self.stats["checksum_failures"] += 1
                raise ValueError(f"chunk {cid} failed its checksum")
            lines = data.decode("utf-8", errors="replace").splitlines()
            records += len(lines)
            bytes_read += len(data)
            for key, partial in mapper(lines).items():   # combiner: one partial per key per map task
                merged.setdefault(key, [])
                merged[key].append(partial)
        partitions: List[Dict[str, List[Dict[str, float]]]] = [dict() for _ in reducers]
        for key, partials in merged.items():
            partitions[partition(key, len(reducers))].setdefault(key, []).extend(partials)
        shuffle_bytes = 0
        for i, r in enumerate(reducers):
            payload = {"job_id": job_id, "attempt_id": body["attempt_id"], "from": self.node.node_id,
                       "partition": partitions[i]}
            shuffle_bytes += len(str(payload))
            if r["id"] == self.node.node_id:
                self.accept_shuffle(payload)
            else:
                await self._post(r["address"], r["port"], "/orbitfs/mapreduce/shuffle", payload)
        self.stats["map_tasks"] += 1
        self._ev("MAP_TASK_DONE", job_id=job_id, chunks=body["chunk_ids"], records=records)
        return {"node": self.node.node_id, "attempt_id": body["attempt_id"], "chunks": body["chunk_ids"],
                "records": records, "bytes_read": bytes_read,
                "keys": len(merged), "shuffle_bytes": shuffle_bytes,
                "duration_ms": round((time.time() - started) * 1000, 2), "data_local": True}

    def accept_shuffle(self, body: Dict[str, Any]) -> Dict[str, Any]:
        attempt = self.shuffle_inbox.setdefault(body["job_id"], {}).setdefault(body["attempt_id"], {})
        for key, partials in body["partition"].items():
            attempt.setdefault(key, []).extend(partials)
        return {"ok": True}

    def run_reduce(self, body: Dict[str, Any]) -> Dict[str, Any]:
        self._check_alive()
        job_id, job = body["job_id"], body["job"]
        _, reducer = JOBS[job]
        started = time.time()
        attempts = self.shuffle_inbox.pop(job_id, {})
        accepted = set(body.get("accepted_attempts") or attempts)
        merged: Dict[str, List[Dict[str, float]]] = {}
        for attempt_id, keys in attempts.items():
            if attempt_id not in accepted:
                continue  # output of a failed / superseded map attempt
            for key, partials in keys.items():
                merged.setdefault(key, []).extend(partials)
        senders = sorted(a for a in attempts if a in accepted)
        results = {key: reducer(partials) for key, partials in sorted(merged.items())}
        self.stats["reduce_tasks"] += 1
        self._ev("REDUCE_TASK_DONE", job_id=job_id, keys=len(results))
        return {"node": self.node.node_id, "results": results, "map_attempts_used": senders,
                "map_attempts_ignored": sorted(a for a in attempts if a not in accepted),
                "duration_ms": round((time.time() - started) * 1000, 2)}


def create_datanode_router(dn: DataNode):
    from fastapi import APIRouter, Body, HTTPException

    router = APIRouter(prefix="/orbitfs")

    @router.post("/chunk")
    async def put_chunk(body: Dict[str, Any] = Body(...)):
        try:
            return await dn.store(body)
        except (RuntimeError, ValueError) as exc:
            raise HTTPException(503 if isinstance(exc, RuntimeError) else 422, str(exc))

    @router.get("/chunk/{cid}")
    async def get_chunk(cid: str):
        try:
            return dn.read(cid)
        except RuntimeError as exc:
            raise HTTPException(503, str(exc))
        except KeyError:
            raise HTTPException(404, f"chunk {cid} not here")

    @router.post("/replicate")
    async def replicate(body: Dict[str, Any] = Body(...)):
        try:
            return await dn.replicate(body["chunk_id"], body["to"])
        except KeyError:
            raise HTTPException(404, "chunk not here")
        except Exception as exc:
            raise HTTPException(503, str(exc))

    @router.delete("/chunk/{cid}")
    async def delete_chunk(cid: str):
        return {"deleted": dn.delete(cid)}

    @router.get("/blocks")
    async def blocks():
        if dn.node.transport.silent:
            raise HTTPException(503, "satellite is silent")
        return dn.block_report()

    @router.post("/mapreduce/map")
    async def mr_map(body: Dict[str, Any] = Body(...)):
        try:
            return await dn.run_map(body)
        except KeyError as exc:
            raise HTTPException(404, f"chunk {exc} not here")
        except Exception as exc:
            raise HTTPException(503, str(exc))

    @router.post("/mapreduce/shuffle")
    async def mr_shuffle(body: Dict[str, Any] = Body(...)):
        if dn.node.transport.silent:
            raise HTTPException(503, "satellite is silent")
        return dn.accept_shuffle(body)

    @router.post("/mapreduce/reduce")
    async def mr_reduce(body: Dict[str, Any] = Body(...)):
        try:
            return dn.run_reduce(body)
        except Exception as exc:
            raise HTTPException(503, str(exc))

    return router
