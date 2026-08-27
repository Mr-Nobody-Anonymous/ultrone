# Copyright (c) Ultrone Contributors. All rights reserved.
"""Integration tests for the routing loop end-to-end."""

from __future__ import annotations

from brain.learning.experience_memory import ExperienceMemory
from orchestration.model_registry import default_model_registry
from orchestration.router import Orchestrator, RoutingPolicy, \
    default_routing_registry
from orchestration.task_classifier import (
    TaskProfile,
    classify,
    synthetic_profile,
)
from orchestration.traces import TraceLog

_POLICY = RoutingPolicy()


def _canonical_cases():
    return {
        "simple": TaskProfile(
            domain="analysis", difficulty=0.15, reasoning_depth=0.10,
            context_requirement=0.05, tool_requirement=0.0,
            latency_sensitivity=0.6, task_id="simple"),
        "deep": TaskProfile(
            domain="analysis", difficulty=0.85, reasoning_depth=0.90,
            context_requirement=0.10, task_id="deep"),
        "coding": TaskProfile(
            domain="coding", difficulty=0.60, reasoning_depth=0.40,
            context_requirement=0.20, tool_requirement=0.30,
            task_id="coding"),
        "long": TaskProfile(
            domain="analysis", difficulty=0.50, reasoning_depth=0.40,
            context_requirement=0.92, task_id="long"),
        "private": TaskProfile(
            domain="simulation", difficulty=0.45, reasoning_depth=0.35,
            context_requirement=0.15, tool_requirement=0.2,
            privacy_required=True, task_id="private"),
    }


class TestCanonicalRoutes:
    def test_simple_task_lands_on_cheap_tier(self):
        decision = _POLICY.decide(_canonical_cases()["simple"])[0]
        assert decision.model.name in {"nano", "local-7b"}
        assert "[economy]" in decision.rationale

    def test_deep_reasoning_gets_the_strongest_reasoner(self):
        decision = _POLICY.decide(_canonical_cases()["deep"])[0]
        assert decision.model.name == "reasoner"
        assert "[complexity]" in decision.rationale

    def test_coding_routes_to_the_coding_specialist(self):
        decision = _POLICY.decide(_canonical_cases()["coding"])[0]
        assert decision.model.name == "coder"

    def test_long_context_routes_to_the_window_specialist(self):
        profile = _canonical_cases()["long"]
        decision = _POLICY.decide(profile)[0]
        assert decision.model.name == "longctx"
        assert decision.memory.name == "tiered"

    def test_private_tasks_never_leave_the_local_tier(self):
        models = default_model_registry()
        decisions = _POLICY.decide(_canonical_cases()["private"])
        assert decisions, "private tasks must remain routable"
        for decision in decisions:
            spec = models.get(decision.model.name)
            assert spec.local_only, (
                f"non-local model {spec.name} eligible for private task")

    def test_decisions_are_ranked_by_utility(self):
        candidates = _POLICY.decide(_canonical_cases()["coding"])
        utilities = [c.utility for c in candidates]
        assert utilities == sorted(utilities, reverse=True)


class TestExecutionLoop:
    def test_rejections_exhaust_the_fallback_chain(self, tmp_path):
        """Deterministic retry mechanics via the confidence ceiling.

        ``validate.min_confidence`` caps at 0.90 while result confidence
        is 0.55 + 0.40*quality; a *simple* task cannot push quality past
        ~0.58 (confidence ~0.78) on ANY candidate tier. So every
        candidate fails validation identically -- exercising the full
        chain without depending on simulator margins.
        """
        registry = default_routing_registry()
        registry.set("validate.min_confidence", 0.90)
        orchestrator = Orchestrator(RoutingPolicy(registry))
        profile = _canonical_cases()["simple"]
        log = TraceLog(tmp_path / "traces.jsonl")

        outcome = orchestrator.run(profile, trace_log=log)
        expected_attempts = min(len(_POLICY.decide(profile)), 3)

        assert not outcome.accepted
        assert outcome.attempts_used == expected_attempts == 3
        assert len(outcome.failures) == outcome.attempts_used
        assert all("confidence" in f for f in outcome.failures)

        traces = log.load()
        assert len(traces) == 1
        trace = traces[0]
        assert not trace.accepted
        assert len(trace.failures) == trace.attempts_used == 3
        assert all(not a.validated for a in trace.failures)
        # Trace provenance: same snapshot the orchestrator stamped.
        assert trace.configuration_hash \
            == orchestrator.configuration_hash

    def test_budget_ceiling_stops_runaway_retries(self):
        """A tight budget guard halts retries mid-chain.

        With validation impossible (floor 0.90 on hard work) and a
        1-credit ceiling, no more than one attempt may execute: after
        the first paid rejection the second estimate would cross the
        cap, so the guard must append its own named failure and stop.
        """
        registry = default_routing_registry()
        registry.set("validate.min_confidence", 0.90)
        registry.set("routing.budget_cap_credits", 0.5)
        orchestrator = Orchestrator(RoutingPolicy(registry))

        outcome = orchestrator.run(TaskProfile(
            domain="coding", difficulty=0.95, reasoning_depth=0.9,
            context_requirement=0.45, tool_requirement=0.5,
            task_id="budget-brutal"))

        assert not outcome.accepted
        assert any("budget exhausted" in f for f in outcome.failures)
        assert 1 <= outcome.attempts_used < 3

    def test_experience_memory_records_routed_runs(self):
        experience = ExperienceMemory(max_history=50)
        orchestrator = Orchestrator(_POLICY)
        tasks = [synthetic_profile(1), synthetic_profile(2),
                 synthetic_profile(3)]

        orchestrator.run_many(tasks, experience=experience)

        stats = experience.get_stats()
        assert stats["total_engagements"] == len(tasks)
        assert stats["by_domain"] == {"land": len(tasks)}

    def test_identical_tasks_produce_identical_outcomes(self):
        orchestrator = Orchestrator(_POLICY)
        first = orchestrator.run(synthetic_profile(42))
        second = orchestrator.run(synthetic_profile(42))
        assert first.score == second.score
        assert first.selected_model == second.selected_model
        assert first.attempts_used == second.attempts_used

    def test_classified_requests_route_like_profiles(self):
        """A raw request dict routes straight to the local tier."""
        request = {
            "id": "req-77",
            "description": "confidential mission plan with waypoints; "
                           "derive the optimal strategy",
            "privacy_required": True,
        }
        profile = classify(request)
        assert profile.privacy_required is True
        decisions = _POLICY.decide(profile)
        routed_models = {d.model.name for d in decisions}
        assert routed_models <= {"local-7b", "local-70b"}