# Copyright (c) Ultrone Contributors. All rights reserved.
"""Multidimensional capability evaluation for candidate models.

Phase-4 measurement: instead of a single score, a candidate model is
reported across the dimensions ULTRONE actually cares about::

    ModelEvaluation
    ├── reasoning
    ├── planning
    ├── memory
    ├── tool use
    ├── generalization
    ├── robustness
    ├── simulation performance
    ├── regression
    ├── latency
    └── resource usage

Every value is computed *deterministically* by running the candidate's
executor over the same gated task families the promotion path uses, so
"is the loop-produced model measurably better than the one it started
with?" becomes an exact, re-runnable question -- unchanged whether the
underlying model is the statistical capability learner today or a real
neural/hosted backend behind the same ``make_executor`` seam tomorrow.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from orchestration.router import Orchestrator, RoutingPolicy

from self_improvement.self_training.regression import (
    RegressionReport,
)
from self_improvement.self_training.trainer import (
    LearnedWeights,
    make_executor,
)

#: Profile field a capability dimension loads against.
_CAP_FIELD: Dict[str, str] = {
    "reasoning": "reasoning_depth",
    "planning": "difficulty",
    "memory": "context_requirement",
    "tool_use": "tool_requirement",
}

_COMPOSITE_DIMS = ("reasoning", "planning", "memory", "tool_use",
                   "generalization", "robustness",
                   "simulation_performance")


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, float(v)))


@dataclass
class CapabilityMetrics:
    """All reported capabilities for one model.

    ``capability_source`` marks where the capability was measured:
    ``"simulated"`` (the statistical learner / simulator) vs ``"neural"``
    (a real network's trained output). This provenance is a hard
    separation -- never merge the two into one "got smarter" claim. A
    ``"simulated"`` gain is evidence the *surround* improved on the
    simulated task mix; it is NOT evidence the underlying neural model
    became more intelligent.
    """

    simulation_performance: float = 0.0
    reasoning: float = 0.0
    planning: float = 0.0
    memory: float = 0.0
    tool_use: float = 0.0
    generalization: float = 0.0
    robustness: float = 0.0
    regression_risk: float = 0.0      # most negative family delta (<= 0 = safe)
    latency_ms: float = 0.0
    resource_cost: float = 0.0
    capability_source: str = "simulated"

    def composite(self) -> float:
        """Equal-weight mean of the capability dimensions (scale ~ utility)."""
        core = [self.reasoning, self.planning, self.memory, self.tool_use,
                self.generalization, self.robustness,
                self.simulation_performance]
        return round(sum(core) / len(core), 6)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "simulation_performance": self.simulation_performance,
            "reasoning": self.reasoning,
            "planning": self.planning,
            "memory": self.memory,
            "tool_use": self.tool_use,
            "generalization": self.generalization,
            "robustness": self.robustness,
            "regression_risk": self.regression_risk,
            "latency_ms": self.latency_ms,
            "resource_cost": self.resource_cost,
            "capability_source": self.capability_source,
            "composite": self.composite(),
        }


def _run_outcomes(weights: LearnedWeights, profiles,
                  *, policy=None) -> Dict[str, Any]:
    """task_id -> OrchestrationOutcome under a weights-built executor."""
    orchestrator = Orchestrator(policy or RoutingPolicy(),
                                executor=make_executor(weights))
    outcomes = orchestrator.run_many(profiles)
    return {o.task_id: o for o in outcomes}


def evaluate_capabilities(
        weights: LearnedWeights,
        families: Dict[str, List[Any]],
        *, policy=None,
        capability_source: str = "simulated") -> CapabilityMetrics:
    """Score one model across every family; aggregate into capabilities.

    ``capability_source`` tokens the report as ``"simulated"`` or
    ``"neural"`` so a gain is never ambiguously attributed to the wrong
    substrate.
    """
    # Map every family's profiles to their outcomes in one pass each.
    task_by_id: Dict[str, Any] = {}
    profiles: List[Any] = []
    for profiles_list in families.values():
        for profile in profiles_list:
            profiles.append(profile)
            task_by_id[profile.task_id] = profile

    outcomes = _run_outcomes(weights, profiles, policy=policy)
    score_of = {tid: o.score for tid, o in outcomes.items()}
    latencies = [o.total_latency_ms for o in outcomes.values()] or [0.0]
    costs = [o.total_cost for o in outcomes.values()] or [0.0]

    def mean(xs):
        return round(sum(xs) / len(xs), 6) if xs else 0.0

    def weighted(field: str) -> float:
        num = den = 0.0
        for profile in profiles:
            weight = max(0.0, float(getattr(profile, field)))
            num += weight * score_of[profile.task_id]
            den += weight
        return round(num / den, 6) if den else 0.0

    family_mean = {name: mean(
        [score_of[p.task_id] for p in p_list])
        for name, p_list in families.items()}

    return CapabilityMetrics(
        simulation_performance=family_mean.get("normal", 0.0),
        reasoning=weighted("reasoning_depth"),
        planning=weighted("difficulty"),
        memory=weighted("context_requirement"),
        tool_use=weighted("tool_requirement"),
        generalization=family_mean.get("unseen", 0.0),
        robustness=family_mean.get("adversarial", 0.0),
        regression_risk=0.0,
        latency_ms=round(sum(latencies) / len(latencies), 4),
        resource_cost=round(sum(costs) / len(costs), 6),
        capability_source=capability_source)


@dataclass
class CapabilityComparison:
    """Baseline vs candidate across every reported dimension.

    ``deltas`` are candidate minus baseline per capability; the verdict
    implements the promotion criteria:
      overall improvement
      AND no critical regression
      AND holdout improvement
      AND reproducibility (recorded from the Evaluator, passed through)
    """

    baseline: CapabilityMetrics
    candidate: CapabilityMetrics
    deltas: Dict[str, float]
    regression: Optional[RegressionReport] = None
    regression_risk: float = 0.0          # most negative family mean delta
    overall: bool = False
    no_critical_regression: bool = True
    holdout_improvement: bool = False
    reproducible: bool = True

    @property
    def measurably_better(self) -> bool:
        return (self.overall and self.no_critical_regression
                and self.holdout_improvement and self.reproducible)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "baseline": self.baseline.to_dict(),
            "candidate": self.candidate.to_dict(),
            "deltas": dict(self.deltas),
            "regression_risk": self.regression_risk,
            "overall": self.overall,
            "no_critical_regression": self.no_critical_regression,
            "holdout_improvement": self.holdout_improvement,
            "reproducible": self.reproducible,
            "measurably_better": self.measurably_better,
            "regression_families": (
                list(self.regression.family_regressions)
                if self.regression else []),
        }


def _run_family_means(weights: LearnedWeights,
                      families: Dict[str, List[Any]],
                      *, policy=None) -> Dict[str, float]:
    """Mean orchestrator score per family under one weights executor."""
    outcomes = {}
    for name, profiles in families.items():
        runs = _run_outcomes(weights, profiles, policy=policy)
        scores = [o.score for o in runs.values()]
        outcomes[name] = round(sum(scores) / len(scores), 6) if scores \
            else 0.0
    return outcomes


def compare_capabilities(
        baseline: LearnedWeights,
        candidate: LearnedWeights,
        families: Dict[str, List[Any]],
        *, policy=None,
        regression: Optional[RegressionReport] = None,
        reproducible: bool = True,
        baseline_source: str = "simulated",
        candidate_source: str = "simulated") -> CapabilityComparison:
    """Measure candidate against baseline and apply the verdict criteria."""
    base_metrics = evaluate_capabilities(
        baseline, families, policy=policy,
        capability_source=baseline_source)
    cand_metrics = evaluate_capabilities(
        candidate, families, policy=policy,
        capability_source=candidate_source)
    base_scores = _run_family_means(baseline, families, policy=policy)
    cand_scores = _run_family_means(candidate, families, policy=policy)
    family_deltas = {name: round(cand_scores[name] - base_scores[name], 6)
                     for name in cand_scores}

    deltas = {name: round(getattr(cand_metrics, name)
                          - getattr(base_metrics, name), 6)
              for name in _COMPOSITE_DIMS}

    overall = cand_metrics.composite() > base_metrics.composite()
    holdout_up = family_deltas.get("unseen", 0.0) > 0
    if regression is not None:
        no_critical = regression.passed
    else:
        no_critical = min(family_deltas.values()) >= -1e-6 \
            if family_deltas else True

    return CapabilityComparison(
        baseline=base_metrics,
        candidate=cand_metrics,
        deltas=deltas,
        regression=regression,
        regression_risk=(round(min(family_deltas.values()), 6)
                         if family_deltas else 0.0),
        overall=overall,
        no_critical_regression=no_critical,
        holdout_improvement=holdout_up,
        reproducible=reproducible)