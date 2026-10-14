"""
Phase 5 (CAP demo) on five in-process satellites:
- CP command ledger: commits need 3 of 5 signatures; the minority side of a partition refuses writes;
  after healing, lagging satellites catch up; tampering is detected and repaired.
- AP status board: both sides of a partition accept writes; after healing the vector clocks expose the
  concurrent writes as a conflict on every satellite; a resolution clears it everywhere.
"""

import asyncio

import pytest

from satellites.dsync.ledger import verify_chain
from tests.test_fa2_algorithms import Cluster, until

GROUPS = [["SAT-01", "SAT-02", "SAT-03"], ["SAT-04", "SAT-05"]]


async def elect(c, starter, expect):
    await c[starter].election.start("bully", run_id=f"lead-{starter}")
    assert await until(lambda: c[starter].election.leader == expect, timeout=5)


def partition(c):
    for n in c.nodes.values():
        n.apply_fault("PARTITION", {"groups": GROUPS})


async def heal(c):
    for n in c.nodes.values():
        n.apply_fault("HEAL", {})
    await asyncio.sleep(0.8)  # _after_heal pushes board + ledger catch-up


@pytest.mark.asyncio
async def test_ledger_commits_with_majority_and_refuses_on_minority_side():
    c = Cluster()
    await c.beacon_round()  # spreads public keys
    await elect(c, "SAT-01", "SAT-05")
    r = await c["SAT-05"].ledger.submit({"action": "SET_POWER_MODE", "target": "SAT-02", "params": {"mode": "POWER_SAVING"}})
    assert r["status"] == "COMMITTED" and r["signatures"] == 5
    assert await until(lambda: all(len(n.ledger.chain) == 1 for n in c.nodes.values()))

    partition(c)
    await elect(c, "SAT-01", "SAT-03")          # majority side elects its own leader
    maj = await c["SAT-03"].ledger.submit({"action": "SCHEDULE_DOWNLINK", "target": "SAT-01", "params": {"window": "12:00"}})
    mino = await c["SAT-05"].ledger.submit({"action": "SCHEDULE_DOWNLINK", "target": "SAT-04", "params": {"window": "12:05"}})
    assert maj["status"] == "COMMITTED" and maj["signatures"] == 3
    assert mino["status"] == "REJECTED_NO_QUORUM" and mino["signatures"] == 2
    assert len(c["SAT-04"].ledger.chain) == 1   # minority did not diverge

    await heal(c)
    await c.beacon_round()                       # beacons advertise the longer chain -> catch-up
    assert await until(lambda: len({n.ledger.tip() for n in c.nodes.values()}) == 1, timeout=5)
    keys = c["SAT-01"].ledger.pubkeys()
    for n in c.nodes.values():
        assert verify_chain(n.ledger.chain, keys)["valid"]
    assert c["SAT-02"].ledger.applied[0]["action"] == "SET_POWER_MODE"


@pytest.mark.asyncio
async def test_tampered_block_is_detected_and_repaired_from_peers():
    c = Cluster()
    await c.beacon_round()
    await elect(c, "SAT-01", "SAT-05")
    for i in range(3):
        await c["SAT-05"].ledger.submit({"action": "RESET_FAULTS", "target": f"SAT-0{i + 1}"})
    assert await until(lambda: all(len(n.ledger.chain) == 3 for n in c.nodes.values()))
    node = c["SAT-02"]
    node.ledger.tamper(1)
    check = verify_chain(node.ledger.chain, node.ledger.pubkeys())
    assert check["valid"] is False and check["bad_index"] == 1
    res = await node.ledger.repair()
    assert res["repaired"] and verify_chain(node.ledger.chain, node.ledger.pubkeys())["valid"]
    assert node.ledger.tip() == c["SAT-05"].ledger.tip()


@pytest.mark.asyncio
async def test_status_board_accepts_writes_on_both_sides_and_detects_conflict():
    c = Cluster()
    await c.beacon_round()
    partition(c)
    a = await c["SAT-01"].board.put("downlink_window", "12:00 via Pune")
    b = await c["SAT-04"].board.put("downlink_window", "12:05 via Svalbard")
    assert a["accepted"] and b["accepted"]                       # AP: both sides stay writable
    assert c["SAT-02"].board.store["downlink_window"][0]["value"] == "12:00 via Pune"
    assert c["SAT-05"].board.store["downlink_window"][0]["value"] == "12:05 via Svalbard"

    await heal(c)
    for n in c.nodes.values():                                   # anti-entropy rounds
        for p in n.directory.live_ids():
            await n.board.push_to(p)
    for n in c.nodes.values():
        sibs = n.board.store["downlink_window"]
        assert len(sibs) == 2, f"{n.node_id} should see the conflict"
        assert sorted(v["value"] for v in sibs) == ["12:00 via Pune", "12:05 via Svalbard"]

    res = await c["SAT-03"].board.resolve("downlink_window", "merge")
    assert res["accepted"]
    for n in c.nodes.values():
        assert len(n.board.store["downlink_window"]) == 1
        assert "Pune" in n.board.store["downlink_window"][0]["value"] and "Svalbard" in n.board.store["downlink_window"][0]["value"]
