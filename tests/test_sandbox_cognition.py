# Copyright (c) Ultrone Contributors. All rights reserved.
"""Unit tests for sandbox cognition modules (memory/planning/tools/
world-model/critique/multi-agent)."""

import pytest

from sandbox.critique import OVERCONFIDENT, STUCK_LOOP, WRONG_TOP, SelfCritic
from sandbox.memory import EpisodicMemory, GoalStack, GOAL_STALLED
from sandbox.multiagent import SandboxAgent, Task, cooperation_gain
from sandbox.planning import backchain, build_example_domains
from sandbox.prediction import PredictionRecord
from sandbox.tooluse import Tool, build_demo_toolbox
from sandbox.world_model import TransitionModel


class TestMemory:
    def test_retrieval_ranks_by_relevance(self):
        mem = EpisodicMemory()
        mem.remember("hazard", "storm surge damaged pier seven",
                     tags=("hazard",), salience=1.5, tick=1)
        mem.remember("admin", "inventory count completed",
                     tags=("admin",), tick=1)
        hits = mem.recall(keywords=("surge", "pier"), tick=2)
        assert hits[0].key == "hazard"

    def test_salience_and_recency_matter(self):
        mem = EpisodicMemory()
        mem.remember("old", "pump valve inspection", tick=1)
        mem.remember("fresh", "pump valve inspection", tick=50)
        top = mem.recall(keywords=("valve",), tick=51)[0]
        assert top.key == "fresh"

    def test_goal_stall_detection(self):
        goals = GoalStack()
        goals.push("g1", "x", deadline_tick=5)
        assert goals.sweep(tick=4) == []
        stalled = goals.sweep(tick=6)
        assert [g.goal_id for g in stalled] == ["g1"]
        assert goals.goals["g1"].status == GOAL_STALLED

    def test_suspend_resume_roundtrip(self):
        from sandbox.memory import GOAL_SUSPENDED

        goals = GoalStack()
        goals.push("g1", "x")
        goals.suspend("g1")
        assert goals.active == []
        goals.resume("g1")
        assert len(goals.active) == 1


class TestPlanning:
    def test_backchain_solves_kitchen(self):
        reg = build_example_domains()["kitchen"]
        plan = backchain(reg, "kitchen", "tea")
        assert plan is not None and plan[-1].provides == "tea"

    def test_transfer_to_unrelated_domain(self):
        domains = build_example_domains()
        tea = backchain(domains["kitchen"], "kitchen", "tea")
        delivery = backchain(domains["logistics"], "logistics", "box_delivered")
        assert tea and delivery                      # same decomposer, both work
        assert {s.domain for s in tea} == {"kitchen"}
        assert {s.domain for s in delivery} == {"logistics"}

    def test_impossible_goal_returns_none(self):
        reg = build_example_domains()["kitchen"]
        assert backchain(reg, "kitchen", "cold_fusion") is None

    def test_depth_limit_bounds_search(self):
        reg = build_example_domains()["logistics"]
        assert backchain(reg, "logistics", "box_delivered", max_depth=1) is None


class TestToolUse:
    def test_chain_discovered_and_executed(self):
        box = build_demo_toolbox()
        path = box.chain("text", "count")
        # BFS yields the shortest chain: tokenize -> count_tokens.
        assert [t.name for t in path] == ["tokenize", "count_tokens"]
        assert box.execute("the quick brown fox and the dog", path) == 7

    def test_new_tool_shortens_chain(self):
        box = build_demo_toolbox()
        before = len(box.chain("text", "count"))
        box.register(Tool(
            "count_words", "text", "count", lambda s: len(s.split()),
        ))
        after_path = box.chain("text", "count")
        assert len(after_path) < before
        assert box.execute("a b c d", after_path) == 4

    def test_no_chain_for_impossible_type(self):
        assert build_demo_toolbox().chain("text", "quantum_state") is None


class TestWorldModel:
    def test_learns_deterministic_transitions(self):
        model = TransitionModel()
        for _ in range(10):
            model.update("A", "go", "B")
        assert model.predict("A", "go") == {"B": 1.0}

    def test_counterfactual_separates_actions(self):
        model = TransitionModel()
        model.update("A", "go", "B")
        model.update("A", "stay", "A")
        cf = model.counterfactual("A", "go", "stay")
        assert cf["divergence"] == pytest.approx(1.0)

    def test_surprise_on_novel_pair_is_maximal(self):
        assert TransitionModel().surprise("Q", "go", "Z") == 1.0


class TestSelfCritique:
    @staticmethod
    def _rec(tick, top, conf, correct, truth="X"):
        return PredictionRecord(tick=tick, true_state=truth, observed="x",
                                top_hypothesis=top, confidence=conf,
                                correct=correct, brier=0.0)

    def test_detects_all_three_failure_shapes(self):
        records = [
            self._rec(1, "Y", 0.9, False),
            self._rec(2, "Y", 0.9, False),
            self._rec(3, "Y", 0.9, False),
        ]
        kinds = {c.kind for c in SelfCritic().review_predictions(records)}
        assert {WRONG_TOP, OVERCONFIDENT, STUCK_LOOP} <= kinds

    def test_correct_run_produces_no_critiques(self):
        records = [self._rec(t, "X", 0.9, True) for t in range(1, 6)]
        assert SelfCritic().review_predictions(records) == []

    def test_low_confidence_wrong_is_not_overconfident(self):
        critiques = SelfCritic().review_predictions([self._rec(1, "Y", 0.3, False)])
        assert {OVERCONFIDENT} & {c.kind for c in critiques} == set()


class TestMultiAgent:
    def _agents_tasks(self):
        agents = [
            SandboxAgent("a1", frozenset({"lift", "carry"})),
            SandboxAgent("a2", frozenset({"carry"})),
            SandboxAgent("a3", frozenset({"lift"})),
        ]
        tasks = [Task(f"t{i}", "carry" if i % 2 else "lift",
                      load=2 + (i % 3)) for i in range(8)]
        return agents, tasks

    def test_coordination_balances_load(self):
        agents, tasks = self._agents_tasks()
        gain = cooperation_gain(tasks, agents)
        assert (gain["cooperative"]["imbalance_std"]
                <= gain["isolated"]["imbalance_std"])

    def test_claims_prevent_duplicate_work(self):
        agents, tasks = self._agents_tasks()
        gain = cooperation_gain(tasks, agents)
        assert gain["cooperative"]["duplicate_assignments"] == 0
        assert gain["duplicates_eliminated"] >= 0

    def test_incapable_task_left_unassigned(self):
        agents = [SandboxAgent("a1", frozenset({"lift"}))]
        stats = cooperation_gain([Task("t1", "dive")], agents)
        assert stats["cooperative"]["unassigned"] == 1
