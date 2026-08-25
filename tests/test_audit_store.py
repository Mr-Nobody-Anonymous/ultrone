# Copyright (c) Ultrone Contributors. All rights reserved.
"""Audit store: immutability, tamper-evidence, retrieval, replay, persistence."""

import json

import pytest

from ultrone_hitl.audit_store import (
    DuplicateDecisionError,
    InMemoryAuditStore,
    JSONLAuditStore,
    TamperDetectedError,
)


def proposal_payload(decision_id: str) -> dict:
    return {
        "trace": {
            "decision_id": decision_id,
            "episode_id": "EP-1",
            "tick": 0,
            "sensing": {"observation": {"red_force": {"type": "tank"}}},
            "perception": {"feeds_generated": 3, "dropped": 0},
            "world_state": {"primary_target_position": [60, 60], "primary_target_confidence": 0.8},
            "planning": {"n_candidates": 2, "candidate_ids": ["COA-a", "COA-b"]},
            "safety": {"verdict": {"approved": True}, "rejections": []},
            "execution": {"env_action": {"action": "strike", "asset_type": "missiles"}},
            "outcome": {"reward": 1.0, "done": False},
        },
        "summary": "strike",
    }


class TestInMemory:
    def test_append_and_replay_order(self):
        store = InMemoryAuditStore()
        store.append_event("submit", "D1", "PENDING", "bob", proposal_payload("D1"))
        store.append_event("approve", "D1", "APPROVED", "alice", {"note": "ok"})
        events = store.replay()
        assert [e["type"] for e in events] == ["submit", "approve"]
        assert events[0]["prev_hash"] == ""
        assert events[1]["prev_hash"] == events[0]["hash"]
        assert store.verify() is True

    def test_unique_events_chain(self):
        store = InMemoryAuditStore()
        store.append_event("submit", "D1", "PENDING", "a", proposal_payload("D1"))
        store.append_event("submit", "D2", "PENDING", "a", proposal_payload("D2"))
        events = store.replay()
        assert events[1]["prev_hash"] == events[0]["hash"]

    def test_duplicate_proposal_rejected(self):
        store = InMemoryAuditStore()
        store.append_event("submit", "D1", "PENDING", "a", proposal_payload("D1"))
        with pytest.raises(DuplicateDecisionError):
            store.append_event("submit", "D1", "PENDING", "a", proposal_payload("D1"))

    def test_timestamp_and_actor_preserved(self):
        store = InMemoryAuditStore()
        store.append_event("submit", "D1", "PENDING", "carol", proposal_payload("D1"))
        ev = store.replay()[0]
        assert ev["actor"] == "carol"
        assert ev["timestamp"].endswith("Z")
        assert ev["hash"]

    def test_retrieval_by_decision(self):
        store = InMemoryAuditStore()
        store.append_event("submit", "D1", "PENDING", "a", proposal_payload("D1"))
        store.append_event("approve", "D1", "APPROVED", "b", {"note": "ok"})
        store.append_event("submit", "D2", "PENDING", "a", proposal_payload("D2"))
        assert [e["type"] for e in store.decision_events("D1")] == ["submit", "approve"]
        assert store.current_state("D1") == "APPROVED"
        assert store.current_state("D2") == "PENDING"
        assert store.current_state("nope") is None

    def test_retrieved_records_are_deep_copies(self):
        store = InMemoryAuditStore()
        store.append_event("submit", "D1", "PENDING", "a", proposal_payload("D1"))
        returned = store.decision_events("D1")
        returned[0]["payload"]["trace"]["sensing"]["injected"] = True
        # The store must be unchanged by that mutation.
        fresh = store.decision_events("D1")[0]["payload"]["trace"]["sensing"]
        assert "injected" not in fresh

    def test_no_silent_mutation_in_memory(self):
        store = InMemoryAuditStore()
        store.append_event("submit", "D1", "PENDING", "a", proposal_payload("D1"))
        store.append_event("approve", "D1", "APPROVED", "b", {"note": "ok"})
        store._events[0]["state"] = "EXECUTED"  # simulate in-place back-door edit
        with pytest.raises(TamperDetectedError):
            store.events()


class TestJSONLTamper:
    def _make_chain(self, tmp_path):
        store = JSONLAuditStore(tmp_path / "audit.jsonl")
        store.append_event("submit", "D1", "PENDING", "alice", proposal_payload("D1"))
        store.append_event("approve", "D1", "APPROVED", "bob", {"note": "ok"})
        return store

    def test_persists_and_reloads(self, tmp_path):
        self._make_chain(tmp_path)
        store2 = JSONLAuditStore(tmp_path / "audit.jsonl")
        assert store2.current_state("D1") == "APPROVED"
        assert len(store2.replay()) == 2
        assert store2.verify() is True

    def test_replay_preserves_append_order(self, tmp_path):
        store = self._make_chain(tmp_path)
        assert [e["type"] for e in store.replay()] == ["submit", "approve"]

    def test_tamper_prior_record_detected(self, tmp_path):
        path = tmp_path / "audit.jsonl"
        self._make_chain(tmp_path)
        lines = path.read_text(encoding="utf-8").strip().splitlines()
        rec = json.loads(lines[0])
        rec["payload"]["summary"] = "SILENTLY TAMPERED"
        lines[0] = json.dumps(rec, ensure_ascii=False)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        store = JSONLAuditStore(path)
        with pytest.raises(TamperDetectedError):
            store.replay()
        with pytest.raises(TamperDetectedError):
            store.verify()

    def test_append_only_never_alters_prior_records(self, tmp_path):
        store = self._make_chain(tmp_path)
        before = store.replay()
        store.append_event("execute", "D1", "EXECUTED", "bob", {"note": ""})
        after = store.replay()
        assert len(after) == len(before) + 1
        assert after[0]["hash"] == before[0]["hash"]

    def test_unique_across_reload(self, tmp_path):
        store = self._make_chain(tmp_path)
        with pytest.raises(DuplicateDecisionError):
            store.append_event("submit", "D1", "PENDING", "alice", proposal_payload("D1"))