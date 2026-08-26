# Copyright (c) Ultrone Contributors. All rights reserved.
"""Adaptive engine tests: registry, evaluator gates, optimizer,
promotion flow, skills, and experiments."""

import pytest

from adaptive import (
    AdaptiveOptimizer,
    BrainStore,
    Evaluator,
    ExperimentRunner,
    ParameterRegistry,
    PromotionGate,
    PromotionRecord,
    SkillLibrary,
    default_patrol_registry,
    ground_patrol_score,
)
from adaptive.optimizer import config_hash


def _registry() -> ParameterRegistry:
    registry = default_patrol_registry()
    return registry


class TestParameterRegistry:
    def test_declare_and_defaults(self):
        registry = _registry()
        assert registry.get("patrol.speed") == 1.2
        assert registry.names() == ["patrol.speed",
                                    "patrol.waypoint_budget",
                                    "patrol.wear_sensitivity"]

    def test_bounds_clamp_and_int_rounding(self):
        registry = ParameterRegistry()
        registry.declare("gain", "float", 0.5, bounds=(0.0, 1.0))
        assert registry.set("gain", 5.0) == 1.0
        registry.declare("iters", "int", 10, bounds=(4, 20))
        assert registry.set("iters", 7.6) == 8

    def test_type_mismatch_rejected(self):
        registry = ParameterRegistry()
        registry.declare("enabled", "bool", False)
        with pytest.raises(TypeError):
            registry.set("enabled", "yes")

    def test_undeclared_set_rejected_atomically(self):
        registry = _registry()
        with pytest.raises(KeyError):
            registry.apply_overrides({"patrol.speed": 1.5,
                                      "rogue.param": 3.0})
        # Atomicity: the valid entry was NOT applied.
        assert registry.get("patrol.speed") == 1.2

    def test_unknown_dependency_rejected(self):
        registry = ParameterRegistry()
        with pytest.raises(ValueError):
            registry.declare("child", "float", 1.0,
                             dependencies=["missing.parent"])

    def test_config_hash_tracks_values(self):
        registry = _registry()
        before = registry.config_hash()
        registry.set("patrol.speed", 1.9)
        after = registry.config_hash()
        assert before != after
        registry.reset("patrol.speed")
        assert registry.config_hash() == before

    def test_snapshot_roundtrip(self):
        registry = _registry()
        registry.set("patrol.speed", 1.77)
        clone = ParameterRegistry.from_snapshot(registry.export()
                                                ["parameters"])
        assert clone.snapshot() == registry.snapshot()
        assert clone.export()["config_hash"] == \
            registry.export()["config_hash"]


class TestEvaluatorGates:
    def test_better_candidate_promotes(self):
        baseline = {"patrol.speed": 1.0}
        candidate = {"patrol.speed": 1.48}   # near the interior optimum
        result = Evaluator().evaluate(candidate, baseline)
        assert result.decision == "promote"
        assert result.candidate_score > result.baseline_score

    def test_identical_candidate_rejected(self):
        config = {"patrol.speed": 1.2}
        result = Evaluator(margin=0.01).evaluate(config, dict(config))
        assert result.decision == "reject"

    def test_non_reproducible_task_rejected(self):
        counter = {"n": 0}

        def noisy(_config):
            counter["n"] += 1
            return float(counter["n"])

        evaluator = Evaluator(task=noisy)
        result = evaluator.evaluate({"x": 1}, {"x": 1})
        assert result.decision == "non_reproducible"

    def test_repeats_below_two_rejected(self):
        with pytest.raises(ValueError):
            Evaluator(repeats=1)

    def test_builtin_task_is_deterministic(self):
        config = {"patrol.speed": 1.4}
        assert ground_patrol_score(config) == ground_patrol_score(config)


class TestOptimizer:
    def _optimizer(self, **kwargs):
        defaults = dict(registry=_registry(),
                        evaluator=Evaluator(),
                        tunable=["patrol.speed",
                                 "patrol.wear_sensitivity"],
                        population_size=10, seed=7)
        defaults.update(kwargs)
        return AdaptiveOptimizer(**defaults)

    def test_run_is_deterministic_per_seed(self):
        first = self._optimizer().run(generations=6)
        second = self._optimizer().run(generations=6)
        assert first.best.config == second.best.config
        assert first.best.score == second.best.score
        assert first.history_best == second.history_best

    def test_respects_parameter_bounds(self):
        result = self._optimizer().run(generations=4)
        speed = result.best.config["patrol.speed"]
        assert 0.5 <= speed <= 2.4

    def test_never_loses_the_baseline(self):
        result = self._optimizer().run(generations=5)
        assert result.best.score >= result.baseline_score - 1e-9

    def test_result_is_serializable(self):
        payload = self._optimizer().run(generations=3).to_dict()
        assert payload["best"]["origin"] in ("seed", "mutate", "crossover")


