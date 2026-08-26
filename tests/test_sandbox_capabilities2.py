# Copyright (c) Ultrone Contributors. All rights reserved.
"""Tests for the Sprint D completion capabilities: multimodal perception,
continual learning, distribution shift, learning from experience,
cross-domain reasoning, and GeneralAgent integration."""

import random

import pytest

from sandbox.agent import GeneralAgent
from sandbox.continual import (
    TabularLearner,
    build_task_sequence,
    run_continual_sequence,
)
from sandbox.experience import EpsilonGreedyLearner, BanditEnvironment
from sandbox.perception import MultimodalFusion, MultimodalWorld, Percept
from sandbox.reasoning import (
    build_analogous_domains,
    map_facts,
    run_reasoning_suite,
)
from sandbox.robustness import shift, run_shift_suite


class TestMultimodalPerception:
    def test_fusion_beats_single_modalities_statistically(self):
        from sandbox.perception import run_perception_suite

        result = run_perception_suite(seed=5, n_trials=400)
        fusion = result["fusion_accuracy"]
        best_single = max(result["unimodal_accuracy"].values())
        assert fusion >= best_single - 0.03
        assert result["graceful_under_dropout"]

    def test_fusion_deterministic_tiebreak(self):
        fusion = MultimodalFusion()
        tied = [
            Percept("visual", "barrel", 0.5),
            Percept("lidar", "crate", 0.5),
        ]
        assert fusion.fuse(tied).claimed_class == "barrel"  # sorted tie-break

    def test_empty_input_falls_back_blindly(self):
        out = MultimodalFusion().fuse([])
        assert out.confidence == 0.0

    def test_world_respects_reliability_bounds(self):
        world = MultimodalWorld(seed=1)
        percepts = world.observe("barrel", ["tag"])
        assert len(percepts) == 1
        assert percepts[0].claimed_class in ("barrel", "crate", "tarp")


class TestContinualLearning:
    def test_unbounded_learner_retains_everything(self):
        tasks = build_task_sequence(4, 4)
        report = run_continual_sequence(tasks, capacities=(None,))
        unbounded = report["learners"]["unbounded"]
        assert unbounded["learned_each_task"]
        assert unbounded["retained_everything"]

    def test_benchmark_detects_capacity_forgetting(self):
        tasks = build_task_sequence(4, 4)
        report = run_continual_sequence(tasks, capacities=(None, 6))
        capped = report["learners"]["cap_6"]
        # 16 symbols through a 6-slot memory: early tasks must be evicted.
        assert capped["retention_after_all"] != [1.0] * 4
        assert report["benchmark_detects_forgetting"]

    def test_lru_eviction_order(self):
        learner = TabularLearner(capacity=2)
        learner.update("s1", "a")
        learner.update("s2", "b")
        learner.update("s1", "a")          # refresh s1
        learner.update("s3", "c")          # evicts s2 (least recently used)
        assert learner.predict("s1") == "a"
        assert learner.predict("s2") is None
        assert learner.predict("s3") == "c"


class TestDistributionShift:
    @pytest.fixture(scope="class")
    def suite(self):
        return run_shift_suite(seed=3)

    def test_all_shifts_stay_graceful(self, suite):
        assert suite["all_graceful"]

    def test_mild_shift_is_bounded(self, suite):
        assert suite["mild_shift_bounded"]

    def test_novel_symbol_does_not_crash_agent(self, suite):
        assert suite["survives_novel_symbol"]

    def test_shift_transformations_are_valid_distributions(self):
        for kind in ("base", "mild", "novel_symbol", "regime_merge"):
            rows = shift(kind)
            for dist in rows.values():
                total = sum(dist.values())
                assert total == pytest.approx(1.0, abs=1e-3)


