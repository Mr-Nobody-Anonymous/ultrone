# Copyright (c) Ultrone Contributors. All rights reserved.
"""Integration tests for the canonical end-to-end decision pipeline.

These tests prove that every layer of the ULTRONE vertical slice
communicates correctly:

    env observation -> sensors -> fusion -> world estimate -> COA planning
        -> independent safety gate -> execution -> outcome -> trace
"""

import pytest

from core import (
    ActionOrder,
    AssetSnapshot,
    DecisionPipeline,
    SafetyConfig,
    SafetyGate,
    WorldEstimate,
)


@pytest.fixture
def pipeline():
    return DecisionPipeline(seed=7, n_candidates=3)


class TestFullPipeline:
    """The whole chain runs as one coherent system."""

    def test_step_produces_complete_trace(self, pipeline):
        pipeline.reset_episode()
        result = pipeline.step()
        d = result.trace.to_dict()

        assert result.trace.decision_id.startswith("DEC-")
        # Every stage must be populated - no silent gaps.
        assert d["sensing"]["observation"]["red_force"] is not None
        assert "feeds_generated" in d["perception"]
        assert "primary_target_confidence" in d["world_state"]
        assert d["planning"]["n_candidates"] == 3
        assert "verdict" in d["safety"]
        assert "env_action" in d["execution"]
        assert "reward" in d["outcome"]

    def test_trace_records_all_candidate_coas(self, pipeline):
        pipeline.reset_episode()
        result = pipeline.step()
        ids = result.trace.planning["candidate_ids"]
        assert len(ids) == 3
        assert len(set(ids)) == 3  # unique COA IDs

    def test_episode_completes_with_traces_for_every_step(self, pipeline):
        summary = pipeline.run_episode(max_steps=30)
        assert summary["steps"] == len(summary["traces"])
        assert summary["steps"] > 0
        for t in summary["traces"]:
            assert t["decision_id"].startswith("DEC-")
            assert "outcome" in t

    def test_traces_accumulate_across_steps(self, pipeline):
        pipeline.reset_episode()
        first = pipeline.step()
        second = pipeline.step()
        assert second.trace.tick == first.trace.tick + 1
        assert second.trace.decision_id != first.trace.decision_id