class TestPromotionFlow:
    def _promotable_candidate(self):
        registry = _registry()
        evaluator = Evaluator()
        optimizer = AdaptiveOptimizer(
            registry, evaluator,
            tunable=["patrol.speed", "patrol.wear_sensitivity"],
            population_size=8, seed=11)
        result = optimizer.run(generations=4)
        return evaluator, registry, result

    def test_full_gate_flow_promotes_verified_winner(self, tmp_path):
        _, registry, result = self._promotable_candidate()
        gate = PromotionGate()
        store = BrainStore(storage_dir=str(tmp_path))

        baseline_config = store.get_config("baseline")
        candidate = result.best.config
        store.set_config("candidate", candidate)
        evaluation = Evaluator().evaluate(candidate, baseline_config)
        record = gate.review(evaluation, candidate,
                             config_hash(candidate))

        if record.decision == "promote":
            store.promote(candidate, record, gate)
            assert store.summary()["production"]["config_hash"] is not None
        else:
            # A rejected candidate must never reach production.
            with pytest.raises(PermissionError):
                store.promote(candidate, record, gate)
        assert len(gate.history) == 1

    def test_production_write_requires_matching_record(self):
        from adaptive.optimizer import config_hash
        from adaptive.evaluator import EvaluationResult

        gate = PromotionGate()
        store = BrainStore()
        config = {"patrol.speed": 2.0}
        forged = PromotionRecord(
            record_id=99, decision="promote",
            config_hash=config_hash(config),
            candidate_config=config, candidate_score=99.0,
            baseline_score=1.0, reason="forged")
        with pytest.raises(PermissionError):
            store.promote(config, forged, gate)

    def test_direct_production_writes_blocked(self):
        store = BrainStore()
        with pytest.raises(ValueError):
            store.set_config("production", {"patrol.speed": 2.0})

    def test_persistence_roundtrip(self, tmp_path):
        store = BrainStore(storage_dir=str(tmp_path))
        candidate = {"patrol.speed": 1.5}
        store.set_config("experimental", candidate)
        reloaded = BrainStore(storage_dir=str(tmp_path))
        reloaded.load()
        assert reloaded.get_config("experimental") == candidate


class TestSkillLibrary:
    def _library(self) -> SkillLibrary:
        library = SkillLibrary()
        library.register_skill("nav.basic", "Basic navigation",
                               "navigation", benchmark_score=0.7,
                               inputs=["position", "target"])
        library.register_skill("nav.advanced", "Advanced navigation",
                               "navigation", benchmark_score=0.9,
                               confidence=0.6,
                               prerequisites=["nav.basic"],
                               inputs=["position", "target"])
        return library

    def test_select_best_by_utility(self):
        best = self._library().select("navigation")
        assert best is not None and best.skill_id == "nav.advanced"

    def test_prerequisites_enforced_at_registration(self):
        library = SkillLibrary()
        with pytest.raises(ValueError):
            library.register_skill("orphan", "Orphan", "planning",
                                   benchmark_score=0.5,
                                   prerequisites=["ghost.skill"])

    def test_outcomes_update_confidence_monotonically(self):
        library = self._library()
        start = library.get("nav.basic").confidence
        after_success = library.record_outcome("nav.basic", True)
        assert after_success > start
        before_fail = library.get("nav.basic").confidence
        after_fail = library.record_outcome("nav.basic", False)
        assert after_fail < before_fail

    def test_unknown_skill_outcome_rejected(self):
        with pytest.raises(KeyError):
            SkillLibrary().record_outcome("nope", True)

    def test_export_shape(self):
        exported = self._library().export()
        assert set(exported) == {"nav.basic", "nav.advanced"}
        assert exported["nav.advanced"]["prerequisites"] == ["nav.basic"]


class TestExperimentGrid:
    def test_grid_ranks_and_restores_registry(self):
        registry = default_patrol_registry()
        runner = ExperimentRunner(registry, ground_patrol_score)
        experiment = runner.grid("speed-sweep", "patrol.speed",
                                 [0.6, 0.9, 1.2, 1.5, 1.8, 2.1])
        ranked = experiment.ranked()
        scores = [t.score for t in ranked]
        assert scores == sorted(scores, reverse=True)
        # Interior optimum near speed ~1.5: faster must NOT be best.
        assert ranked[0].overrides["patrol.speed"] < 2.1
        # Registry restored to its pre-sweep value.
        assert registry.get("patrol.speed") == 1.2

    def test_grid_input_validation(self):
        registry = default_patrol_registry()
        runner = ExperimentRunner(registry, ground_patrol_score)
        with pytest.raises(ValueError):
            runner.grid("empty", "patrol.speed", [])
        with pytest.raises(KeyError):
            # Undeclared parameter: rejected before any trial runs.
            runner.grid("nonnumeric", "patrol.mode", ["a"])
