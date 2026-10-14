"""
FA-2 Phase 3 guarantees on five in-process satellites:
- Chandy-Lamport: every task appears exactly once in (satellite states + channel states).
- Task redistribution: a dead owner's tasks move to a capable satellite; a returning satellite's
  stale copy is revoked, so no task runs twice.
- Chandy-Misra-Haas: a real cycle is detected and broken (youngest request aborts); a chain without
  a cycle completes with no false alarm.
- Ground blackout: events stay buffered on the satellite until the ground is back.
"""

import asyncio
import time

import pytest

from backend.fa2_extensions.catalog import MISSION_TASKS, TASKS_BY_ID, capable
from tests.test_fa2_algorithms import Cluster, until

ALL_TASKS = {t["task_id"] for t in MISSION_TASKS}


def fast(c):
    for n in c.nodes.values():
        n.beacons.interval = 0.1
        n.tasks.handoff_every = (0.03, 0.08)
        n.tasks.link_delay = (0.04, 0.15)
        n.deadlock.probe_after = 0.25
    return c


def owners(c):
    out = {}
    for sid, n in c.nodes.items():
        if sid in c.net.down:
            continue
        for tid in n.tasks.owned:
            out.setdefault(tid, []).append(sid)
    return out


@pytest.mark.asyncio
async def test_initial_tasks_are_owned_once_by_capable_satellites():
    c = Cluster()
    own = owners(c)
    assert set(own) == ALL_TASKS
    for tid, sats in own.items():
        assert len(sats) == 1 and capable(sats[0], TASKS_BY_ID[tid])


@pytest.mark.asyncio
async def test_chandy_lamport_snapshot_conserves_tasks_under_handoff_traffic():
    c = fast(Cluster())
    await c.beacon_round()
    loops = [asyncio.ensure_future(n.tasks.run()) for n in c.nodes.values()]
    for n in c.nodes.values():
        n.tasks.traffic = True
    in_channel_seen = 0
    try:
        for k in range(6):
            await asyncio.sleep(0.25)
            snap_id = f"snap-{k}"
            await c["SAT-0%d" % (k % 5 + 1)].snapshots.start(snap_id)
            done = lambda: all(snap_id in n.snapshots.snaps and n.snapshots.snaps[snap_id]["done"] for n in c.nodes.values())
            assert await until(done, timeout=5)
            pieces = [n.snapshots.piece(snap_id) for n in c.nodes.values()]
            assert all(p["complete"] for p in pieces)
            on_sats = [t["task_id"] for p in pieces for t in p["state"]["tasks"]]
            in_channels = [m["payload"]["task"]["task_id"] for p in pieces for msgs in p["channels"].values()
                           for m in msgs if m["msg_type"] == "TASK_HANDOFF"]
            in_channel_seen += len(in_channels)
            everything = on_sats + in_channels
            assert sorted(everything) == sorted(ALL_TASKS), f"snapshot {snap_id}: {on_sats} + in transit {in_channels}"
    finally:
        for n in c.nodes.values():
            n.tasks.traffic = False
        for l in loops:
            l.cancel()
    assert in_channel_seen > 0, "expected at least one task to be caught in transit across 6 snapshots"


@pytest.mark.asyncio
async def test_leader_redistributes_dead_owners_tasks_and_fences_stale_copy():
    c = fast(Cluster())
    await c.beacon_round()
    await c["SAT-01"].election.start("bully", run_id="lead")
    assert await until(lambda: all(n.election.leader == "SAT-05" for n in c.alive()))
    await c.beacon_round()  # leader learns who owns what

    await c.kill("SAT-02")  # owns T-048 (THERMAL): only SAT-03 / SAT-05 can take it
    assert await until(lambda: owners(c).get("T-048") and owners(c)["T-048"][0] in ("SAT-03", "SAT-05"))
    new_owner = owners(c)["T-048"][0]
    assert c[new_owner].tasks.owned["T-048"]["version"] == 2

    c.net.down.discard("SAT-02")  # SAT-02 returns, still holding version 1
    assert "T-048" in c["SAT-02"].tasks.owned
    await c.beacon_round()
    assert await until(lambda: "T-048" not in c["SAT-02"].tasks.owned)
    own = owners(c)
    assert set(own) == ALL_TASKS and all(len(v) == 1 for v in own.values()), own


