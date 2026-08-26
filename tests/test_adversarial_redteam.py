# Copyright (c) Ultrone Contributors. All rights reserved.
"""Tests for the deterministic red-team / outcome-prediction tooling."""

import pytest

from benchmarks.canonical.adversarial import (
    ADVERSARIAL_SUITE_VERSION,
    OutcomePrediction,
    perturb,
    predict_outcomes,
    red_team_suite,
    run_scenario,
    variant_seed,
)
from benchmarks.canonical.scenarios import SCENARIOS


BASE = SCENARIOS["normal_operation"]


class TestVariantGeneration:
    def test_variant_is_deterministic(self):
        v1a = perturb(BASE, 0)
        v1b = perturb(BASE, 0)
        assert v1a == v1b

    def test_variants_differ_from_base_and_from_each_other(self):
        v0, v1 = perturb(BASE, 0), perturb(BASE, 1)
        assert v0.seed != BASE.seed
        assert v0.seed != v1.seed
        assert v0.scenario_id.endswith("::rt0")
        assert v1.scenario_id.endswith("::rt1")

    def test_variant_inherits_governance_fields(self):
        gated = SCENARIOS["human_rejection"]
        v = perturb(gated, 1)
        assert v.human_policy == "reject"
        assert v.n_steps == gated.n_steps

    def test_suite_shape_and_uniqueness(self):
        specs = red_team_suite(variants_per=2)
        assert len(specs) == len(SCENARIOS) * 2
        assert len({s.scenario_id for s in specs}) == len(specs)

    def test_variant_seed_stable_across_calls(self):
        assert variant_seed(BASE, 3) == variant_seed(BASE, 3)


class TestRedTeamRuns:
    @pytest.fixture(scope="module")
    def records(self):
        specs = red_team_suite(
            base_ids=["normal_operation", "low_resource_condition"],
            variants_per=2,
        )
        return [run_scenario(s) for s in specs]

    def test_variants_run_cleanly_with_verified_chains(self, records):
        assert len(records) == 4
        for rec in records:
            assert rec["failures"] == [], rec["scenario_id"]
            assert rec["audit_chain_verified"] is True

    def test_variant_runs_are_reproducible(self, records):
        spec = perturb(SCENARIOS["normal_operation"], 0)
        rerun = run_scenario(spec)
        original = next(
            r for r in records if r["scenario_id"] == spec.scenario_id
        )
        assert rerun["fingerprint"] == original["fingerprint"]

    def test_predictions_aggregate_per_base_scenario(self, records):
        preds = {p.base_scenario: p for p in predict_outcomes(records)}
        assert set(preds) == {"normal_operation", "low_resource_condition"}
        for p in preds.values():
            assert isinstance(p, OutcomePrediction)
            assert p.n_variants == 2
            assert p.reward_min <= p.reward_mean <= p.reward_max

    def test_prediction_flags_failures(self):
        broken = [{
            "scenario_id": "x::rt0",
            "failures": ["ValueError: boom"],
            "metrics": {"total_reward": -1, "steps": 2, "noop_steps": 1},
            "constraint_violations": 0,
        }]
        preds = predict_outcomes(broken)
        assert preds[0].failure_rate == 1.0

    def test_suite_version_pinned(self):
        assert ADVERSARIAL_SUITE_VERSION == "canonical-adversarial-v1"


class TestCliExitSemantics:
    """Crashes are fatal; simulated fault-induced violations are findings."""

    @staticmethod
    def _record(violations=0, failures=None):
        return {
            "scenario_id": "normal_operation::rt0",
            "failures": list(failures or []),
            "metrics": {"total_reward": 10.0, "steps": 1, "noop_steps": 0},
            "steps": [{
                "tick": 0,
                "world_estimate": {
                    "primary_target_confidence": 0.9,
                    "primary_target_position": [10.0, 10.0],
                },
                "safety_verdict": {"reason": "approved"},
                "human_state": "EXECUTED",
                "executed_action": None,
                "reward": 10.0,
            }],
            "constraint_violations": violations,
            "audit_chain_verified": True,
        }

    def test_simulated_violation_reported_not_fatal(self, monkeypatch):
        import benchmarks.canonical.adversarial as adv

        monkeypatch.setattr(
            adv, "run_scenario", lambda spec: self._record(violations=1),
        )
        assert adv.main(["--variants-per", "1"]) == 0

    def test_strict_makes_simulated_violation_fatal(self, monkeypatch):
        import benchmarks.canonical.adversarial as adv

        monkeypatch.setattr(
            adv, "run_scenario", lambda spec: self._record(violations=1),
        )
        assert adv.main(["--variants-per", "1", "--strict"]) == 1

    def test_variant_crash_always_fatal(self, monkeypatch):
        import benchmarks.canonical.adversarial as adv

        rec = self._record(failures=["ValueError: boom"])
        monkeypatch.setattr(adv, "run_scenario", lambda spec: rec)
        assert adv.main(["--variants-per", "1"]) == 1
