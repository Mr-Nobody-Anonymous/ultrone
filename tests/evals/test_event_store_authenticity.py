"""Tests for EventStore Signed Checkpoints and Deterministic Re-Execution vs Event Replay."""

import pytest
from packages.runtime.event_sourcing.event_store import EventStore, IntegrityViolationError, SignedCheckpoint
from packages.runtime.event_sourcing.events import EventType
from packages.runtime.event_sourcing.replay import (
    DeterministicReExecutionEngine,
    EventReplayEngine,
    ExecutionEnvelope,
)


def test_signed_checkpoint_creation_and_verification():
    store = EventStore()
    trace_id = "authentic-trace-01"
    key = "super-secret-audit-signing-key-12345"

    store.append(trace_id, EventType.ObservationReceived, 1, {"altitude": 1000})
    store.append(trace_id, EventType.PlanGenerated, 1, {"plan": "recon"})
    store.append(trace_id, EventType.ActionApproved, 2, {"approved": True})

    # Create signed checkpoint
    checkpoint = store.create_signed_checkpoint(trace_id, signing_key=key, signer_id="auditor-01")
    assert checkpoint.event_count == 3
    assert checkpoint.signature is not None

    # Verify signature passes with valid key
    valid, err = store.verify_checkpoint(checkpoint, signing_key=key)
    assert valid is True
    assert err is None

    # Verification fails with incorrect key
    valid_bad_key, err_bad_key = store.verify_checkpoint(checkpoint, signing_key="wrong-key")
    assert valid_bad_key is False
    assert "signature invalid" in err_bad_key


def test_signed_checkpoint_fails_if_event_stream_rewritten():
    store = EventStore()
    trace_id = "tampered-audit-trace"
    key = "audit-key-xyz"

    store.append(trace_id, EventType.ActionProposed, 1, {"target": "radar_site"})
    checkpoint = store.create_signed_checkpoint(trace_id, signing_key=key)

    # Attacker modifies the event in place and recomputes hashes
    events = store.get_trace(trace_id)
    # Tamper payload
    object.__setattr__(events[0], "payload", {"target": "civilian_hospital"})
    # Recomputed event hash will now diverge from checkpoint.cumulative_chain_hash
    valid, err = store.verify_checkpoint(checkpoint, signing_key=key)
    assert valid is False
    assert "Event chain compromised" in err or "Cumulative chain hash mismatch" in err


def test_deterministic_re_execution_vs_event_replay():
    store = EventStore()
    envelope = ExecutionEnvelope(
        git_commit_sha="4c75fdf",
        python_version="3.10.11",
        random_seed=42,
        config_hash="cfg-hash-abc",
        model_weights_hash="weights-hash-xyz",
    )

    def mock_pipeline(seed: int):
        # Deterministic calculation using seed
        val = (seed * 1103515245 + 12345) & 0x7FFFFFFF
        return {"output_metric": val, "seed_used": seed}

    reexec_engine = DeterministicReExecutionEngine(store)

    # 1. First execution
    ok1, res1, digest1 = reexec_engine.execute_and_verify(
        envelope, trace_id="run-genesis-1", pipeline_fn=mock_pipeline
    )
    assert ok1 is True
    assert res1["seed_used"] == 42

    # 2. Independent re-execution from genesis asserts zero computational drift
    ok2, res2, digest2 = reexec_engine.execute_and_verify(
        envelope, trace_id="run-genesis-2", pipeline_fn=mock_pipeline, expected_digest=digest1
    )
    assert ok2 is True
    assert digest1 == digest2

    # 3. Event replay reconstructs past emitted event states without re-running physics
    replay_engine = EventReplayEngine(store)
    state = replay_engine.replay_trace("run-genesis-1")
    assert state["current_tick"] == 1


def test_asymmetric_ed25519_checkpoint_verification():
    """Verify asymmetric audit model: Writer signs with private key, Auditor verifies with public key."""
    store = EventStore()
    trace_id = "asym-audit-trace-01"

    store.append(trace_id, EventType.ObservationReceived, 1, {"altitude": 5000})
    store.append(trace_id, EventType.ActionApproved, 1, {"authorized": True})

    priv_key, pub_key = store.generate_ed25519_keypair()
    other_priv, other_pub = store.generate_ed25519_keypair()

    # Writer signs checkpoint with private key
    checkpoint = store.create_asymmetric_checkpoint(
        trace_id=trace_id,
        private_key=priv_key,
        signer_id="flight-recorder-service",
        key_id="key-writer-01",
    )
    assert checkpoint.signature_scheme == "ed25519"
    assert checkpoint.public_key_hex is not None

    # Auditor verifies using public key
    valid, err = store.verify_asymmetric_checkpoint(checkpoint, public_key=pub_key)
    assert valid is True
    assert err is None

    # Verification fails with an untrusted / different public key
    valid_bad, err_bad = store.verify_asymmetric_checkpoint(checkpoint, public_key=other_pub)
    assert valid_bad is False
    assert "verification failed" in err_bad
