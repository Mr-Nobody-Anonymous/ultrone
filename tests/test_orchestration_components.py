# Copyright (c) Ultrone Contributors. All rights reserved.
"""Unit tests for orchestration building blocks."""

from __future__ import annotations

import json

import pytest

from orchestration.cost_policy import CostEstimate, CostPolicy, price_items
from orchestration.fallback import build_chain
from orchestration.memory_router import (
    default_memory_registry,
    select_memory,
)
from orchestration.model_registry import (
    DIMENSIONS,
    ModelSpec,
    default_model_registry,
)
from orchestration.result_validator import (
    StructuredResult,
    demand_level,
    validate_result,
)
from orchestration.task_classifier import (
    DOMAINS,
    TaskProfile,
    classify,
    synthetic_profile,
)
from orchestration.tool_registry import (
    default_tool_registry,
    select_tools,
)
from orchestration.traces import AttemptRecord, OrchestrationTrace, TraceLog


def _strengths(value: float = 0.5):
    return {dim: value for dim in DIMENSIONS}


class TestModelRegistry:
    def test_incomplete_strengths_rejected(self):
        registry = default_model_registry()
        with pytest.raises(ValueError):
            ModelSpec(
                name="broken", capabilities=frozenset({"fast"}),
                context_window=1_000, cost_per_call=1.0,
                latency_ms=10.0, strengths={"reasoning": 0.5})
        assert not registry.has("broken")

    def test_duplicate_names_rejected(self):
        registry = default_model_registry()
        duplicate = ModelSpec(
            name="nano", capabilities=frozenset(), context_window=1_000,
            cost_per_call=1.0, latency_ms=10.0, strengths=_strengths())
        with pytest.raises(ValueError):
            registry.register(duplicate)

    def test_builtin_catalog_has_real_tradeoffs(self):
        registry = default_model_registry()
        nano = registry.get("nano")
        reasoner = registry.get("reasoner")
        assert nano.cost_per_call < reasoner.cost_per_call
        assert reasoner.strengths["reasoning"] \
            > nano.strengths["reasoning"]
        assert registry.get("local-70b").local_only
        assert not registry.get("balanced").local_only


class TestTaskProfileAndClassifier:
    def test_dimensions_clamped_and_domain_fallback(self):
        profile = TaskProfile(domain="nonsense", difficulty=7.0,
                              reasoning_depth=-1.0)
        assert profile.domain in DOMAINS
        assert profile.difficulty == 1.0
        assert profile.reasoning_depth == 0.0

    def test_context_tokens_increase_monotonically(self):
        light = TaskProfile(domain="analysis", context_requirement=0.05)
        heavy = TaskProfile(domain="analysis", context_requirement=0.92)
        assert light.context_tokens < heavy.context_tokens

    def test_explicit_fields_beat_keywords(self):
        classified = classify({"description": "prove why the bug exists",
                               "difficulty": 0.11})
        assert classified.difficulty == pytest.approx(0.11)

    def test_keyword_evidence_fills_gaps(self):
        coded = classify({"description":
                          "implement the function and refactor its tests"})
        assert coded.domain == "coding"
        secret = classify({"description":
                           "summarize the confidential internal report"})
        assert secret.privacy_required is True

    def test_synthetic_family_is_deterministic(self):
        assert synthetic_profile(42) == synthetic_profile(42)


class TestSelectionHelpers:
    def test_low_context_task_skips_tiered_memory(self):
        registry = default_memory_registry()
        light = TaskProfile(domain="analysis", context_requirement=0.05)
        assert select_memory(registry, light).name != "tiered"

    def test_high_context_task_gets_full_coverage(self):
        registry = default_memory_registry()
        heavy = TaskProfile(domain="analysis", context_requirement=0.95)
        assert select_memory(registry, heavy).coverage_until >= 0.9

    def test_richness_appetite_upgrades_mid_context(self):
        """Appetite may buy insurance headroom, never fake support."""
        registry = default_memory_registry()
        mid = TaskProfile(domain="analysis", context_requirement=0.50)
        frugal = select_memory(registry, mid, richness_weight=0.0)
        greedy = select_memory(registry, mid, richness_weight=2.0)
        assert frugal.name != greedy.name
        # The richer appetite lands on a strategy that covers more of
        # the demand spectrum (or boosts recall at least as much).
        assert (greedy.coverage_until >= frugal.coverage_until
                or greedy.recall_boost >= frugal.recall_boost)

    def test_tool_selection_respects_domain_and_cap(self):
        registry = default_tool_registry()
        sim_task = TaskProfile(domain="simulation", tool_requirement=0.8)
        kit = select_tools(registry, sim_task, max_tools=2)
        assert 1 <= len(kit) <= 2
        assert all(sim_task.domain in t.domains for t in kit)


