"""Unit 4 building blocks: OrbitFS chunking, MapReduce map/reduce + attempt filtering, serverless cold/warm."""

import asyncio
import base64

import pytest

from backend.fa2.orbitfs import NameNode
from satellites.dsync.datanode import map_health_stats, reduce_health_stats, sha256
from tests.test_fa2_algorithms import Cluster

ROWS = [
    "timestamp,satellite_id,battery,temperature,cpu_usage,signal_strength,health_score,status",
    "1,SAT-01,90,25,20,95,100,HEALTHY",
    "2,SAT-01,20,26,20,95,60,WARNING",
    "3,SAT-02,80,50,20,95,90,HEALTHY",
]


def test_line_aligned_chunks_reassemble_and_never_split_a_record():
    data = ("\n".join(ROWS * 400) + "\n").encode()
    pieces = NameNode.split(data, line_aligned=True, chunk_size=1024)
    assert len(pieces) > 5
    assert b"".join(pieces) == data
    assert all(p.endswith(b"\n") for p in pieces)


def test_health_stats_map_and_reduce():
    part1 = map_health_stats(ROWS[:3])
    part2 = map_health_stats([ROWS[0], ROWS[3]])
    sat1 = reduce_health_stats([part1["SAT-01"]])
    assert sat1["samples"] == 2 and sat1["min_battery"] == 20 and sat1["anomalies"] == 1
    sat2 = reduce_health_stats([part2["SAT-02"]])
    assert sat2["max_temperature"] == 50 and sat2["anomalies"] == 1


@pytest.mark.asyncio
async def test_datanode_reduce_ignores_output_of_rejected_map_attempts():
    c = Cluster()
    dn = c["SAT-01"].datanode
    chunk = ("\n".join(ROWS) + "\n").encode()
    await dn.store({"chunk_id": "blk-1", "data_b64": base64.b64encode(chunk).decode(), "checksum": sha256(chunk)})
    me = [{"id": "SAT-01", "address": "sim", "port": 6001}]
    for attempt in ("job-a1", "job-a2"):   # the same chunk mapped twice (first attempt "failed")
        rep = await dn.run_map({"job_id": "job", "job": "health_stats", "attempt_id": attempt,
                                "chunk_ids": ["blk-1"], "reducers": me})
        assert rep["records"] == len(ROWS)
    out = dn.run_reduce({"job_id": "job", "job": "health_stats", "accepted_attempts": ["job-a2"]})
    assert out["results"]["SAT-01"]["samples"] == 2          # counted once, not twice
    assert out["map_attempts_ignored"] == ["job-a1"]


@pytest.mark.asyncio
async def test_datanode_rejects_corrupted_chunk():
    c = Cluster()
    with pytest.raises(ValueError):
        await c["SAT-02"].datanode.store({"chunk_id": "x", "data_b64": base64.b64encode(b"abc").decode(),
                                          "checksum": sha256(b"abd")})


@pytest.mark.asyncio
async def test_serverless_cold_then_warm_start_in_separate_process():
    import os
    from backend.fa2.serverless import runtime
    snap = {"snapshot_id": "s1", "tasks_on_satellites": [{"task_id": t} for t in ["T-047", "T-048", "T-049", "T-050"]],
            "tasks_in_transit": [{"task_id": "T-051"}], "consistency": {"holds": True}, "channel_states": {}}
    first = await runtime.invoke("snapshot_audit", {"type": "SNAPSHOT_COMPLETED", "snapshot": snap})
    second = await runtime.invoke("snapshot_audit", {"type": "SNAPSHOT_COMPLETED", "snapshot": snap})
    try:
        assert first["status"] == "OK" and first["cold_start"] is True and first["cold_start_ms"] > 0
        assert second["cold_start"] is False and second["pid"] == first["pid"]
        assert first["pid"] != os.getpid()
        assert first["result"]["independent_check_holds"] is True
    finally:
        runtime.shutdown()
        runtime.instances["snapshot_audit"].clear()
