"""
FA-2 Phase 3-5 gate probe against the LIVE system (run scripts/fa2_phase2_probe.py first for Phase 1-2).
Exit code 0 = every check passed.

    python scripts/fa2_full_probe.py [--base-url http://localhost:8080]
"""

import argparse
import base64
import os
import sys
import time

import httpx

FAILURES = []


def check(name, ok, detail=""):
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    if not ok:
        FAILURES.append(name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:8080")
    c = httpx.Client(base_url=ap.parse_args().base_url.rstrip("/"), timeout=120.0)

    def post(path, body=None):
        r = c.post(path, json=body or {})
        if r.status_code >= 400:
            raise RuntimeError(f"{path}: HTTP {r.status_code} {r.text[:300]}")
        return r.json()

    def get(url, **params):
        return c.get(url, params=params).json()

    leader = get("/api/fa2/status")["agreed_leader"]
    print(f"Leader: {leader}")

    print("Phase 3: tasks + Chandy-Lamport snapshots")
    tasks = get("/api/fa2/tasks")["tasks"]
    check("every mission task has exactly one live owner", all(t["status"] == "RUNNING" for t in tasks),
          ", ".join(f"{t['task_id']}={t['current_owner']}" for t in tasks))
    post("/api/fa2/tasks/traffic", {"enabled": True})
    time.sleep(3)
    held, caught = True, 0
    for _ in range(3):
        s = post("/api/fa2/snapshot")
        held &= s["consistency"]["holds"]
        caught += len(s["tasks_in_transit"])
        time.sleep(0.8)
    post("/api/fa2/tasks/traffic", {"enabled": False})
    check("3 snapshots under handoff traffic all conserve the tasks", held, f"{caught} task(s) caught in transit")

    print("Phase 3: deadlock detection")
    cyc = post("/api/fa2/deadlock/run", {"mode": "cycle", "members": ["SAT-01", "SAT-02", "SAT-03"]})
    statuses = sorted(o["status"] for o in cyc["outcomes"].values())
    check("cycle detected and broken by aborting one victim",
          cyc["deadlock_detected"] and statuses == ["ABORTED_AS_VICTIM", "COMPLETED", "COMPLETED"],
          f"victim {cyc['victim']} after {cyc['detection_ms']} ms, {cyc['probes']['messages']} probe messages")
    chain = post("/api/fa2/deadlock/run", {"mode": "chain", "members": ["SAT-01", "SAT-02", "SAT-03"]})
    check("chain without cycle: no false alarm", not chain["deadlock_detected"]
          and all(o["status"] == "COMPLETED" for o in chain["outcomes"].values()),
          f"{chain['probes']['dropped']} probe(s) dropped at unblocked satellites")

    print("Phase 3: ground blackout")
    owners = {t["current_owner"] for t in get("/api/fa2/tasks")["tasks"]}
    leader = get("/api/fa2/status")["agreed_leader"]
    victim = sorted(o for o in owners if o and o != leader)[0]          # a task owner that is not the leader
    post("/api/fa2/blackout/start", {"seconds": 30, "crash": victim, "crash_after_s": 6})
    time.sleep(15)
    st = get("/api/fa2/blackout/status")
    check("satellites switched to autonomous mode", all(s["ground_ok"] is False for sid, s in st["satellites"].items()
                                                        if not s["silent"] and not s["unreachable"]))
    time.sleep(22)
    rep = get("/api/fa2/blackout/report")
    moved = rep.get("summary", {}).get("tasks_reassigned", [])
    check(f"during the blackout the satellites declared {victim} dead and moved its task, reported afterwards",
          victim in rep["summary"]["satellites_declared_dead"] and any(m.get("from") == victim for m in moved)
          and rep["summary"]["delivered_only_after_ground_returned"] > 0,
          f"{rep['summary']['events_during_blackout']} events, {len(moved)} task move(s), "
          f"{rep['summary']['berkeley_rounds']} Berkeley round(s)")
    post("/api/fa2/faults/recover", {"target": victim})
    time.sleep(8)

    print("Phase 4: OrbitFS + MapReduce + serverless + objects + gateway")
    data = os.urandom(200_000)
    w = post("/api/orbitfs/files", {"path": "images/probe.bin", "content_b64": base64.b64encode(data).decode()})
    check("file written in chunks with 3 pipeline acks each", all(len(p["acks"]) == 3 for p in w["placement"]),
          f"{len(w['placement'])} chunks")
    holder = w["placement"][0]["acks"][0]
    post("/api/fa2/faults/crash", {"target": holder})
    healed = False
    for _ in range(10):
        time.sleep(2)
        if get("/api/orbitfs/files/info", path="images/probe.bin")["under_replicated"] == 0:
            healed = True
            break
    v = get("/api/orbitfs/files/verify", path="images/probe.bin")
    check(f"after crashing {holder}: chunks re-replicated and file reads back intact", healed and v["matches_original"])
    post("/api/fa2/faults/recover", {"target": holder})
    post("/api/mapreduce/archive")
    job = post("/api/mapreduce/jobs", {"job": "health_stats"})
    check("MapReduce job ran data-local on satellites", job["counters"]["map_tasks"] == job["counters"]["data_local_map_tasks"] > 0,
          f"{job['chunks']} chunks, reducers {job['reducers']}, {job['phases_ms']['total']} ms")
    inv = get("/api/serverless/invocations")["invocations"]
    check("serverless functions were triggered by events", any(i["trigger"].startswith("event:") for i in inv),
          ", ".join(sorted({i['function'] for i in inv})))
    r1 = post("/api/objects/call", {"name": "satellite.SAT-03.payload", "method": "capture"})
    r2 = post("/api/objects/call", {"name": "satellite.SAT-03.payload", "method": "capture"})
    check("Pyro remote object keeps state between calls", r2["result"]["total_captures"] == r1["result"]["total_captures"] + 1)
    gw = c.get("/api/satellites")
    check("request went through the Nginx gateway", gw.headers.get("X-Gateway") is not None, gw.headers.get("X-Upstream") or "")

    print("Phase 5: CAP")
    post("/api/fa2/faults/partition", {"groups": [["SAT-01", "SAT-02", "SAT-03"], ["SAT-04", "SAT-05"]]})
    time.sleep(10)
    leaders = get("/api/fa2/cap/status")["leaders"]
    maj = next((s for s in ("SAT-01", "SAT-02", "SAT-03") if leaders.get(s) == s), None)
    mino = next((s for s in ("SAT-04", "SAT-05") if leaders.get(s) == s), None)
    a = c.post("/api/fa2/ledger/submit", json={"via": maj, "action": "RESET_FAULTS", "target": "SAT-01"}).json()
    b = c.post("/api/fa2/ledger/submit", json={"via": mino, "action": "RESET_FAULTS", "target": "SAT-04"}).json()
    check("ledger: majority side commits, minority side refuses", a.get("status") == "COMMITTED" and b.get("status") == "REJECTED_NO_QUORUM",
          f"{maj}: {a.get('signatures')} sigs, {mino}: {b.get('signatures')} sigs")
    post("/api/fa2/board/put", {"via": "SAT-01", "key": "probe_key", "value": "A"})
    post("/api/fa2/board/put", {"via": "SAT-04", "key": "probe_key", "value": "B"})
    post("/api/fa2/faults/heal")
    time.sleep(8)
    board = get("/api/fa2/board")["satellites"]
    check("board: both writes accepted and seen as a conflict everywhere after healing",
          all(len(s["keys"].get("probe_key", [])) == 2 for s in board.values()))
    post("/api/fa2/board/resolve", {"via": "SAT-02", "key": "probe_key", "strategy": "merge"})
    time.sleep(2)
    lv = get("/api/fa2/ledger")
    check("all ledger copies valid and identical after healing",
          all(cp["verification"]["valid"] and cp["agrees_with_majority"] for cp in lv["copies"].values() if cp.get("reachable")))

    print()
    if FAILURES:
        print(f"{len(FAILURES)} check(s) failed: {FAILURES}")
        sys.exit(1)
    print("All FA-2 Phase 3-5 gate checks passed.")


if __name__ == "__main__":
    main()
