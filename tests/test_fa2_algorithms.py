"""
FA-2 Phase 1 + 2: each algorithm's core guarantee, checked on five real DsyncNode instances that
exchange messages over an in-process network (same code that runs inside the satellite processes).
"""

import asyncio
import time

import pytest

from satellites.dsync import DsyncNode, PeerUnreachable, VectorClock
from satellites.dsync.mutex import ALGORITHMS
from satellites.dsync.testing import InMemoryNetwork

IDS = ["SAT-01", "SAT-02", "SAT-03", "SAT-04", "SAT-05"]


class Cluster:
    def __init__(self, health=None):
        self.net = InMemoryNetwork()
        self.now = [1000.0]  # fake monotonic clock for beacon liveness
        self.health = {i: 90.0 for i in IDS}
        self.health.update(health or {})
        self.nodes = {}
        for n, sid in enumerate(IDS, start=1):
            node = DsyncNode(sid, info=lambda sid=sid, n=n: {"address": "sim", "p2p_port": 6000 + n,
                                                             "health": self.health[sid], "position": None},
                             network=self.net, directory_clock=lambda: self.now[0])
            self.net.attach(node, "sim", 6000 + n)
            self.nodes[sid] = node
        for sid, node in self.nodes.items():
            for m, other in enumerate(IDS, start=1):
                if other != sid:
                    node.directory.upsert(other, "sim", 6000 + m)

    def __getitem__(self, sid):
        return self.nodes[sid]

    def alive(self):
        return [n for sid, n in self.nodes.items() if sid not in self.net.down]

    async def beacon_round(self):
        await asyncio.gather(*(n.beacons.beacon_round() for n in self.alive()))

    async def kill(self, sid):
        self.net.down.add(sid)
        self.now[0] += 6.0  # longer than DEAD_AFTER
        await self.beacon_round()

    def events(self):
        return [e for n in self.nodes.values() for e in n.reporter.local]


async def until(pred, timeout=10.0):
    end = time.time() + timeout
    while time.time() < end:
        if pred():
            return True
        await asyncio.sleep(0.02)
    return False


async def agreed_leader(cluster):
    views = {(n.election.leader, n.election.term) for n in cluster.alive()}
    return views.pop() if len(views) == 1 else None


# ------------------------------------------------------------------ logical clocks
@pytest.mark.asyncio
async def test_lamport_and_vector_clocks_capture_causality():
    c = Cluster()
    await c.beacon_round()
    await c["SAT-01"].transport.send("SAT-02", "CROSSLINK", {}, algo="lens")
    await c["SAT-02"].transport.send("SAT-03", "CROSSLINK", {}, algo="lens")
    e4 = c["SAT-04"].transport.local_event("X", algo="lens")
    e5 = c["SAT-05"].transport.local_event("Y", algo="lens")

    sends = [e for e in c.events() if e["kind"] == "SEND" and e.get("algo") == "lens"]
    recvs = {e["msg_id"]: e for e in c.events() if e["kind"] == "RECV" and e.get("algo") == "lens"}
    for s in sends:
        r = recvs[s["msg_id"]]
        assert s["lamport"] < r["lamport"]
        assert VectorClock.compare(s["vector"], r["vector"]) == "BEFORE"
    first, last = sends[0], recvs[sends[1]["msg_id"]]
    assert VectorClock.compare(first["vector"], last["vector"]) == "BEFORE"   # transitive: 01 -> 02 -> 03
    assert VectorClock.compare(e4["vector"], e5["vector"]) == "CONCURRENT"


@pytest.mark.asyncio
async def test_clock_drift_misorders_physical_time_but_not_lamport():
    c = Cluster()
    await c.beacon_round()
    c["SAT-02"].apply_fault("CLOCK_DRIFT", {"offset_ms": -800})
    await c["SAT-01"].transport.send("SAT-02", "CROSSLINK", {}, algo="lens")
    send = next(e for e in c["SAT-01"].reporter.local if e["kind"] == "SEND" and e.get("algo") == "lens")
    recv = next(e for e in c["SAT-02"].reporter.local if e["kind"] == "RECV" and e.get("algo") == "lens")
    assert recv["phys_ts"] < send["phys_ts"]          # receive appears to happen before the send
    assert recv["lamport"] > send["lamport"]          # Lamport keeps the causal order


