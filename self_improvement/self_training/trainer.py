# Copyright (c) Ultrone Contributors. All rights reserved.
"""The learning substrate: trainable capability state.

Honest scope (per the project charter): this is a *statistical
capability learner*, not a foundation model. It fits a per-dimension
capability vector -- how well ULTRONE executes reasoning, coding,
retrieval, tool use -- from evaluator-grade experiences, with prior
shrinkage toward the incumbent weights so a handful of lucky runs
cannot yank the model around.

``LearnedWeights`` is the serialized "model": it is hashed into
checkpoint lineage, promoted through BrainStore channels exactly like
any other governed configuration, and drives execution through
``make_executor`` -- the callable plugged into
``Orchestrator(executor=...)`` in place of the built-in simulator.
Swapping in a real neural trainer means fitting something heavier and
exposing the same ``from_config``/``to_config`` contract; every gate,
checkpoint, and trace keeps working unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List

from adaptive.optimizer import config_hash
from orchestration.model_registry import DIMENSIONS
from orchestration.router import capability_mix
from orchestration.task_classifier import TaskProfile

CONFIG_KIND = "learned_model_v1"


def _clamp01(value: float) -> float:
    return min(1.0, max(0.0, float(value)))


@dataclass
class LearnedWeights:
    """Capability vector over the closed dimension set."""

    values: Dict[str, float]

    def __post_init__(self) -> None:
        missing = [d for d in DIMENSIONS if d not in self.values]
        if missing:
            raise ValueError(f"weights missing dimensions: {missing}")
        extra = [d for d in self.values if d not in DIMENSIONS]
        if extra:
            raise ValueError(f"unknown dimensions: {extra}")
        self.values = {d: round(_clamp01(v), 6)
                       for d, v in sorted(self.values.items())}

    # -- serialization -------------------------------------------------- #
    def to_config(self) -> Dict[str, Any]:
        return {"kind": CONFIG_KIND, "weights": dict(self.values)}

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "LearnedWeights":
        if config.get("kind") != CONFIG_KIND:
            raise ValueError(f"config kind {config.get('kind')!r} "
                             f"is not {CONFIG_KIND!r}")
        return cls(values=dict(config.get("weights", {})))

    @classmethod
    def neutral(cls, level: float = 0.5) -> "LearnedWeights":
        return cls(values={d: float(level) for d in DIMENSIONS})

    @property
    def model_hash(self) -> str:
        return config_hash(self.to_config())

    def blend(self, target: "LearnedWeights",
              alpha: float) -> "LearnedWeights":
        if not 0.0 <= alpha <= 1.0:
            raise ValueError("alpha must be within [0, 1]")
        blended = {d: _clamp01((1 - alpha) * self.values[d]
                               + alpha * target.values[d])
                   for d in DIMENSIONS}
        return LearnedWeights(values=blended)


@dataclass
class FitResult:
    weights: LearnedWeights
    loss_history: List[float]
    examples_used: int


def _example_mix(example: Dict[str, Any]) -> Dict[str, float]:
    fields = example["input"]
    profile = TaskProfile(domain=fields["domain"],
                          difficulty=fields["difficulty"],
                          reasoning_depth=fields["reasoning_depth"],
                          context_requirement=fields[
                              "context_requirement"],
                          tool_requirement=fields["tool_requirement"],
                          latency_sensitivity=fields[
                              "latency_sensitivity"])
    return capability_mix(profile)


class StatisticalTrainer:
    """Prior-shrunk evidence accumulation toward successful demands."""

    def __init__(self, prior_strength: float = 4.0) -> None:
        if prior_strength <= 0:
            raise ValueError("prior_strength must be positive")
        self.prior_strength = float(prior_strength)

    def fit(self, examples: List[Dict[str, Any]],
            current: LearnedWeights) -> FitResult:
        if not examples:
            return FitResult(weights=current, loss_history=[0.0],
                             examples_used=0)

        def residual(w: LearnedWeights) -> float:
            errs = []
            for example in examples:
                mix = _example_mix(example)
                target = float(example["outcome_score"])
                fit = sum(mix[d] * w.values[d] for d in DIMENSIONS)
                errs.append(abs(target - fit))
            return round(sum(errs) / len(errs), 6)

        before = residual(current)
        numerator = {d: self.prior_strength * current.values[d]
                     for d in DIMENSIONS}
        denominator = {d: self.prior_strength for d in DIMENSIONS}
        for example in examples:
            mix = _example_mix(example)
            score = _clamp01(float(example["outcome_score"]))
            for d in DIMENSIONS:
                numerator[d] += score * mix[d]
                denominator[d] += mix[d]
        updated = LearnedWeights(values={
            d: numerator[d] / max(denominator[d], 1e-9)
            for d in DIMENSIONS})
        after = residual(updated)
        return FitResult(weights=updated,
                         loss_history=[before, after],
                         examples_used=len(examples))


def make_executor(weights: LearnedWeights) -> Callable:
    """Build an Orchestrator execution-judge from capability weights.

    Contract: same physics family as ``router.simulate_quality`` --
    capability fit of the *learned* vector against the task's demand
    mix, penalized for truncated context and retry fatigue. It does
    NOT model planner-parameter finesse; candidate comparisons stay
    internally consistent because every side is judged identically.
    """
    learned = weights.values

    def judge(decision, profile, bundle, attempt_index) -> float:
        mix = capability_mix(profile)
        fit = sum(mix[d] * learned[d] for d in DIMENSIONS)
        quality = 0.15 + 0.65 * fit
        if getattr(bundle, "truncated", False):
            quality -= 0.06
        quality -= 0.025 * max(0, int(attempt_index))
        return round(_clamp01(quality), 6)

    return judge
