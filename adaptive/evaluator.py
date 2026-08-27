# Copyright (c) Ultrone Contributors. All rights reserved.
"""Evaluation suite: the benchmark decides, never self-assessment.

A candidate configuration is scored by running a deterministic
evaluation task and compared against baseline. Two hard rules:

1. **Reproducibility gate** -- candidates run more than once; if
   repeated runs disagree the result is ``non_reproducible`` regardless
   of score.
2. **Margin gate** -- must beat baseline by at least the configured
   margin to be promotable.

Built-in task: a ground robot patrol scored on waypoints reached minus
tick cost minus an energy penalty growing with speed squared -- so
faster is not automatically better and the optimum is interior.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Tuple

EvalTask = Callable[[Dict[str, Any]], float]

_REPEATS = 3


# --------------------------------------------------------------------- #
# Scenario family: the *world* varies; candidates vary the *config*      #
# --------------------------------------------------------------------- #
@dataclass(frozen=True)
class PatrolScenario:
    """One environment instance of the ground-patrol benchmark.

    Scenarios vary the world (waypoint layout, per-leg tick budget,
    platform top speed) while candidate configurations vary the agent
    (patrol speed, wear sensitivity). Splitting a seed space into
    training and holdout scenario sets makes *generalization to unseen
    worlds measurable* rather than assumed -- the learning benchmark in
    ``benchmarks/learning_benchmark.py`` depends on that property.
    """

    name: str
    waypoints: Tuple[Tuple[float, float], ...]
    tick_budget: int = 240
    max_speed: float = 2.5


DEFAULT_SCENARIO = PatrolScenario(
    name="default_patrol",
    waypoints=((6.0, 0.0), (12.0, 4.0), (18.0, 4.0), (24.0, 8.0)),
)


def scenario_from_seed(seed: int, legs: int = 4,
                       name: str = "") -> PatrolScenario:
    """Deterministically generate one patrol scenario from a seed.

    Waypoints form a connected route where every leg is long enough
    (>= 5 units) that cruise speed genuinely matters. Tick budgets are
    jittered per leg so faster-is-not-always-better holds in every
    scenario, keeping the interior optimum property of the metric.
    """
    rng = random.Random(int(seed))
    waypoints: List[Tuple[float, float]] = []
    x, y = 0.0, 0.0
    for _ in range(max(1, legs)):
        while True:
            nx = round(rng.uniform(0.0, 30.0), 2)
            ny = round(rng.uniform(0.0, 12.0), 2)
            if math.hypot(nx - x, ny - y) >= 5.0:
                waypoints.append((nx, ny))
                x, y = nx, ny
                break
    return PatrolScenario(
        name=name or f"patrol_{seed}",
        waypoints=tuple(waypoints),
        tick_budget=int(rng.randint(200, 260)),
        max_speed=2.5,
    )


def make_patrol_task(scenario: PatrolScenario) -> EvalTask:
    """Build a deterministic scoring task bound to one scenario."""
    waypoints = tuple(scenario.waypoints)

    def task(config: Dict[str, Any]) -> float:
        from agents.commands import Command
        from agents.subsystems.locomotion import MobilitySubsystem
        from agents.subsystems.platform_subsystems import (
            HealthSubsystem, NavigationSubsystem)

        speed = float(config.get("patrol.speed",
                                 config.get("patrol_speed", 1.0)))
        wear_scale = float(config.get("patrol.wear_sensitivity",
                                      config.get("wear_sensitivity", 1.0)))

        mobility = MobilitySubsystem(max_speed=scenario.max_speed)
        mobility.handle("set_mode", {"mode": "wheels"})
        navigation = NavigationSubsystem(x=0.0, y=0.0)
        health = HealthSubsystem(wear_rate=0.0)

        reached = 0
        ticks_used = 0
        energy = 0.0
        for wx, wy in waypoints:
            for _ in range(scenario.tick_budget):
                dx, dy = wx - navigation.x, wy - navigation.y
                dist = math.hypot(dx, dy)
                if dist <= 0.5:
                    reached += 1
                    break
                bearing = math.atan2(dy, dx)
                navigation.set_heading(math.degrees(bearing))
                step = min(speed, max(0.35, dist * 0.3))
                rad = math.radians(navigation.heading_deg)
                navigation.x += math.cos(rad) * step
                navigation.y += math.sin(rad) * step
                mobility.drive(step)
                mobility.tick(ticks_used)
                ticks_used += 1
                energy += step * step
            else:
                break                               # budget exhausted

        wear = min(100.0, health.wear + wear_scale * energy / 40.0)
        return round(10.0 * reached - ticks_used / 10.0 - energy / 50.0
                     - wear / 100.0, 6)

    return task


def ground_patrol_score(config: Dict[str, Any]) -> float:
    """Score a patrol-speed config on the default simulated waypoint run."""
    return make_patrol_task(DEFAULT_SCENARIO)(config)


# --------------------------------------------------------------------- #
# Comparison with gates                                                  #
# --------------------------------------------------------------------- #
@dataclass
class EvaluationResult:
    decision: str                       # promote | reject | non_reproducible
    candidate_score: float
    baseline_score: float
    margin_required: float
    repeats: int
    candidate_runs: List[float] = field(default_factory=list)
    baseline_runs: List[float] = field(default_factory=list)
    reason: str = ""

    @property
    def promotable(self) -> bool:
        return self.decision == "promote"


class Evaluator:
    """Baseline-vs-candidate comparison with reproducibility gates."""

    def __init__(self, task: EvalTask = ground_patrol_score,
                 margin: float = 0.05, repeats: int = _REPEATS) -> None:
        if repeats < 2:
            raise ValueError("repeats must be >= 2 for reproducibility")
        self.task = task
        self.margin = float(margin)
        self.repeats = int(repeats)

    def evaluate(self, candidate_config: Dict[str, Any],
                 baseline_config: Dict[str, Any]) -> EvaluationResult:
        candidate_runs = [self.task(candidate_config)
                          for _ in range(self.repeats)]
        baseline_runs = [self.task(baseline_config)
                         for _ in range(self.repeats)]
        candidate_score = candidate_runs[0]
        baseline_score = baseline_runs[0]

        if len(set(candidate_runs)) != 1 or len(set(baseline_runs)) != 1:
            return EvaluationResult(
                decision="non_reproducible",
                candidate_score=candidate_score,
                baseline_score=baseline_score,
                margin_required=self.margin, repeats=self.repeats,
                candidate_runs=candidate_runs,
                baseline_runs=baseline_runs,
                reason="repeated evaluations disagreed")
        if candidate_score > baseline_score + self.margin:
            delta = round(candidate_score - baseline_score, 6)
            return EvaluationResult(
                decision="promote",
                candidate_score=candidate_score,
                baseline_score=baseline_score,
                margin_required=self.margin, repeats=self.repeats,
                candidate_runs=candidate_runs,
                baseline_runs=baseline_runs,
                reason=f"beats baseline by {delta}")
        return EvaluationResult(
            decision="reject",
            candidate_score=candidate_score,
            baseline_score=baseline_score,
            margin_required=self.margin, repeats=self.repeats,
            candidate_runs=candidate_runs,
            baseline_runs=baseline_runs,
            reason="does not clear margin over baseline")