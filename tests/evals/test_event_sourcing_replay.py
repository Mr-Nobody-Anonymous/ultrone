"""Tests for Event-Sourcing immutable journal and deterministic replay engine."""

import tempfile
from pathlib import Path
import pytest
from packages.runtime.event_sourcing.event_store import EventStore, IntegrityViolationError
from packages.runtime.event_sourcing.events import EventType
from packages.runtime.event_sourcing.replay import DeterministicReplayEngine


def test_event_store_append_and_hash_chain():
    store = EventStore()
    trace_id = "mission-alpha-trace"

    # Append sequential lifecycle events
    e1 = store.append(trace_id, EventType.ObservationReceived, logical_tick=1, payload={"radar_tracks": 2})
    e2 = store.append(trace_id, EventType.WorldEstimateUpdated, logical_tick=1, payload={"estimate_conf": 0.88})
    e3 = store.append(trace_id, EventType.ActionProposed, logical_tick=2, payload={"action": "reposition", "wp": [10, 20]})
    e4 = store.append(trace_id, EventType.ActionApproved, logical_tick=2, payload={"gate": "ROEGrader", "approved": True})

    assert e1.previous_event_hash is None
    assert e2.previous_event_hash == e1.compute_event_hash()
    assert e3.previous_event_hash == e2.compute_event_hash()
    assert e4.previous_event_hash == e3.compute_event_hash()

    # Verify integrity
    ok, err = store.verify_chain_integrity(trace_id)
    assert ok is True
    assert err is None


def test_event_store_tamper_detection():
    store = EventStore()
    trace_id = "tamper-test-trace"

    store.append(trace_id, EventType.ActionProposed, logical_tick=1, payload={"target": "SAM_01"})
    store.append(trace_id, EventType.ActionApproved, logical_tick=1, payload={"approved": True})

    # Tamper with an event in memory
    events = store.get_trace(trace_id)
    # Manually tamper with previous_event_hash of the second event
    object.__setattr__(events[1], "previous_event_hash", "corrupted_bogus_hash_12345")

    ok, err = store.verify_chain_integrity(trace_id)
    assert ok is False
    assert "Integrity check failed" in err


def test_event_store_jsonl_persistence_and_reload():
    store = EventStore()
    trace_id = "persistence-trace"

    store.append(trace_id, EventType.ObservationReceived, logical_tick=1, payload={"alt": 500})
    store.append(trace_id, EventType.OutcomeObserved, logical_tick=2, payload={"hit": True})

    with tempfile.TemporaryDirectory() as tmp_dir:
        jsonl_path = Path(tmp_dir) / "trace.jsonl"
        count = store.save_to_jsonl(trace_id, jsonl_path)
        assert count == 2

        new_store = EventStore()
        loaded_id = new_store.load_from_jsonl(jsonl_path)
        assert loaded_id == trace_id

        ok, err = new_store.verify_chain_integrity(loaded_id)
        assert ok is True
        assert len(new_store.get_trace(loaded_id)) == 2


def test_deterministic_replay_and_reproducibility():
    store = EventStore()
    t1 = "run-001"
    t2 = "run-002"

    # Populate two identical runs
    for tid in (t1, t2):
        store.append(tid, EventType.ObservationReceived, 1, {"radar": [10, 20]})
        store.append(tid, EventType.PlanGenerated, 1, {"plan_id": "p-1"})
        store.append(tid, EventType.ActionApproved, 2, {"approved": True})

    engine = DeterministicReplayEngine(store)

    # Replay trace
    state = engine.replay_trace(t1)
    assert state["current_tick"] == 2
    assert len(state["observations"]) == 1
    assert len(state["plans"]) == 1
    assert len(state["verdicts"]) == 1

    # Verify zero-divergence between runs
    identical, divergences = engine.verify_reproducibility(t1, t2)
    assert identical is True
    assert len(divergences) == 0