# ------------------------------------------------------------------ faults enforced by satellites
@pytest.mark.asyncio
async def test_partition_and_crash_are_enforced_by_satellites():
    c = Cluster()
    await c.beacon_round()
    groups = [["SAT-01", "SAT-02", "SAT-03"], ["SAT-04", "SAT-05"]]
    for n in c.nodes.values():
        n.apply_fault("PARTITION", {"groups": groups})
    with pytest.raises(PeerUnreachable):
        await c["SAT-01"].transport.send("SAT-04", "CROSSLINK", {})
    await c["SAT-01"].transport.send("SAT-02", "CROSSLINK", {})  # same side still works
    for n in c.nodes.values():
        n.apply_fault("HEAL", {})
    await c["SAT-01"].transport.send("SAT-04", "CROSSLINK", {})

    c["SAT-03"].apply_fault("CRASH", {})
    with pytest.raises(PeerUnreachable):
        await c["SAT-01"].transport.send("SAT-03", "CROSSLINK", {})
    c["SAT-03"].apply_fault("RECOVER", {})
    await c["SAT-01"].transport.send("SAT-03", "CROSSLINK", {})


@pytest.mark.asyncio
async def test_beacons_detect_dead_peer_without_mission_control():
    c = Cluster()
    await c.beacon_round()
    assert set(c["SAT-01"].directory.live_ids()) == {"SAT-02", "SAT-03", "SAT-04", "SAT-05"}
    await c.kill("SAT-03")
    assert "SAT-03" not in c["SAT-01"].directory.live_ids()
    assert any(e.get("label") == "PEER_DEAD" for e in c["SAT-01"].reporter.local)


# ------------------------------------------------------------------ election
@pytest.mark.asyncio
@pytest.mark.parametrize("algorithm", ["bully", "ring"])
async def test_election_unique_leader_and_reelection_after_leader_failure(algorithm):
    c = Cluster(health={"SAT-05": 25.0})  # SAT-05 is unhealthy, so SAT-04 has the highest priority
    for n in c.nodes.values():
        n.election.default_algorithm = algorithm
    await c.beacon_round()
    await c["SAT-01"].election.start(algorithm, run_id="t1")
    assert await until(lambda: asyncio.get_event_loop() and len({(n.election.leader, n.election.term) for n in c.alive()}) == 1
                       and c["SAT-01"].election.leader is not None)
    leader, term = c["SAT-01"].election.leader, c["SAT-01"].election.term
    assert leader == "SAT-04"

    await c.kill("SAT-04")  # survivors detect it through beacons and re-elect by themselves
    assert await until(lambda: all(n.election.leader == "SAT-03" for n in c.alive()), timeout=15)
    assert all(n.election.term > term for n in c.alive())
    assert len({n.election.term for n in c.alive()}) == 1


# ------------------------------------------------------------------ clock synchronisation
@pytest.mark.asyncio
async def test_berkeley_converges_clocks_and_cristian_tracks_true_time():
    c = Cluster()
    offsets = {"SAT-01": 400, "SAT-02": -300, "SAT-03": 150, "SAT-04": -50, "SAT-05": 900}
    for sid, off in offsets.items():
        c[sid].apply_fault("CLOCK_DRIFT", {"offset_ms": off})
    await c.beacon_round()
    await c["SAT-01"].election.start("bully", run_id="lead")
    assert await until(lambda: c["SAT-05"].election.leader == "SAT-05" and c["SAT-01"].election.leader == "SAT-05")

    report = await c["SAT-05"].clocksync.berkeley("b1")
    assert report["spread_before_ms"] > 1000
    assert report["spread_after_ms"] < 25
    skews = [n.physical.skew_ms() for n in c.nodes.values()]
    assert max(skews) - min(skews) < 25

    async def server_time():
        return time.time()
    for n in c.nodes.values():
        rec = await n.clocksync.cristian(server_time)
        assert abs(rec["skew_after_ms"]) <= rec["error_bound_ms"] + 5


