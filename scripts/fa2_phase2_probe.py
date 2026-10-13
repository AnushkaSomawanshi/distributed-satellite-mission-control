"""
FA-2 Phase 1 + 2 gate probe: runs every algorithm against the LIVE system (Mission Control + 5
satellites) and checks its guarantee from the measured results. Exit code 0 = all gates passed.

    python scripts/fa2_phase2_probe.py [--base-url http://localhost:8000]
"""

import argparse
import json
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
    ap.add_argument("--base-url", default="http://localhost:8000")
    base = ap.parse_args().base_url.rstrip("/")
    c = httpx.Client(base_url=base, timeout=120.0)

    def post(path, body=None):
        r = c.post(path, json=body or {})
        if r.status_code >= 400:
            raise RuntimeError(f"{path}: HTTP {r.status_code} {r.text[:300]}")
        return r.json()

    print("Phase 1: satellites, clocks, events")
    end = time.time() + 40
    status = {}
    while time.time() < end:
        status = c.get("/api/fa2/status").json()
        if len(status["leader_by_satellite"]) == 5 and status["agreed_leader"]:
            break
        time.sleep(1)
    check("5 satellites respond on /dsync/state", len(status.get("leader_by_satellite", {})) == 5, json.dumps(status.get("leader_by_satellite")))
    check("satellites agreed on a leader by themselves at start-up", bool(status.get("agreed_leader")), str(status.get("agreed_leader")))

    post("/api/fa2/faults/clock-drift", {"target": "SAT-02", "offset_ms": -900})
    run = post("/api/fa2/lens/send", {"source": "SAT-01", "dest": "SAT-02", "run_id": "probe-lens"})
    check("cross-link delivered", run.get("delivered") is True)
    time.sleep(1.5)
    ev = c.get("/api/fa2/events", params={"run_id": "probe-lens"}).json()["events"]
    send = next((e for e in ev if e["kind"] == "SEND"), None)
    recv = next((e for e in ev if e["kind"] == "RECV"), None)
    check("events collected from both satellites", bool(send and recv), f"{len(ev)} events")
    if send and recv:
        check("drift makes physical time show RECV before SEND", recv["phys_ts"] < send["phys_ts"],
              f"send {send['phys_ts']:.3f} recv {recv['phys_ts']:.3f}")
        check("Lamport keeps SEND before RECV", recv["lamport"] > send["lamport"], f"{send['lamport']} -> {recv['lamport']}")

    print("Phase 2: clock synchronisation")
    for sid, off in {"SAT-01": 400, "SAT-03": 250, "SAT-04": -150, "SAT-05": 700}.items():
        post("/api/fa2/faults/clock-drift", {"target": sid, "offset_ms": off})
    b = post("/api/fa2/clocks/berkeley")
    check("Berkeley shrinks the spread of the satellites' clocks",
          b["spread_after_ms"] is not None and b["spread_after_ms"] < 50 < b["spread_before_ms"],
          f"spread {b['spread_before_ms']} ms -> {b['spread_after_ms']} ms (daemon {b['daemon']})")
    cr = post("/api/fa2/clocks/cristian")
    check("Cristian brings every clock close to true time", cr["max_abs_skew_after_ms"] is not None and cr["max_abs_skew_after_ms"] < 50,
          f"max |skew| {cr['max_abs_skew_before_ms']} ms -> {cr['max_abs_skew_after_ms']} ms")

    print("Phase 2: elections")
    for algo in ("bully", "ring"):
        r = post("/api/fa2/election/run", {"algorithm": algo, "initiator": "SAT-01"})
        check(f"{algo}: all satellites agree on one leader", r["status"] == "AGREED",
              f"leader {(r.get('agreement') or {}).get('leader')}, {r['messages']} messages, {r['agreement_observed_ms']} ms")
    r = post("/api/fa2/election/leader-failure", {"algorithm": "bully"})
    check("leader crash: survivors detect it and elect a new leader without Mission Control deciding",
          r["status"] == "NEW_LEADER_AGREED" and r["agreement"]["leader"] != r["failed_leader"],
          f"{r['failed_leader']} -> {(r.get('agreement') or {}).get('leader')} in {r['time_to_new_leader_ms']} ms "
          f"(detected after {r['detection_ms']} ms)")
    time.sleep(6)

    print("Phase 2: mutual exclusion arena")
    for algo in ("centralised", "ricart_agrawala", "token_ring", "lodha_kshemkalyani"):
        r = post("/api/fa2/arena/mutex", {"algorithm": algo, "rounds": 2, "hold_ms": 50})
        check(f"{algo}: all 10 requests served, no overlap",
              r["entries"] == 10 and not r["safety_violations"] and not r["errors"],
              f"{r['messages_per_entry']} msgs/entry, avg wait {r['avg_wait_ms']} ms, fairness inversions {r['fairness_inversions']}")

    print("Phase 1: partition enforced by satellites")
    post("/api/fa2/faults/partition", {"groups": [["SAT-01", "SAT-02", "SAT-03"], ["SAT-04", "SAT-05"]]})
    r = c.post("/api/fa2/lens/send", json={"source": "SAT-01", "dest": "SAT-04"}).json()
    check("SAT-01 cannot reach SAT-04 across the partition", r.get("delivered") is False, str(r.get("reason")))
    post("/api/fa2/faults/heal")
    r = post("/api/fa2/lens/send", {"source": "SAT-01", "dest": "SAT-04"})
    check("after HEAL the link works again", r.get("delivered") is True)

    print()
    if FAILURES:
        print(f"{len(FAILURES)} check(s) failed: {FAILURES}")
        sys.exit(1)
    print("All FA-2 Phase 1 + 2 gate checks passed.")


if __name__ == "__main__":
    main()
