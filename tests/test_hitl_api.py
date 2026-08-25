# Copyright (c) Ultrone Contributors. All rights reserved.
"""HITL workflow + API: state transitions, authorization, evidence, retrieval."""

import pytest
from fastapi.testclient import TestClient

from ultrone_hitl.api import create_app
from ultrone_hitl.audit_store import InMemoryAuditStore
from ultrone_hitl.decision_workflow import (
    Authorizer,
    DecisionWorkflow,
    InvalidTransitionError,
    UnauthorizedActionError,
    UnknownDecisionError,
    trace_from_dict,
)


def trace_dict(decision_id: str = "DEC-T", confidence: float = 0.8) -> dict:
    return {
        "decision_id": decision_id,
        "episode_id": "EP-1",
        "tick": 0,
        "sensing": {"observation": {"red_force": {"type": "tank"}}},
        "perception": {"feeds_generated": 3, "dropped": 0},
        "world_state": {"primary_target_position": [60, 60], "primary_target_confidence": confidence},
        "planning": {
            "n_candidates": 3,
            "candidate_ids": ["COA-1", "COA-2", "COA-3"],
            "proposed_orders": [{"action": "strike", "asset_type": "missiles", "target": [60, 60]}],
        },
        "safety": {"verdict": {"approved": True, "reason": "approved"}, "rejections": [], "fallback_noop": False},
        "execution": {"env_action": {"action": "strike", "asset_type": "missiles", "target": [60, 60]}},
        "outcome": {"reward": 1.0, "done": False, "roe_violation": False, "red_health": 50},
    }


def _wf():
    return DecisionWorkflow(InMemoryAuditStore())


def _submit(wf, did="DEC-T"):
    return wf.submit(trace_from_dict(trace_dict(did)), "bob", scenario_id="S-1", summary="strike")


class TestWorkflowStateMachine:
    def test_submit_places_proposal_in_pending(self):
        wf = _wf()
        d = _submit(wf)
        assert d.state.value == "PENDING"
        assert d.summary == "strike"

    def test_approve_then_execute(self):
        wf = _wf()
        d = _submit(wf)
        assert wf.approve(d.decision_id, "alice").state.value == "APPROVED"
        assert wf.execute(d.decision_id, "bob").state.value == "EXECUTED"

    def test_rejected_cannot_be_resurrected(self):
        wf = _wf()
        d = _submit(wf)
        wf.reject(d.decision_id, "alice", "bad ROE")
        assert wf.get(d.decision_id).state.value == "REJECTED"
        # operator cannot resurrect
        with pytest.raises(InvalidTransitionError):
            wf.approve(d.decision_id, "alice")
        # admin cannot resurrect either
        with pytest.raises(InvalidTransitionError):
            wf.approve(d.decision_id, "carol")

    def test_override_requires_supervisor_role(self):
        wf = _wf()
        d = _submit(wf)
        with pytest.raises(UnauthorizedActionError):
            wf.override(d.decision_id, "bob", {"action": "move", "asset_type": "drones"})
        parent, child = wf.override(
            d.decision_id, "alice", {"action": "move", "asset_type": "drones", "target": [10, 10]}
        )
        assert parent.state.value == "OVERRIDDEN"
        assert child.state.value == "PENDING"
        assert child.decision_id != parent.decision_id
        # original proposal preserved on parent; child carries the new order
        assert parent.trace.execution == trace_dict()["execution"]
        assert child.trace.execution["order"]["action"] == "move"

    def test_unknown_actor_denied(self):
        wf = _wf()
        d = _submit(wf)
        with pytest.raises(UnauthorizedActionError):
            wf.approve(d.decision_id, "mallory")

    def test_unknown_decision(self):
        wf = _wf()
        with pytest.raises(UnknownDecisionError):
            wf.get("DEC-missing")

    def test_list_filters_by_state(self):
        wf = _wf()
        a = _submit(wf, "DEC-A")
        b = _submit(wf, "DEC-B")
        wf.approve(a.decision_id, "alice")
        assert {d.state.value for d in wf.list()} == {"APPROVED", "PENDING"}
        assert [d.decision_id for d in wf.list(state="APPROVED")] == [a.decision_id]

    def test_evidence_from_canonical_trace(self):
        wf = _wf()
        d = _submit(wf)
        ev = wf.evidence(d.decision_id)
        assert ev.decision_id == d.decision_id
        assert ev.n_candidates == 3
        assert ev.confidence == pytest.approx(0.8)
        assert ev.uncertainty == pytest.approx(0.2)
        assert ev.safety_verdict["approved"] is True


