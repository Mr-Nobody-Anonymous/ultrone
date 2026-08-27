# Copyright (c) Ultrone Contributors. All rights reserved.
"""Tests for the self-training substrate (learning + promotion gates)."""

from __future__ import annotations

import pytest

from adaptive.promotion import BrainStore
from orchestration.router import Orchestrator, RoutingPolicy
from orchestration.task_classifier import TaskProfile
from orchestration.traces import OrchestrationTrace

from self_improvement.self_training import (
    CheckpointManager,
    ContinualMixture,
    CurriculumManager,
    DatasetBuilder,
    ExperienceSelector,
    LearnedWeights,
    LevelSpec,
    RegressionSuite,
    Scheduler,
    StatisticalTrainer,
    TestModelAdapter,
    default_curriculum,
    make_executor,
)
from self_improvement.self_training.promotion import Promoter
from self_improvement.self_training.regression import (
    FamilyReport,
    RegressionReport,
)


def _weights(**values):
    defaults = {"reasoning": 0.5, "coding": 0.5,
                "retrieval": 0.5, "tool_use": 0.5}
    defaults.update(values)
    return LearnedWeights(values=defaults)


def profile(difficulty: float = 0.5) -> TaskProfile:
    return TaskProfile(domain="coding", difficulty=float(difficulty),
                       reasoning_depth=0.5, task_id="t",
                       source_summary="s")


def _trace(task_id: str, quality: float, accepted: bool,
           difficulty: float = 0.4) -> OrchestrationTrace:
    profile = TaskProfile(domain="coding", difficulty=difficulty,
                          reasoning_depth=0.5, task_id=task_id,
                          source_summary="s")
    return OrchestrationTrace(
        task_id=task_id, task_profile=profile,
        selected_model="coder", selected_memory="none",
        result={"quality": quality, "task_id": task_id} if accepted
        else {"quality": quality},
        score=1.0, accepted=accepted)


class TestTaskGeneration:
    def test_curriculum_has_five_levels(self):
        assert len(default_curriculum()) == 5

    def test_siblings_distinct_and_deterministic(self):
        level = default_curriculum()[0]
        a = level.sample(0, prefix="cur-1")
        b = level.sample(1, prefix="cur-1")
        assert a.task_id != b.task_id
        assert (a.difficulty, a.reasoning_depth) != \
            (b.difficulty, b.reasoning_depth)
        again = level.sample(0, prefix="cur-1")
        assert a.to_dict() == again.to_dict()  # deterministic


class TestCurriculumAdvance:
    def test_advances_on_saturation(self):
        levels = [
            LevelSpec(name="l1", difficulty=(0.0, 0.2),
                      saturation_mean=0.2, required_streaks=1,
                      num_tasks=4),
            LevelSpec(name="l2", difficulty=(0.2, 0.4),
                      saturation_mean=0.2, required_streaks=1,
                      num_tasks=4),
        ]
        cm = CurriculumManager(levels)
        step = cm.record(0.6)
        assert step.advanced            # l1 -> l2
        assert cm.current_level.name == "l2"
        step2 = cm.record(0.6)
        assert step2.completed_all

    def test_streak_resets_on_dip(self):
        cm = CurriculumManager([LevelSpec(name="l1",
                                          saturation_mean=0.5,
                                          required_streaks=2,
                                          num_tasks=4)])
        cm.record(0.9)
        cm.record(0.1)                  # dip resets streak
        assert cm.progress()[0]["streak"] == 0


class TestSelector:
    def test_three_way_bucket(self):
        selector = ExperienceSelector(good_floor=0.6, bad_ceiling=0.3)
        traces = [
            _trace("g1", 0.85, True),
            _trace("b1", 0.15, False),
            _trace("u1", 0.45, True),      # accepted but below good bar
        ]
        selected = selector.select(traces)
        assert selected.counts() == {"good": 1, "bad": 1, "uncertain": 1}

    def test_weakness_profile_from_failures(self):
        bad = [_trace("x", 0.1, False), _trace("y", 0.2, False)]
        weakness = ExperienceSelector(0.6, 0.3).select(bad).weakness_profile()
        assert set(weakness) >= {"difficulty", "domains"}


class TestDatasetBuilder:
    def test_dedup_and_ceiling_labeling(self, tmp_path):
        builder = DatasetBuilder(str(tmp_path))
        traces = [
            _trace("a", 0.4, True, difficulty=0.4),
            _trace("a", 0.4, True, difficulty=0.4),   # exact dup
            _trace("b", 0.9, True, difficulty=0.8),   # distinct payload
        ]
        artifact = builder.build_from_traces(
            traces, tag="t", desired_ceiling=0.8)
        rows = artifact.load()
        assert artifact.num_examples == 2
        assert artifact.duplicates_removed == 1
        by_difficulty = {row["input"]["difficulty"]: row for row in rows}
        assert by_difficulty[0.4]["outcome_score"] == 0.8   # raised to ceiling
        assert by_difficulty[0.8]["outcome_score"] == 0.9   # already above

    def test_no_signal_yields_none(self, tmp_path):
        assert DatasetBuilder(str(tmp_path)).build_from_traces(
            [], tag="x") is None