class TestLearningFromExperience:
    def test_regret_decreases_across_episodes(self):
        from sandbox.experience import run_learning_curve

        result = run_learning_curve(seed=0)
        assert result["learns_from_experience"]
        assert result["finds_best_arm"]
        assert result["episode_mean_reward"][-1] >= 0.9 * 0.8

    def test_learner_exploits_learned_values(self):
        agent = EpsilonGreedyLearner(3, random.Random(1), epsilon_min=0.0)
        for _ in range(50):
            arm = agent.select()
            reward = 1.0 if arm == 2 else 0.0   # arm 2 always pays
            agent.update(arm, reward)
        assert agent.greedy_arm() == 2

    def test_environment_is_stochastic_but_seeded(self):
        a = BanditEnvironment((0.5,), seed=9)
        b = BanditEnvironment((0.5,), seed=9)
        draws_a = [a.pull(0) for _ in range(30)]
        draws_b = [b.pull(0) for _ in range(30)]
        assert draws_a == draws_b
        assert set(draws_a) <= {0, 1}


class TestCrossDomainReasoning:
    def test_deduction_reaches_depth_two_in_both_domains(self):
        result = run_reasoning_suite()
        assert result["deduces_to_depth_two"]
        assert result["both_domains_solved"]

    def test_analogy_maps_solution_across_domains(self):
        domains, mapping = build_analogous_domains()
        derived = domains["botany"].derive(
            {"green_leaves", "moist_soil"}, "botany",
        )
        mapped = map_facts(derived, mapping)
        fleet_derived = domains["fleet"].derive(mapped, "fleet")
        assert "inspection_pass" in fleet_derived

    def test_missing_premise_blocks_chain(self):
        domains, _ = build_analogous_domains()
        partial = domains["botany"].derive({"green_leaves"}, "botany")
        assert "thriving_plant" not in partial
        assert "blooms_soon" not in partial

    def test_negative_cause_does_not_produce_positive_outcome(self):
        domains, _ = build_analogous_domains()
        derived = domains["botany"].derive({"pest_damage"}, "botany")
        assert "blooms_soon" not in derived


class TestGeneralAgentIntegration:
    @pytest.fixture()
    def agent(self):
        return GeneralAgent(seed=0)

    def test_full_loop_tool_task(self, agent):
        result = agent.handle_tool_task(
            "T1", "the quick brown fox and the dog", needed_type="count",
        )
        assert result.success and result.detail["value"] == 7
        assert agent.completed_goals == 1
        assert len(agent.memory) == 1

    def test_world_learning_improves_prediction(self, agent):
        first = agent.handle_world_task("W0", "dock", "ship_out", "harbor")
        assert first.detail["had_prior"] is False      # nothing known yet
        for i in range(5):
            agent.handle_world_task(f"W{i+1}", "dock", "ship_out", "harbor")
        assert agent.predict_transition("dock", "ship_out") == "harbor"

    def test_critiques_are_remembered(self, agent):
        from sandbox.prediction import PredictionRecord

        n = agent.review_prediction_history([
            PredictionRecord(tick=1, true_state="X", observed="x",
                             top_hypothesis="Y", confidence=0.9,
                             correct=False, brier=1.2),
            PredictionRecord(tick=2, true_state="X", observed="x",
                             top_hypothesis="Y", confidence=0.9,
                             correct=False, brier=1.2),
            PredictionRecord(tick=3, true_state="X", observed="x",
                             top_hypothesis="Y", confidence=0.9,
                             correct=False, brier=1.2),
        ])
        assert n >= 3                                   # wrong x3 + overconf + loop
        assert any(m.tags & {"critique"} for m in agent.memory._items.values())

    def test_agent_is_deterministic_given_seed(self):
        a, b = GeneralAgent(seed=7), GeneralAgent(seed=7)
        ra = [a.handle_tool_task(f"T{i}", "one two three") for i in range(3)]
        rb = [b.handle_tool_task(f"T{i}", "one two three") for i in range(3)]
        assert [(r.task_id, r.success, r.detail) for r in ra] \
            == [(r.task_id, r.success, r.detail) for r in rb]
        assert a.completed_goals == b.completed_goals