class TestAPI:
    @pytest.fixture
    def client(self):
        app = create_app(store=InMemoryAuditStore(), authorizer=Authorizer())
        return TestClient(app)

    def _submit(self, client, decision_id="DEC-api"):
        r = client.post(
            "/api/human/decisions",
            json={"trace": trace_dict(decision_id), "actor": "bob"},
        )
        assert r.status_code == 200, r.text
        return r.json()["decision"]

    def test_full_lifecycle(self, client):
        d = self._submit(client)
        did = d["decision_id"]
        assert d["state"] == "PENDING"
        r = client.post(f"/api/human/decisions/{did}/approve", json={"actor": "alice"})
        assert r.status_code == 200
        client.post(f"/api/human/decisions/{did}/execute", json={"actor": "bob"})
        got = client.get(f"/api/human/decisions/{did}").json()["decision"]
        assert got["state"] == "EXECUTED"
        assert len(got["history"]) == 3

    def test_cannot_approve_a_rejected_decision(self, client):
        d = self._submit(client)
        did = d["decision_id"]
        client.post(f"/api/human/decisions/{did}/reject", json={"actor": "alice", "reason": "bad ROE"})
        r = client.post(f"/api/human/decisions/{did}/approve", json={"actor": "carol"})
        assert r.status_code == 409
        assert client.get(f"/api/human/decisions/{did}").json()["decision"]["state"] == "REJECTED"

    def test_unknown_actor_gets_403(self, client):
        d = self._submit(client)
        r = client.post(f"/api/human/decisions/{d['decision_id']}/approve", json={"actor": "mallory"})
        assert r.status_code == 403

    def test_operator_cannot_override_403(self, client):
        d = self._submit(client)
        r = client.post(
            f"/api/human/decisions/{d['decision_id']}/override",
            json={"actor": "bob", "target": {"action": "move", "asset_type": "drones"}},
        )
        assert r.status_code == 403

    def test_supervisor_override_spawns_child(self, client):
        d = self._submit(client)
        r = client.post(
            f"/api/human/decisions/{d['decision_id']}/override",
            json={"actor": "alice", "target": {"action": "move", "asset_type": "drones", "target": [10, 10]}},
        )
        assert r.status_code == 200, r.text
        parent, child = r.json()["parent"], r.json()["child"]
        assert parent["state"] == "OVERRIDDEN"
        assert child["state"] == "PENDING"
        assert child["decision_id"] != parent["decision_id"]
        assert child["trace"]["execution"]["order"]["action"] == "move"

    def test_ask_reasoning_returns_evidence(self, client):
        d = self._submit(client)
        r = client.post(
            f"/api/human/decisions/{d['decision_id']}/ask_reasoning", json={"actor": "bob"}
        )
        assert r.status_code == 200
        ev = r.json()["evidence"]
        assert ev["n_candidates"] == 3 and ev["confidence"] == pytest.approx(0.8)

    def test_retrieve_unknown_is_404(self, client):
        assert client.get("/api/human/decisions/DEC-missing").status_code == 404

    def test_duplicate_submit_is_409(self, client):
        self._submit(client, decision_id="dup")
        r = client.post("/api/human/decisions", json={"trace": trace_dict("dup"), "actor": "bob"})
        assert r.status_code == 409

    def test_audit_replay(self, client):
        self._submit(client, "x1")
        self._submit(client, "x2")
        r = client.get("/api/human/audit")
        assert r.status_code == 200
        assert len(r.json()["events"]) >= 2

    def test_list_by_state(self, client):
        d = self._submit(client, "l1")
        client.post(f"/api/human/decisions/{d['decision_id']}/approve", json={"actor": "alice"})
        r = client.get("/api/human/decisions", params={"state": "APPROVED"})
        assert any(x["decision_id"] == d["decision_id"] for x in r.json()["decisions"])