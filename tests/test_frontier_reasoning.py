# Copyright (c) Ultrone Contributors. All rights reserved.
"""Tests for the Frontier Reasoning / Adaptation / Agents / Decision stacks.

Covers the reasoning strategies (ToT, GoT, Self-Consistency, Multi-Agent
Debate, Constitutional Critique, Beam Search), the reflection & self-correction
engines, the critic model, the agent orchestration stack (Planner, Executor,
Verifier, ToolRouter), and the Bayesian decision / uncertainty / calibration
layer.
"""

from __future__ import annotations

import pytest

from frontier.reasoning.tree_of_thoughts import TreeOfThoughts
from frontier.reasoning.graph_of_thoughts import GraphOfThoughts
from frontier.reasoning.self_consistency import SelfConsistency
from frontier.reasoning.multi_agent_debate import MultiAgentDebate
from frontier.reasoning.constitutional_critique import ConstitutionalCritique
from frontier.reasoning.beam_search_reasoner import BeamSearchReasoner
from frontier.reasoning.base import Verification
from frontier.adaptation.critic_model import CriticModel, Critique
from frontier.adaptation.reflection_engine import ReflectionEngine
from frontier.adaptation.self_correction_engine import SelfCorrectionEngine
from frontier.agents.planner import Planner, Plan, PlanStep
from frontier.agents.executor import Executor
from frontier.agents.verifier import Verifier as AgentVerifier
from frontier.agents.tool_router import ToolRouter
from frontier.decision.uncertainty import UncertaintyEstimator
from frontier.decision.calibration import ConfidenceCalibrator
from frontier.decision.bayesian_decision import BayesianDecisionLayer, Belief


# ---------------------------------------------------------------------------
# Deterministic test solvers and verifiers
# ---------------------------------------------------------------------------
class EchoSolver:
    """A solver that returns a fixed answer."""

    def __init__(self, answer: str = "42") -> None:
        self.answer = answer

    def __call__(self, prompt: str, **kwargs):
        return self.answer


class MajoritySolver:
    """Returns alternating answers so 3 samples yield 42, 43, 42."""

    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, prompt: str, **kwargs):
        self.calls += 1
        return "42" if self.calls % 2 else "43"


class VerifierStub:
    """A verifier that passes only the answer '42'."""

    def __call__(self, solution, prompt):
        ok = solution.strip() == "42"
        return Verification(passes=ok, score=1.0 if ok else 0.0)


# ---------------------------------------------------------------------------
# Reasoning strategies
# ---------------------------------------------------------------------------
class TestReasoningBase:
    def test_requires_solver(self):
        with pytest.raises(ValueError):
            TreeOfThoughts().solve("x")

    def test_trace_recorded(self):
        strategy = SelfConsistency(solver=EchoSolver("42"), n_samples=3)
        result = strategy.solve_with_trace("What is the answer?")
        assert result.trace is not None
        assert result.trace.strategy == "self_consistency"
        assert len(strategy.get_history()) == 1


class TestTreeOfThoughts:
    def test_solves_with_generator(self):
        def gen(prompt, state, cfg):
            if not state:
                return ["step a", "step b"]
            return ["final"]

        def evaluator(thought, prompt, state, cfg):
            return 1.0 if thought.startswith("final") else 0.5

        tot = TreeOfThoughts(
            solver=EchoSolver("answer"),
            thought_generator=gen,
            thought_evaluator=evaluator,
            max_depth=2,
        )
        result = tot.solve("problem")
        assert result.solution
        assert result.confidence > 0.0


class TestGraphOfThoughts:
    def test_solves(self):
        def gen(prompt, n, cfg):
            return [f"idea {i}" for i in range(n)]

        def agg(prompt, thoughts):
            return " | ".join(thoughts)

        got = GraphOfThoughts(
            solver=EchoSolver("combined"),
            thought_generator=gen,
            aggregator=agg,
            num_initial_thoughts=2,
            aggregation_rounds=1,
            max_refinements=0,
        )
        result = got.solve("problem")
        assert result.solution
        assert "num_nodes" in result.metadata


class TestSelfConsistency:
    def test_majority_voting(self):
        sc = SelfConsistency(solver=MajoritySolver(), n_samples=3)
        result = sc.solve("sum?")
        # 3 samples: 42, 43, 42 -> majority 42
        assert result.solution == "42"
        assert result.confidence == pytest.approx(2 / 3)

    def test_verifier_weighted(self):
        sc = SelfConsistency(
            solver=EchoSolver("42"),
            verifier=VerifierStub(),
            n_samples=2,
            weighting="verifier",
        )
        result = sc.solve("value?")
        assert result.solution == "42"


class TestMultiAgentDebate:
    def test_majority_consensus(self):
        class AgentA:
            def __call__(self, prompt, **kwargs):
                return "apple"

        agents = [AgentA(), AgentA(), AgentA()]
        debate = MultiAgentDebate(solvers=agents, num_rounds=0)
        result = debate.solve("fruit?")
        assert result.solution == "apple"
        assert result.confidence == pytest.approx(1.0)


class TestConstitutionalCritique:
    def test_solves(self):
        cc = ConstitutionalCritique(solver=EchoSolver("improved"), max_rounds=1)
        result = cc.solve("problem")
        assert result.solution


class TestBeamSearchReasoner:
    def test_solves(self):
        def gen(prompt, text, cfg):
            return ["step " + str(i) for i in range(cfg.expansions_per_beam)]

        bs = BeamSearchReasoner(
            solver=EchoSolver("answer"),
            step_generator=gen,
            beam_width=2,
            max_depth=2,
            expansions_per_beam=2,
        )
        result = bs.solve("problem")
        assert result.solution
        assert result.confidence > 0.0