# ------------------------------------------------------------------ mutual exclusion
def cs_intervals(events, run_id):
    opened, intervals = {}, []
    for e in sorted(events, key=lambda e: e["true_ts"]):
        if e.get("run_id") != run_id:
            continue
        if e.get("label") == "CS_ENTER":
            opened[e["node"]] = e
        elif e.get("label") == "CS_EXIT":
            start = opened.pop(e["node"])
            intervals.append((start["true_ts"], e["true_ts"], e["node"], start["detail"]["request_lamport"]))
    return intervals


async def run_mutex(c, algo, run_id, rounds=3):
    if algo == "centralised":
        await c["SAT-01"].election.start("bully", run_id="lead")
        assert await until(lambda: all(n.election.leader == "SAT-05" for n in c.alive()))
    if algo == "token_ring":
        for sid, n in c.nodes.items():
            n.mutex.token_control("start", run_id, IDS, create=(sid == "SAT-01"))
    start_at = time.time() + 0.05
    results = await asyncio.gather(*(n.mutex.run_rounds(algo, run_id, rounds, 5, start_at) for n in c.nodes.values()))
    if algo == "token_ring":
        for n in c.nodes.values():
            n.mutex.token_control("stop", run_id)
    return results


@pytest.mark.asyncio
@pytest.mark.parametrize("algo", ALGORITHMS)
async def test_mutual_exclusion_safety_and_liveness(algo):
    c = Cluster()
    await c.beacon_round()
    results = await run_mutex(c, algo, f"mx-{algo}")
    assert all("error" not in r for res in results for r in res), results
    intervals = cs_intervals(c.events(), f"mx-{algo}")
    assert len(intervals) == 15  # 5 satellites x 3 rounds, all served
    intervals.sort()
    for (s1, e1, n1, _), (s2, e2, n2, _) in zip(intervals, intervals[1:]):
        assert s2 >= e1, f"{n1} and {n2} overlapped in the critical section"


def messages_per_entry(c, algo, run_id):
    sends = [e for e in c.events() if e["kind"] == "SEND" and e.get("algo") == algo and e.get("run_id") == run_id]
    return len(sends) / len(cs_intervals(c.events(), run_id))


@pytest.mark.asyncio
async def test_lodha_kshemkalyani_uses_no_more_messages_than_ricart_agrawala():
    c1, c2 = Cluster(), Cluster()
    await c1.beacon_round()
    await c2.beacon_round()
    await run_mutex(c1, "ricart_agrawala", "ra")
    await run_mutex(c2, "lodha_kshemkalyani", "lk")
    ra, lk = messages_per_entry(c1, "ricart_agrawala", "ra"), messages_per_entry(c2, "lodha_kshemkalyani", "lk")
    assert ra == pytest.approx(8.0)       # 2(N-1) with N = 5
    assert 4.0 <= lk <= ra                # between N-1 and 2(N-1)


@pytest.mark.asyncio
@pytest.mark.parametrize("algo", ["ricart_agrawala", "lodha_kshemkalyani"])
async def test_timestamp_fairness(algo):
    c = Cluster()
    await c.beacon_round()
    await run_mutex(c, algo, "fair")
    events = [e for e in c.events() if e.get("run_id") == "fair"]
    requests = {}
    for e in sorted(events, key=lambda e: e["true_ts"]):
        if e.get("label") == "CS_REQUEST":
            requests.setdefault(e["node"], []).append(e)
    entries = sorted((e for e in events if e.get("label") == "CS_ENTER"), key=lambda e: e["true_ts"])
    # whenever a satellite enters, no satellite with an OLDER (smaller Lamport, ID) request may still be waiting
    for ent in entries:
        mine = (ent["detail"]["request_lamport"], ent["node"])
        for other in entries:
            theirs = (other["detail"]["request_lamport"], other["node"])
            other_req = next(r for r in requests[other["node"]] if r["lamport"] == other["detail"]["request_lamport"])
            if theirs < mine and other_req["true_ts"] < ent["true_ts"] < other["true_ts"]:
                pytest.fail(f"{ent['node']} {mine} entered before older waiting request {other['node']} {theirs}")