@pytest.mark.asyncio
async def test_new_leader_takes_over_tasks_of_crashed_leader():
    c = fast(Cluster())
    await c.beacon_round()
    await c["SAT-01"].election.start("bully", run_id="lead")
    assert await until(lambda: all(n.election.leader == "SAT-05" for n in c.alive()))
    await c.beacon_round()
    await c.kill("SAT-05")  # leader and owner of T-050 (COMPUTE)
    assert await until(lambda: all(n.election.leader == "SAT-04" for n in c.alive()), timeout=10)
    await c.beacon_round()
    assert await until(lambda: "T-050" in owners(c), timeout=10)
    assert owners(c)["T-050"][0] in ("SAT-01", "SAT-03")  # capable of COMPUTE


@pytest.mark.asyncio
async def test_chandy_misra_haas_detects_and_breaks_a_cycle():
    c = fast(Cluster())
    await c.beacon_round()
    cycle = {"SAT-01": "SAT-02", "SAT-02": "SAT-03", "SAT-03": "SAT-01"}
    results = await asyncio.gather(*(c[s].deadlock.run_scenario(t, 50, "dl-cycle") for s, t in cycle.items()))
    statuses = {r["node"]: r["status"] for r in results}
    assert sorted(statuses.values()) == ["ABORTED_AS_VICTIM", "COMPLETED", "COMPLETED"], statuses
    detections = [e for e in c.events() if e.get("label") == "DEADLOCK_DETECTED"]
    assert detections
    victim = detections[0]["detail"]["victim"]
    assert statuses[victim] == "ABORTED_AS_VICTIM"
    assert set(detections[0]["detail"]["cycle"]) == set(cycle)


@pytest.mark.asyncio
async def test_chain_without_cycle_completes_with_no_false_alarm():
    c = fast(Cluster())
    await c.beacon_round()
    chain = {"SAT-01": "SAT-02", "SAT-02": "SAT-03", "SAT-03": None}
    results = await asyncio.gather(*(c[s].deadlock.run_scenario(t, 600, "dl-chain") for s, t in chain.items()))
    assert all(r["status"] == "COMPLETED" for r in results), results
    assert not [e for e in c.events() if e.get("label") == "DEADLOCK_DETECTED"]
    assert [e for e in c.events() if e.get("label") == "PROBE_DROPPED"]  # probes reached SAT-03, which is not blocked


@pytest.mark.asyncio
async def test_ground_blackout_buffers_events_until_restored():
    c = Cluster()
    node = c["SAT-01"]
    delivered = []

    async def sink(batch):
        if not node.ground_ok:
            return False
        delivered.extend(batch)
        return True
    node.reporter.sink = sink
    node.set_ground(False)
    node.transport.local_event("WORK_DURING_BLACKOUT")
    await node.reporter.flush()
    assert delivered == [] and len(node.reporter.pending) >= 2
    node.set_ground(True)
    await node.reporter.flush()
    labels = [e.get("label") for e in delivered]
    assert labels.index("GROUND_LOST") < labels.index("WORK_DURING_BLACKOUT") < labels.index("GROUND_RESTORED")


@pytest.mark.asyncio
async def test_recovered_satellite_does_not_declare_peers_dead_from_its_own_silence():
    c = fast(Cluster())
    await c.beacon_round()
    await c["SAT-01"].election.start("bully", run_id="lead")
    assert await until(lambda: all(n.election.leader == "SAT-05" for n in c.alive()))
    c["SAT-05"].apply_fault("CRASH", {})
    c.now[0] += 6.0  # time passes while SAT-05 hears nothing
    await asyncio.gather(*(n.beacons.beacon_round() for sid, n in c.nodes.items() if sid != "SAT-05"))
    c["SAT-05"].apply_fault("RECOVER", {})
    await c["SAT-05"].beacons.beacon_round()  # first round after recovery: must not kill anyone
    dead_from_05 = [e for e in c["SAT-05"].reporter.local
                    if e.get("label") == "PEER_DEAD" and e["true_ts"] > time.time() - 1]
    assert dead_from_05 == []
