"""Tests for Machine-Checkable Causal Boundary and Confidence Provenance."""

import pytest
from packages.cognition.brain.orchestrator import Orchestrator
from packages.runtime.event_sourcing.causal_boundary import (
    CausalBoundaryValidator,
    CausalBoundaryViolationError,
    ConfidenceProvenance,
)


def test_causal_boundary_rejects_post_action_outcomes_in_pre_action_inputs():
    # Valid pre-action context
    clean_inputs = {
        "tick": 42,
        "observations": [{"contact_id": "c-01", "azimuth": 45.0}],
        "belief_state": {"threat_level": "HIGH"},
        "policy_version": "v1.2",
    }
    # Passes cleanly
    CausalBoundaryValidator.inspect_decision_inputs(clean_inputs)

    # Contaminated context containing post-action outcome
    contaminated_inputs = {
        "tick": 42,
        "observations": [{"contact_id": "c-01"}],
        "actual_outcome": {"hit": True, "damage": 100},  # Forbidden post-action leakage!
    }
    with pytest.raises(CausalBoundaryViolationError) as excinfo:
        CausalBoundaryValidator.inspect_decision_inputs(contaminated_inputs)
    assert "actual_outcome" in str(excinfo.value)


def test_orchestrator_gates_contaminated_inputs():
    orch = Orchestrator(oracle_mode=False)
    obs = {"blue_assets": {"drone": [{"position": [0, 0, 0], "fuel": 1.0, "ammo": 5}]}}

    # Contaminated action containing ground truth hits
    contaminated_action = {
        "action": "strike",
        "asset_type": "drone",
        "target": [10, 20, 0],
        "hits": 1,  # Post-action outcome field!
    }

    with pytest.raises(CausalBoundaryViolationError):
        orch._gate_action(contaminated_action, obs)


def test_confidence_provenance_requires_verifiable_source():
    # 1. Unbacked confidence without source -> rejected (defaults to 0.0)
    unbacked_action = {"action": "strike", "confidence": 0.95}
    conf, err = CausalBoundaryValidator.extract_calibrated_confidence(unbacked_action, require_source=True)
    assert conf == 0.0
    assert "Unbacked confidence" in err

    # 2. Verified confidence with source and observation IDs -> approved
    verified_action = {
        "action": "strike",
        "confidence_provenance": {
            "confidence": 0.88,
            "confidence_source": "radar_fusion_kalman",
            "observation_ids": ["obs-radar-001", "obs-eoir-002"],
            "model_version": "tracker-v2",
            "calibration_version": "platt-v1",
        },
    }
    conf_valid, err_valid = CausalBoundaryValidator.extract_calibrated_confidence(verified_action, require_source=True)
    assert conf_valid == 0.88
    assert err_valid is None


def test_taint_tracking_rejects_arbitrary_named_future_data():
    """Verify that taint tracking detects post-action leakage regardless of variable naming."""
    from packages.runtime.event_sourcing.causal_boundary import TaintTracker, TaintedValue

    # A field named arbitrarily: 'custom_secret.value'
    secret_future_data = {"custom_metric": 42}
    TaintTracker.taint(secret_future_data)

    context = {
        "tick": 10,
        "observations": [{"id": 1}],
        "some_subfield": secret_future_data,
    }

    with pytest.raises(CausalBoundaryViolationError) as excinfo:
        CausalBoundaryValidator.inspect_decision_inputs(context)
    assert "tainted" in str(excinfo.value).lower()

    # Also with TaintedValue wrapper
    wrapped_context = {
        "tick": 10,
        "arbitrary_var": TaintedValue(value=999, source="oracle_future"),
    }
    with pytest.raises(CausalBoundaryViolationError) as excinfo2:
        CausalBoundaryValidator.inspect_decision_inputs(wrapped_context)
    assert "tainted" in str(excinfo2.value).lower()


def test_cryptographic_confidence_provenance_chain():
    """Verify cryptographic provenance chain: observation_hash + model_artifact_hash."""
    prov_no_crypto = ConfidenceProvenance(
        confidence=0.92,
        confidence_source="neural_tracker",
        observation_ids=["obs-1"],
    )
    # Valid without crypto requirement
    assert prov_no_crypto.is_valid(require_crypto=False) is True
    # Rejected when crypto chain is required
    assert prov_no_crypto.is_valid(require_crypto=True) is False

    # Full cryptographic provenance chain
    prov_crypto = ConfidenceProvenance(
        confidence=0.92,
        confidence_source="neural_tracker",
        observation_ids=["obs-1"],
        observation_hash="sha256_obs_e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        model_artifact_hash="sha256_model_a1b2c3d4e5f6...",
        calibration_artifact_hash="sha256_calib_123...",
        sensor_id="radar-array-01",
        sensor_calibration_version="cal-2026.08",
    )
    assert prov_crypto.is_valid(require_crypto=True) is True