# ---------------------------------------------------------------------------
# Adaptation: Critic, Reflection, Self-Correction
# ---------------------------------------------------------------------------
class TestCriticModel:
    def test_heuristic_critique(self):
        critic = CriticModel()
        critique = critic.evaluate("prompt", "A short answer.")
        assert critique.score >= 0.0
        assert critique.passed in (True, False)

    def test_explicit_critic_fn(self):
        def fn(prompt, solution):
            return Critique(score=0.9, issues=[], suggestions=[], passed=None)

        critic = CriticModel(critic_fn=fn)
        critique = critic.evaluate("p", "s")
        assert critique.score == 0.9
        assert critique.passed is True


class TestReflectionEngine:
    def test_reflect_loop(self):
        engine = ReflectionEngine(
            solver=EchoSolver("solution"),
            verifier=VerifierStub(),
            max_reflections=1,
        )
        result = engine.reflect("prompt")
        assert "solution" in result
        assert "traces" in result


class TestSelfCorrectionEngine:
    def test_corrects_until_passing(self):
        engine = SelfCorrectionEngine(
            solver=EchoSolver("42"),
            verifier=VerifierStub(),
            max_attempts=3,
        )
        result = engine.solve("prompt")
        assert result["passed"] is True


# ---------------------------------------------------------------------------
# Agent orchestration
# ---------------------------------------------------------------------------
class TestPlanner:
    def test_planner_with_generator(self):
        def gen(goal, context):
            return [PlanStep(index=i, description=f"step {i}") for i in range(3)]

        planner = Planner(plan_generator=gen)
        plan = planner.plan("goal")
        assert isinstance(plan, Plan)
        assert len(plan.steps) == 3

    def test_planner_heuristic(self):
        planner = Planner()
        plan = planner.plan("goal")
        assert len(plan.steps) >= 1

    def test_replan(self):
        planner = Planner()
        plan = planner.replan("goal", {}, 1, "failed")
        assert plan.goal == "goal"


class TestExecutor:
    def test_execute_with_tool(self):
        executor = Executor(tools={"add": lambda **kw: kw["a"] + kw["b"]})
        plan = Plan(
            goal="g",
            steps=[PlanStep(index=0, description="add", tool="add", args={"a": 1, "b": 2})],
        )
        result = executor.execute(plan)
        assert result.success is True
        assert result.final_output == 3

    def test_execute_stops_on_failure(self):
        def bad(**kw):
            raise RuntimeError("boom")

        executor = Executor(tools={"bad": bad})
        plan = Plan(
            goal="g",
            steps=[
                PlanStep(index=0, description="ok", tool="bad"),
                PlanStep(index=1, description="never", tool="bad"),
            ],
        )
        result = executor.execute(plan)
        assert result.success is False
        assert len(result.step_results) == 1


class TestVerifier:
    def test_oracle_verification(self):
        verifier = AgentVerifier(oracle=lambda task: "42")
        result = verifier.verify("task", "the answer is 42")
        assert result.passes is True

    def test_check_fn(self):
        def check(output, task, context):
            return output == "ok", 1.0, "fine"

        verifier = AgentVerifier(check_fn=check)
        result = verifier.verify("task", "ok")
        assert result.passes is True
        assert result.score == 1.0


class TestToolRouter:
    def test_exact_match_route(self):
        router = ToolRouter()
        router.register("search", lambda **kw: "result", "web search")
        result = router.route("please search for X")
        assert result.success is True
        assert result.tool == "search"

    def test_no_tool(self):
        router = ToolRouter()
        result = router.route("do something")
        assert result.success is False


# ---------------------------------------------------------------------------
# Decision layer
# ---------------------------------------------------------------------------
class TestUncertaintyEstimator:
    def test_ensemble_agreement(self):
        est = UncertaintyEstimator(method="ensemble")
        result = est.estimate(["a", "a", "a"])
        assert result.estimate == pytest.approx(0.0)
        assert result.confidence() == pytest.approx(1.0)

    def test_ensemble_disagreement(self):
        est = UncertaintyEstimator(method="ensemble")
        result = est.estimate(["a", "b"])
        assert result.estimate > 0.0


class TestConfidenceCalibrator:
    def test_ece_computation(self):
        cal = ConfidenceCalibrator(num_bins=10)
        confs = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95]
        correct = [c >= 0.5 for c in confs]
        ece = cal.compute_ece(confs, correct)
        assert ece >= 0.0

    def test_temperature_scale(self):
        cal = ConfidenceCalibrator()
        scale = cal.temperature_scale([0.1, 0.9], [False, True])
        assert scale >= 0.5


class TestBayesianDecisionLayer:
    def test_bayes_update(self):
        belief = Belief(probabilities={"a": 0.5, "b": 0.5})
        updated = belief.posterior({"a": 1.0, "b": 0.0})
        assert updated.mode() == "a"
        assert updated.confidence() == pytest.approx(1.0)

    def test_abstain_when_uncertain(self):
        layer = BayesianDecisionLayer(prior={"a": 0.5, "b": 0.5}, abstain_threshold=0.8)
        decision = layer.decide(["a", "b"])
        assert decision.abstained is True

    def test_decision_with_high_confidence(self):
        layer = BayesianDecisionLayer(prior={"a": 0.9, "b": 0.1}, abstain_threshold=0.5)
        decision = layer.decide(["a", "b"])
        assert decision.action == "a"
        assert decision.abstained is False