class TestCostPolicy:
    def test_price_items_aggregates(self):
        estimate = price_items([(0.20, 150.0), (0.15, 80.0)])
        assert estimate.credits == pytest.approx(0.35)
        assert estimate.latency_ms == pytest.approx(230.0)

    def test_penalty_rises_with_weights(self):
        estimate = CostEstimate(credits=1.0, latency_ms=750.0)
        base = CostPolicy(cost_weight=0.5, latency_weight=0.4)
        spendy = CostPolicy(cost_weight=2.0, latency_weight=2.0)
        assert spendy.penalty(estimate, 0.8) > base.penalty(estimate, 0.8)

    def test_budget_gate(self):
        policy = CostPolicy(budget_cap_credits=1.0)
        assert policy.within_budget(CostEstimate(0.9, 10.0))
        assert not policy.within_budget(CostEstimate(1.1, 10.0))


class TestResultValidator:
    def test_rules_report_the_first_violation(self):
        profile = TaskProfile(domain="coding", difficulty=0.5)
        hollow = StructuredResult(answer=None, quality=0.02,
                                  model="x", latency_ms=1.0)
        report = validate_result(hollow, profile)
        assert not report.ok
        assert "answer" in report.reason

    def test_confidence_floor_enforced(self):
        profile = TaskProfile(domain="coding", difficulty=0.1)
        weak = StructuredResult(answer={"ok": 1}, quality=0.05,
                                model="m", latency_ms=1.0)
        report = validate_result(weak, profile, min_confidence=0.99)
        assert not report.ok
        assert "confidence" in report.reason

    def test_demand_bar_scales_with_difficulty(self):
        easy = TaskProfile(domain="coding", difficulty=0.1)
        hard = TaskProfile(domain="coding", difficulty=0.9)
        assert demand_level(hard) > demand_level(easy)

    def test_acceptance_happy_path(self):
        profile = TaskProfile(domain="coding", difficulty=0.3)
        solid = StructuredResult(answer={"done": True}, quality=0.75,
                                 model="m", latency_ms=5.0)
        assert validate_result(solid, profile).ok


class TestFallbackChain:
    def test_pops_best_first_then_exhausts(self):
        chain = build_chain([("a", "first"), ("b", "second")],
                            max_attempts=2)
        assert chain.next_candidate() == "first"
        assert chain.next_candidate() == "second"
        assert chain.exhausted
        assert chain.next_candidate() is None


class TestTraces:
    def test_roundtrip_preserves_fields(self):
        trace = OrchestrationTrace(
            task_id="t1",
            task_profile=synthetic_profile(5),
            selected_model="reasoner", selected_memory="vector_recall",
            selected_skills=("tactics-planner",),
            parameters={"planning_depth": 3},
            result={"quality": 0.91}, latency_ms=1400.0, score=7.5,
            total_cost=1.8,
            failures=[AttemptRecord(attempt=1, model="nano",
                                    memory="none", tools=(), skills=(),
                                    quality=0.4, validated=False,
                                    reason="demand unmet", cost=0.05,
                                    latency_ms=120.0)],
            accepted=True, attempts_used=1,
            configuration_hash="deadbeef0001")
        restored = OrchestrationTrace.from_dict(trace.to_dict())
        assert restored.selected_model == "reasoner"
        assert restored.task_profile.task_id == "synthetic-5"
        assert restored.failures[0].model == "nano"
        assert restored.configuration_hash == "deadbeef0001"

    def test_tracelog_is_append_only_jsonl(self, tmp_path):
        log = TraceLog(tmp_path / "traces.jsonl")
        for seed in (1, 2):
            log.append(OrchestrationTrace(
                task_id=f"t-{seed}",
                task_profile=synthetic_profile(seed),
                selected_model="balanced", selected_memory="none"))
        loaded = TraceLog(tmp_path / "traces.jsonl").load()
        assert [t.task_id for t in loaded] == ["t-1", "t-2"]
        raw_lines = (tmp_path / "traces.jsonl").read_text(
            encoding="utf-8").strip().splitlines()
        assert len(raw_lines) == 2
        assert all(json.loads(line) for line in raw_lines)