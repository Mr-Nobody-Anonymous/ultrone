# Copyright (c) Ultrone Contributors. All rights reserved.
"""Adversarial evaluation families for candidate model promotion.

Training a model whose only evidence is the curriculum it was taught
is how systems fool themselves. Before any candidate is promoted it
is measured against five families:

- ``normal``          -- the curriculum mix itself (regression floor)
- ``unseen``          -- synthetic instances never used in training
- ``difficult``       -- high-difficulty stress
- ``fault_recovery``  -- context shortfalls + hard retry conditions
- ``adversarial``     -- difficult + tools + privacy, together

Each family is scored by running the candidate's executor and the
baseline's executor over the SAME deterministic task list. Promotion
requires the aggregate to improve (adaptive Evaluator gate) AND
per-family regression to stay within tolerance -- a candidate that
wins on average by quietly breaking one family is refused, and that
refusal is recorded before any BrainStore write.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from orchestration.router import Orchestrator, RoutingPolicy
from orchestration.task_classifier import TaskProfile, synthetic_profile

from self_improvement.self_training.trainer import (
    LearnedWeights,
    make_executor,
)

#: A candidate may not regress more than this on any single task.
DEFAULT_TOLERANCE = 0.12


def _scenario(seed: int, *, prefix: str, **overrides) -> TaskProfile:
    """One deterministic family instance with optional demand overrides."""
    base = synthetic_profile(seed, name_prefix=prefix)
    return TaskProfile(
        domain=overrides.get("domain", base.domain),
        difficulty=overrides.get("difficulty", base.difficulty),
        reasoning_depth=overrides.get("reasoning_depth",
                                      base.reasoning_depth),
        context_requirement=overrides.get("context_requirement",
                                          base.context_requirement),
        tool_requirement=overrides.get("tool_requirement",
                                       base.tool_requirement),
        latency_sensitivity=overrides.get("latency_sensitivity",
                                          base.latency_sensitivity),
        privacy_required=overrides.get("privacy_required", False),
        task_id=f"{prefix}-{seed}",
        source_summary=f"{prefix}#{seed}")


def build_families(n_each: int = 8,
                   base_seed: int = 400) -> Dict[str, List[TaskProfile]]:
    """Deterministic task families in disjoint seed zones."""
    children = {}
    children["normal"] = [
        _scenario(11 + i, prefix="normal") for i in range(n_each)]
    children["unseen"] = [
        _scenario(base_seed + i, prefix="unseen",
                  difficulty=max(((base_seed + i) % 100) / 100, 0.35))
        for i in range(n_each)]
    children["difficult"] = [
        _scenario(201 + i, prefix="difficult", difficulty=0.9,
                  reasoning_depth=0.9) for i in range(n_each)]
    children["fault_recovery"] = [
        _scenario(301 + i, prefix="recovery", difficulty=0.7,
                  reasoning_depth=0.7, context_requirement=0.95)
        for i in range(n_each)]
    children["adversarial"] = [
        _scenario(401 + i, prefix="adversarial", difficulty=0.95,
                  reasoning_depth=0.9, tool_requirement=0.95,
                  privacy_required=(i % 2 == 0))
        for i in range(n_each)]
    return children


def score_weights(weights: LearnedWeights, profiles: List[TaskProfile],
                  *, policy: Optional[RoutingPolicy] = None
                  ) -> Dict[str, float]:
    """Per-task scores under a weights-built executor."""
    executor = make_executor(weights)
    orchestrator = Orchestrator(policy or RoutingPolicy(),
                                executor=executor)
    return {o.task_id: o.score for o in orchestrator.run_many(profiles)}


@dataclass
class FamilyReport:
    family: str
    baseline_mean: float
    candidate_mean: float
    mean_delta: float
    regressions: List[Tuple[str, float]] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.regressions


@dataclass
class RegressionReport:
    families: Dict[str, FamilyReport]
    tolerance: float
    candidate_weights: LearnedWeights
    baseline_weights: LearnedWeights

    @property
    def family_regressions(self) -> List[str]:
        return [name for name, rep in sorted(self.families.items())
                if rep.regressions]

    @property
    def passed(self) -> bool:
        return not self.family_regressions

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tolerance": self.tolerance,
            "families": {name: self.families[name].__dict__
                         for name in sorted(self.families)},
            "passed": self.passed}


class RegressionSuite:
    """Pre-promotion gate: mean gain plus bounded per-family regression."""

    def __init__(self, tolerance: float = DEFAULT_TOLERANCE,
                 families: Optional[Dict[str, List[TaskProfile]]] = None
                 ) -> None:
        if tolerance < 0:
            raise ValueError("tolerance must be non-negative")
        self.tolerance = float(tolerance)
        self.families = families or build_families()

    def run(self, candidate: LearnedWeights,
            baseline: LearnedWeights) -> RegressionReport:
        reports: Dict[str, FamilyReport] = {}
        for name, profiles in sorted(self.families.items()):
            base_scores = score_weights(baseline, profiles)
            cand_scores = score_weights(candidate, profiles)
            regressions: List[Tuple[str, float]] = []
            for task_id, base in base_scores.items():
                delta = cand_scores[task_id] - base
                if delta < -self.tolerance:
                    regressions.append((task_id, round(delta, 6)))
            base_mean = (sum(base_scores.values()) / len(base_scores)
                         if base_scores else 0.0)
            cand_mean = (sum(cand_scores.values()) / len(cand_scores)
                         if cand_scores else 0.0)
            reports[name] = FamilyReport(
                family=name,
                baseline_mean=round(base_mean, 6),
                candidate_mean=round(cand_mean, 6),
                mean_delta=round(cand_mean - base_mean, 6),
                regressions=regressions)
        return RegressionReport(families=reports,
                                tolerance=self.tolerance,
                                candidate_weights=candidate,
                                baseline_weights=baseline)