class TestSafetyGateIndependence:
    """The gate enforces constraints independently of the planner."""

    @staticmethod
    def _estimate(confidence):
        return WorldEstimate(
            contacts=[{"contact_id": "c1", "confidence": confidence}],
            primary_target_position=(60.0, 60.0),
            primary_target_confidence=confidence,
            n_feeds_generated=3,
            n_feeds_received=3,
        )

    def test_blocks_strike_on_low_confidence(self):
        gate = SafetyGate(SafetyConfig(min_engagement_confidence=0.5))
        order = ActionOrder("strike", "missiles", (60, 60), "COA-X")
        asset = AssetSnapshot("missiles", (55, 55), fuel=1.0, ammo=4, range=50.0)

        verdict = gate.evaluate(order, self._estimate(0.2), asset)
        assert not verdict.approved
        rule_ids = {r.rule_id for r in verdict.rule_results if not r.passed}
        assert "R2_ENGAGEMENT_CONFIDENCE" in rule_ids

    def test_approves_high_confidence_in_range_strike(self):
        gate = SafetyGate(SafetyConfig(min_engagement_confidence=0.5))
        order = ActionOrder("strike", "missiles", (60, 60), "COA-X")
        asset = AssetSnapshot("missiles", (58, 58), fuel=1.0, ammo=4, range=50.0)

        verdict = gate.evaluate(order, self._estimate(0.9), asset)
        assert verdict.approved

    def test_blocks_strike_without_ammo(self):
        gate = SafetyGate()
        order = ActionOrder("strike", "missiles", (60, 60), "COA-X")
        asset = AssetSnapshot("missiles", (58, 58), fuel=1.0, ammo=0, range=50.0)

        verdict = gate.evaluate(order, self._estimate(0.9), asset)
        assert not verdict.approved
        rule_ids = {r.rule_id for r in verdict.rule_results if not r.passed}
        assert "R3_AMMO_AVAILABLE" in rule_ids

    def test_blocks_out_of_range_engagement(self):
        gate = SafetyGate()
        order = ActionOrder("strike", "missiles", (90, 90), "COA-X")
        asset = AssetSnapshot("missiles", (10, 10), fuel=1.0, ammo=4, range=30.0)

        verdict = gate.evaluate(order, self._estimate(0.9), asset)
        assert not verdict.approved
        rule_ids = {r.rule_id for r in verdict.rule_results if not r.passed}
        assert "R4_ENGAGEMENT_RANGE" in rule_ids
    def test_blacklisted_action_always_rejected(self):
        gate = SafetyGate(SafetyConfig(blacklisted_actions=["strike"]))
        order = ActionOrder("strike", "missiles", (60, 60), "COA-X")
        asset = AssetSnapshot("missiles", (60, 60), fuel=1.0, ammo=4, range=99.0)

        verdict = gate.evaluate(order, self._estimate(1.0), asset)
        assert not verdict.approved
        rule_ids = {r.rule_id for r in verdict.rule_results if not r.passed}
        assert "R6_ACTION_BLACKLIST" in rule_ids

    def test_pipeline_never_executes_rejected_order(self):
        """With every action blacklisted, nothing may execute (no-op)."""
        strict = DecisionPipeline(
            seed=7,
            safety_gate=SafetyGate(SafetyConfig(
                blacklisted_actions=["strike", "jam", "move", "resupply"],
            )),
        )
        strict.reset_episode()
        for _ in range(5):
            result = strict.step()
            assert result.trace.safety["fallback_noop"]
            assert not result.verdict.approved
            assert result.trace.execution["env_action"] is None


class TestPartialObservability:
    """The planner sees noisy belief, never ground truth."""

    def test_sensor_dropout_and_noise_present(self, pipeline):
        pipeline.reset_episode()
        dropped_seen = False
        for _ in range(20):
            result = pipeline.step()
            if result.trace.perception["dropped"] > 0:
                dropped_seen = True
                break
        assert dropped_seen, "expected at least one sensor dropout in 20 steps"

    def test_no_contacts_yields_noop_not_crash(self):
        from core.pipeline import SensorSuite
        from core.contracts import Observation
        import random as _random

        suite = SensorSuite(rng=_random.Random(1))
        empty_obs = Observation(tick=1, red_force={}, blue_assets={}, supply_nodes={})
        records = suite.generate(empty_obs)
        assert records == []

    def test_estimate_uncertainty_is_derived_from_confidence(self):
        est = WorldEstimate(
            contacts=[], primary_target_position=None,
            primary_target_confidence=0.3,
            n_feeds_generated=3, n_feeds_received=0,
        )
        assert est.uncertainty == pytest.approx(0.7)


class TestReproducibility:
    """Same seed -> comparable run structure (replay foundation)."""

    def test_same_seed_same_action_sequence_shape(self):
        p1 = DecisionPipeline(seed=123)
        p2 = DecisionPipeline(seed=123)

        # Run each pipeline's full sequence independently; global RNGs are
        # seeded at episode start, so identical configs must reproduce.
        p1.reset_episode()
        seq1 = [p1.step().trace.planning["n_candidates"] for _ in range(10)]
        sensor1 = []
        for _ in range(5):
            r = p1.step()
            sensor1.append(r.trace.perception["feeds_generated"])

        p2.reset_episode()
        seq2 = [p2.step().trace.planning["n_candidates"] for _ in range(10)]
        sensor2 = []
        for _ in range(5):
            r = p2.step()
            sensor2.append(r.trace.perception["feeds_generated"])

        assert seq1 == seq2
        assert sensor1 == sensor2