class TestMixture:
    def test_invalid_ratios_rejected(self):
        with pytest.raises(ValueError):
            ContinualMixture(ratios=(0.5, 0.5, 0.5))

    def test_historical_only_blend(self, tmp_path):
        good = [_trace("t0", 0.9, True, difficulty=0.4),
                _trace("t1", 0.9, True, difficulty=0.8)]
        hist = DatasetBuilder(str(tmp_path)).build_from_traces(
            good, tag="h", desired_ceiling=0.8)
        mix = ContinualMixture(ratios=(1.0, 0.0, 0.0))
        out = mix.merge(hist, None, [], workdir=str(tmp_path),
                        tag="m")
        assert out.num_examples == 2
        assert out.source_counts["historical"] == 2


class TestStatisticalTrainer:
    def test_moves_toward_evidence_and_is_deterministic(self):
        trainer = StatisticalTrainer(prior_strength=0.5)
        current = _weights(reasoning=0.3)
        examples = [
            {"example_id": "e1",
             "input": {"domain": "coding", "difficulty": 0.8,
                       "reasoning_depth": 0.9,
                       "context_requirement": 0.3,
                       "tool_requirement": 0.0,
                       "latency_sensitivity": 0.1,
                       "privacy_required": False,
                       "summary": "s"},
             "context": {}, "desired_behavior": {},
             "outcome_score": 0.95},
        ]
        fit_a = trainer.fit(examples, current)
        fit_b = trainer.fit(examples, current)
        assert fit_a.weights.model_hash == fit_b.weights.model_hash
        assert fit_a.examples_used == 1
        assert fit_a.weights.values["reasoning"] > 0.3

    def test_prior_shrinks_little_evidence(self):
        current = _weights(coding=0.2)
        strong = _weights(coding=1.0)
        moved = StatisticalTrainer(prior_strength=10.0).fit(
            [{"input": {"domain": "coding", "difficulty": 0.5,
                        "reasoning_depth": 0.5,
                        "context_requirement": 0.3,
                        "tool_requirement": 0.0,
                        "latency_sensitivity": 0.2,
                        "privacy_required": False, "summary": "s"},
              "context": {}, "desired_score": {},
              "outcome_score": 1.0}],
            current=_weights(reasoning=0.0)).weights
        # a lone example cannot budge a strong prior much
        assert moved.values["reasoning"] < 0.3


class TestExecutorSeam:
    def test_custom_executor_is_used_by_orchestrator(self):
        calls = {"n": 0}

        def fake(decision, profile, bundle, attempt_index):
            calls["n"] += 1
            return 0.6

        orchestrator = Orchestrator(RoutingPolicy(), executor=fake)
        from orchestration.task_classifier import synthetic_profile
        orchestrator.run(synthetic_profile(1))
        assert calls["n"] > 0

    def test_learned_executor_produces_scalar_quality(self):
        judge = make_executor(_weights())
        class _D: pass
        decision, bundle = _D(), _D()
        bundle.truncated = False
        decision.parameters = {}
        quality = judge(decision, TaskProfile(domain="coding",
                                              task_id="t"),
                        bundle, 0)
        assert 0.0 <= quality <= 1.0


class TestAdapters:
    def test_test_adapter_deterministic(self):
        a = TestModelAdapter()
        one = a.generate("hello world", context="c")
        assert one.text == a.generate("hello world", context="c").text

    def test_local_adapter_requires_load(self):
        from self_improvement.self_training import LocalModelAdapter
        adapter = LocalModelAdapter("some/model")
        with pytest.raises(RuntimeError):
            adapter.generate("prompt")


class TestCheckpoints:
    def test_lineage_and_gated_promotion(self, tmp_path):
        mgr = CheckpointManager(str(tmp_path / "models"))
        base = _weights()
        mid = mgr.register_candidate(
            base, dataset_hash="d1", configuration_hash="c1",
            training_seed="1", parent_model="", duration_seconds=1.0)
        assert mid.status == "candidate"
        with pytest.raises(ValueError):
            mgr.promote(mid.model_id)         # not evaluated yet
        mgr.evaluate(mid.model_id, {"normal": 0.1})
        mgr.promote(mid.model_id)
        assert mgr.production().model_id == mid.model_id
        assert mgr.production_weights().model_hash == base.model_hash
        # registry persists across a reload
        mgr2 = CheckpointManager(str(tmp_path / "models"))
        assert mgr2.production().model_id == mid.model_id


