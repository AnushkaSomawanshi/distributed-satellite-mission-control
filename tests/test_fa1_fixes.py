"""Regression tests for the FA-1 fixes: telemetry pipeline, liveness separation and gossip peer selection."""

import time

import pytest

from backend.registry.service_registry import SatelliteRegistry
from satellites.satellite_node import SatelliteNode, GOSSIP_MAX_HOPS
from satellites.telemetry_publisher import TelemetryPublisher


def _registry_with(sat_id="SAT-01"):
    reg = SatelliteRegistry()
    reg.register(sat_id, f"NODE-{sat_id}", "host", "127.0.0.1", 5001, 6001)
    return reg


def test_telemetry_metrics_update_does_not_refresh_liveness():
    reg = _registry_with()
    entry = reg.lookup("SAT-01")
    entry.last_heartbeat = time.time() - 30  # node has been silent for 30s
    entry.status = "DISCONNECTED"

    reg.update_metrics("SAT-01", health_score=80, battery=55, temperature=30,
                       cpu_usage=20, memory_usage=40, signal_strength=90)

    entry = reg.lookup("SAT-01")
    assert entry.battery == 55
    assert entry.status == "DISCONNECTED", "a broker message must not resurrect a dead node"
    assert time.time() - entry.last_heartbeat >= 29


def test_telemetry_for_unregistered_satellite_is_ignored():
    reg = SatelliteRegistry()
    assert reg.update_metrics("SAT-99", 1, 1, 1, 1, 1, 1) is None
    assert reg.lookup("SAT-99") is None


def _node(sat_id="SAT-01"):
    return SatelliteNode(sat_id, 5001, 6001, "http://127.0.0.1:1", rabbitmq_url=None)


def test_gossip_candidates_exclude_self_path_and_dead_peers():
    node = _node()
    node.peers = {
        "SAT-02": {"address": "satellite-02", "p2p_port": 6002, "status": "HEALTHY"},
        "SAT-03": {"address": "satellite-03", "p2p_port": 6003, "status": "DISCONNECTED"},
        "SAT-04": {"address": "satellite-04", "p2p_port": 6004, "status": "HEALTHY"},
    }
    assert node._gossip_candidates(exclude=["SAT-01", "SAT-04"]) == ["SAT-02"]


@pytest.mark.asyncio
async def test_gossip_stops_at_hop_limit_and_with_no_peers():
    node = _node()
    packet = node.build_gossip_packet()
    assert await node.propagate_gossip(packet) is False  # no peers known yet
    packet["hops"] = GOSSIP_MAX_HOPS
    node.peers = {"SAT-02": {"address": "127.0.0.1", "p2p_port": 1, "status": "HEALTHY"}}
    assert await node.propagate_gossip(packet) is False  # hop limit reached, nothing sent


def test_gossip_packet_carries_real_node_state():
    node = _node("SAT-03")
    packet = node.build_gossip_packet()
    assert packet["origin_satellite_id"] == "SAT-03"
    assert packet["origin_battery"] == round(node.battery, 2)
    assert packet["hops"] == 0 and packet["path"] == []


@pytest.mark.asyncio
async def test_publisher_without_broker_or_registry_reports_failure():
    pub = TelemetryPublisher("SAT-01", rabbitmq_url=None, registry_url="http://127.0.0.1:1")
    result = await pub.publish({"satellite_id": "SAT-01", "sequence_number": 1})
    assert result == "FAILED"
    assert pub.stats()["failed_publishes"] == 1
    assert pub.stats()["broker_connected"] is False
