# Copyright (c) Ultrone Contributors. All rights reserved.
"""Tests for the Cockpit API router and runtime integration."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.api.routers.cockpit import router as cockpit_router

test_app = FastAPI(title="Ultrone Cockpit Test API")
test_app.include_router(cockpit_router)


@pytest.fixture(scope="module")
def client():
    return TestClient(test_app)


def test_cockpit_status_and_truth(client):
    res = client.get("/api/cockpit/status")
    assert res.status_code == 200
    data = res.json()
    assert "run" in data
    assert "truth" in data
    assert data["truth"]["simulation_only"] is True
    assert data["truth"]["physical_actuation"] == "DISABLED"
    assert data["truth"]["environment"] == "SIMULATION"
    assert data["mcp_protocol"] == "2026-07-28"


def test_cockpit_overview(client):
    res = client.get("/api/cockpit/overview")
    assert res.status_code == 200
    data = res.json()
    assert "run" in data
    assert "realtime" in data
    assert "world" in data
    assert "policy" in data
    assert "devices" in data
    assert "events" in data
    assert "alerts" in data


def test_cockpit_world_snapshot(client):
    res = client.get("/api/cockpit/world")
    assert res.status_code == 200
    data = res.json()
    assert "ground_truth" in data
    assert "belief" in data
    assert "comparison" in data
    assert "sensors" in data
    assert len(data["ground_truth"]) > 0
    # Every comparison entity has both ground truth and belief comparison fields
    for comp in data["comparison"]:
        assert "entity_id" in comp
        assert "ground_truth" in comp
        assert "confidence" in comp


def test_cockpit_simulation_controls(client):
    # Step simulation
    res = client.post("/api/cockpit/control/step", json={"count": 2, "actor": "tester"})
    assert res.status_code == 200

    # Set speed
    res = client.post("/api/cockpit/control/speed", json={"speed": 2.0, "actor": "tester"})
    assert res.status_code == 200
    assert res.json()["speed"] == 2.0

    # Pause
    res = client.post("/api/cockpit/control/pause", json={"actor": "tester"})
    assert res.status_code == 200
    assert res.json()["running"] is False

    # Fault injection and clearance
    res = client.post(
        "/api/cockpit/control/faults",
        json={"config": {"telemetry_delay": ["sensor-01"]}, "actor": "tester"},
    )
    assert res.status_code == 200
    assert "sensor-01" in res.json()["faults"]["telemetry_delay"]

    res = client.post("/api/cockpit/control/clear-faults", json={"actor": "tester"})
    assert res.status_code == 200


def test_cockpit_agents(client):
    res = client.get("/api/cockpit/agents")
    assert res.status_code == 200
    data = res.json()
    assert "agents" in data
    assert "graph" in data
    assert len(data["agents"]) > 0

    first_agent_id = data["agents"][0]["agent_id"]
    detail_res = client.get(f"/api/cockpit/agents/{first_agent_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["agent_id"] == first_agent_id
    assert "grants" in detail
    assert "physical.execute" in detail["grants"]["denied"]


def test_cockpit_devices_and_fsm(client):
    res = client.get("/api/cockpit/devices")
    assert res.status_code == 200
    data = res.json()
    assert "devices" in data
    assert len(data["devices"]) > 0

    first_dev = data["devices"][0]
    dev_id = first_dev["device_id"]
    detail_res = client.get(f"/api/cockpit/devices/{dev_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["device_id"] == dev_id
    assert "fsm" in detail
    assert "allowed_transitions" in detail["fsm"]
    assert "transitions" in detail["fsm"]

    # Test FSM transition validation
    transition_res = client.post(
        f"/api/cockpit/devices/{dev_id}/transition",
        json={"target_state": "BUSY", "reason": "unit test", "actor": "tester"},
    )
    # Could be 200 or 409 depending on starting state, but must not be 500
    assert transition_res.status_code in (200, 409)


def test_cockpit_mcp_traffic_and_discovery(client):
    res = client.get("/api/cockpit/mcp/discovery")
    assert res.status_code == 200
    data = res.json()
    assert "capabilities" in data
    assert "discovery" in data
    assert data["discovery"]["protocol_version"] == "2026-07-28"

    traffic_res = client.get("/api/cockpit/mcp/traffic")
    assert traffic_res.status_code == 200
    assert isinstance(traffic_res.json(), list)


def test_cockpit_events_and_checkpoint(client):
    res = client.get("/api/cockpit/events?limit=20")
    assert res.status_code == 200
    events = res.json()
    assert isinstance(events, list)

    store_res = client.get("/api/cockpit/events/store")
    assert store_res.status_code == 200
    assert store_res.json()["chain_valid"] is True

    ckpt_res = client.post("/api/cockpit/events/checkpoint")
    assert ckpt_res.status_code == 200
    assert ckpt_res.json()["checkpoint_valid"] is True


def test_cockpit_safety_and_invariants(client):
    res = client.get("/api/cockpit/safety/status")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert "active_policies" in data

    invariants_res = client.get("/api/cockpit/safety/invariants")
    assert invariants_res.status_code == 200
    invs = invariants_res.json()
    inv_ids = [i["id"] for i in invs]
    for expected in ("SAF-001", "SAF-002", "SAF-003", "SAF-004", "SAF-005"):
        assert expected in inv_ids

    cb_res = client.get("/api/cockpit/safety/causal-boundary")
    assert cb_res.status_code == 200
    assert "self_test_evidence" in cb_res.json()
    evidence = cb_res.json()["self_test_evidence"]
    assert evidence["clean_context_accepted"] is True
    assert len(evidence["probes"]) > 0
    assert all(p["rejected"] for p in evidence["probes"])


def test_cockpit_evaluation_and_governance(client):
    eval_res = client.get("/api/cockpit/evaluation?seeds=2&ticks=5")
    assert eval_res.status_code == 200
    data = eval_res.json()
    assert "baseline" in data
    assert "candidate" in data
    assert "metrics" in data
    assert "accuracy" in data["metrics"]

    gov_res = client.get("/api/cockpit/governance")
    assert gov_res.status_code == 200
    gov_data = gov_res.json()
    assert "capabilities" in gov_data
    assert "levels" in gov_data



def test_cockpit_universal_search(client):
    res = client.get("/api/cockpit/search?q=agent")
    assert res.status_code == 200
    results = res.json()
    assert isinstance(results, list)
    assert len(results) > 0
    assert any(r["category"] == "agent" for r in results)


def test_cockpit_export_report(client):
    res = client.get("/api/cockpit/export-report")
    assert res.status_code == 200
    report = res.json()
    assert "report_id" in report
    assert "scenario" in report
    assert "system_truth" in report
    assert "reproducibility" in report