class TestRegressionSuite:
    def test_better_candidate_passes(self):
        suite = RegressionSuite(families={"normal": [profile(0.2)]})
        base = _weights(reasoning=0.3)
        cand = _weights(reasoning=0.9)
        report = suite.run(cand, base)
        assert report.passed
        assert report.families["normal"].mean_delta > 0

    def test_worse_candidate_flags_regression(self):
        suite = RegressionSuite(families={"normal": [profile(0.3)]})
        base = _weights(reasoning=0.9)
        cand = _weights(reasoning=0.1)
        report = suite.run(cand, base)
        assert not report.passed
        assert "normal" in report.family_regressions


class TestPromoter:
    def test_better_candidate_promotes_to_production(self, tmp_path):
        brain = BrainStore(storage_dir=str(tmp_path / "brain"))
        promoter = Promoter(holdout=[profile(0.2)], margin=0.01,
                            brain=brain)
        base = _weights(reasoning=0.5)
        cand = _weights(reasoning=0.95)
        decision = promoter.run(cand, base, persist=True)
        assert decision.promoted
        assert brain.get_config("production").get("kind") is not None
        from adaptive.optimizer import config_hash
        stored_hash = config_hash(brain.get_config("production"))
        assert stored_hash == decision.candidate_hash
        assert promoter.history[-1].decision == "promote"

    def test_identical_candidate_rejected(self, tmp_path):
        promoter = Promoter(holdout=[profile(0.2)], margin=0.01)
        weights = _weights(reasoning=0.5)
        decision = promoter.run(weights, weights)
        assert not decision.promoted

    def test_regression_failure_records_honest_reject(self, tmp_path):
        brain = BrainStore(storage_dir=str(tmp_path / "brain"))
        promoter = Promoter(holdout=[profile(0.2)], margin=0.01,
                            brain=brain)
        cand = _weights(reasoning=0.95)     # would promote on score alone
        base = _weights(reasoning=0.5)
        fake_report = RegressionReport(
            families={"adversarial": FamilyReport(
                family="adversarial", baseline_mean=0.8,
                candidate_mean=0.1, mean_delta=-0.7,
                regressions=[("t", -0.7)])},
            tolerance=0.12,
            candidate_weights=cand, baseline_weights=base)
        decision = promoter.run(cand, base, fake_report, persist=True)
        assert not decision.promoted
        assert "regression" in decision.reason
        # The GATE must record the honest verdict, never 'promote'.
        assert promoter.history[-1].decision == "reject"
        # Nothing written to a production channel.
        assert brain.get_config("production") == {}


class TestClosedLoop:
    def test_controller_learns_promotes_and_plateaus(self, tmp_path):
        from self_improvement.self_training.controller import (
            SelfTrainingController,
        )
        controller = SelfTrainingController(
            workdir=str(tmp_path / "work"),
            batch=12,
            starter=_weights(reasoning=0.62, coding=0.66,
                             retrieval=0.56, tool_use=0.68),
            good_floor=0.5, margin=0.01, desired_ceiling=0.85)
        starter_hash = _weights(reasoning=0.62, coding=0.66,
                                retrieval=0.56, tool_use=0.68).model_hash
        reports = [controller.run_cycle(i) for i in range(1, 5)]

        # Cycle one produced a real dataset + candidate + learned shift.
        first = reports[0]
        assert first.decision.should_train
        assert first.dataset is not None
        assert first.dataset.num_examples > 1
        assert first.candidate is not None
        assert first.candidate.model_hash != starter_hash

        # At least one genuine promotion reached production.
        assert controller.checkpoints.production() is not None
        assert any(r.promotion and r.promotion.promoted for r in reports)

        # Curriculum made progress across the cycles.
        assert any(r.curriculum is not None for r in reports)
        current = controller.curriculum
        assert current.completed or current.progress()[0]["streak"] > 0

    def test_insufficient_signal_does_not_train(self, tmp_path):
        from self_improvement.self_training.controller import (
            SelfTrainingController,
        )
        # A weak starter whose tasks never clear the demand bar yields a
        # controlled no-op cycle -- no dataset, no candidate, no fake learn.
        controller = SelfTrainingController(
            workdir=str(tmp_path / "work"),
            batch=6,
            starter=_weights(reasoning=0.25, coding=0.25,
                             retrieval=0.25, tool_use=0.25),
            good_floor=0.9, margin=0.01, desired_ceiling=0.85)
        report = controller.run_cycle(1)
        assert report.candidate is None
        assert report.dataset is None or \
            not report.decision.should_train
