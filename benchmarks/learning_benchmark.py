# Copyright (c) Ultrone Contributors. All rights reserved.
"""Measurable closed-loop learning benchmark over scenario families.

This answers the question ``tests/test_closed_loop_learning.py``
cannot: does repeated cycling actually *learn* anything? A single
fixed task conflates tuning luck with adaptation. Here the evaluator
task is a family of seeded patrol scenarios split into:

- **training scenarios** -- what reflection + optimization see;
- **holdout / unseen scenarios** -- never touched during adaptation;
  improvement there evidences genuine generalization instead of
  memorizing one waypoint map.

Every cycle follows the same governed pipeline as production::

    Episode -> ExperienceMemory -> Reflection -> candidate
      -> Evaluator (reproducibility + margin gates)
      -> PromotionGate (audit) -> BrainStore (production)

and ends with the four verdict lines that matter::

    Training scenarios   ↑ performance?
    Unseen scenarios     ↑ performance?
    Regression suite     PASS?
    Reproducibility      PASS?

The regression suite guards previously solved scenarios against
promotion-induced damage; it is deliberately NOT the objective being
optimized. Run standalone: ``python -m benchmarks.learning_benchmark``
"""

from __future__ import annotations

import json
import statistics
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from adaptive.evaluator import (
    EvalTask,
    Evaluator,
    PatrolScenario,
    make_patrol_task,
    scenario_from_seed,
)
from adaptive.optimizer import (
    AdaptiveOptimizer,
    Candidate,
    config_hash,
    default_patrol_registry,
)
from adaptive.parameter_registry import ParameterRegistry
from adaptive.promotion import BrainStore, PromotionGate
from brain.learning.experience_memory import (
    EngagementHistory,
    EngagementOutcome,
    ExperienceMemory,
)

#: Absolute score drop any previously-passing scenario may suffer
#: before the regression suite fails the promotion.
REGRESSION_TOLERANCE = 1e-6


# --------------------------------------------------------------------- #
# Reflection: recorded experience -> advisory proposal                   #
# --------------------------------------------------------------------- #
@dataclass(frozen=True)
class ReflectionProposal:
    """Advisory config delta mined from recorded experience.

    Same transparent rule as the integration test: useful engagement
    (nonzero damage) earns a modest speed increase. Deliberately not a
    learned policy -- the Evaluator decides which proposals survive.
    """

    overrides: Dict[str, Any]
    rationale: str


def reflect_on_experience(engagement: EngagementHistory,
                          registry: ParameterRegistry) -> ReflectionProposal:
    """Propose an advisory override from one recorded engagement."""
    if engagement.damage_dealt <= 0.0:
        return ReflectionProposal(
            overrides={},
            rationale="engagement produced no damage; no proposal",
        )
    speed = float(registry.snapshot().get("patrol.speed", 1.2))
    return ReflectionProposal(
        overrides={"patrol.speed": round(min(speed * 1.05, 2.4), 4)},
        rationale="engagement caused damage; compress the kill chain "
                  "with slightly faster patrol",
    )


# --------------------------------------------------------------------- #
# Report: measurements + the headline table                              #
# --------------------------------------------------------------------- #
@dataclass(frozen=True)
class IterationRecord:
    """Best-so-far training score after one learning cycle."""

    iteration: int
    train_score: float
    config_hash: str


@dataclass
class BenchmarkReport:
    """Everything the headline table needs, plus machine-readable form."""

    train_seeds: Tuple[int, ...]
    holdout_seeds: Tuple[int, ...]
    iterations: List[IterationRecord] = field(default_factory=list)
    baseline_train_scores: Dict[str, float] = field(default_factory=dict)
    final_train_scores: Dict[str, float] = field(default_factory=dict)
    baseline_holdout_scores: Dict[str, float] = field(default_factory=dict)
    final_holdout_scores: Dict[str, float] = field(default_factory=dict)
    decision: str = ""
    reason: str = ""
    promoted: bool = False
    config_hash: str = ""
    regression_failures: List[str] = field(default_factory=list)
    reproducibility_passed: bool = False

    # -- aggregates ------------------------------------------------------- #
    @property
    def baseline_train_mean(self) -> float:
        return self._mean(self.baseline_train_scores)

    @property
    def final_train_mean(self) -> float:
        return self._mean(self.final_train_scores)

    @property
    def baseline_holdout_mean(self) -> float:
        return self._mean(self.baseline_holdout_scores)

    @property
    def final_holdout_mean(self) -> float:
        return self._mean(self.final_holdout_scores)

    @property
    def regression_suite_passed(self) -> bool:
        return not self.regression_failures

    @property
    def learning_curve_monotone(self) -> bool:
        scores = [r.train_score for r in self.iterations]
        return all(a <= b for a, b in zip(scores, scores[1:]))

    @staticmethod
    def _mean(scores: Dict[str, float]) -> float:
        return round(statistics.fmean(scores.values()), 6) if scores else 0.0

    # -- presentation ------------------------------------------------------ #
    @staticmethod
    def _arrow(before: float, after: float) -> str:
        glyph = "↑" if after > before else ("↓" if after < before else "→")
        return f"{glyph} ({before:.2f} -> {after:.2f})"

    def to_table(self) -> str:
        """Human-readable summary in the charter's headline format."""
        reg_label = "PASS" if self.regression_suite_passed else "FAIL"
        repro_label = "PASS" if self.reproducibility_passed else "FAIL"
        train_arrow = self._arrow(self.baseline_train_mean,
                                  self.final_train_mean)
        holdout_arrow = self._arrow(self.baseline_holdout_mean,
                                    self.final_holdout_mean)
        decision_label = self.decision or "not reviewed"
        lines = [f"{'':21}{'Score':>14}",
                 f"{'Baseline episode':<21}"
                 f"{self.baseline_train_mean:>14.2f}"]
        for rec in self.iterations:
            lines.append(f"{f'Iteration {rec.iteration}':<21}"
                         f"{rec.train_score:>14.2f}")
        lines.append("")
        lines.append(f"{'Training scenarios':<21}{train_arrow}")
        lines.append(f"{'Unseen scenarios':<21}{holdout_arrow}")
        lines.append(f"{'Regression suite':<21}{reg_label}")
        if not self.regression_suite_passed:
            for failure in self.regression_failures:
                lines.append(f"{'  regression damage':<21}{failure}")
        lines.append(f"{'Reproducibility':<21}{repro_label}")
        lines.append(f"{'Promotion':<21}"
                     f"{decision_label} ({self.reason})")
        lines.append(f"{'Production hash':<21}{self.config_hash}")
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "train_seeds": list(self.train_seeds),
            "holdout_seeds": list(self.holdout_seeds),
            "iterations": [
                {"iteration": r.iteration, "train_score": r.train_score,
                 "config_hash": r.config_hash} for r in self.iterations],
            "baseline_train_mean": self.baseline_train_mean,
            "final_train_mean": self.final_train_mean,
            "baseline_holdout_mean": self.baseline_holdout_mean,
            "final_holdout_mean": self.final_holdout_mean,
            "baseline_train_scores": dict(self.baseline_train_scores),
            "final_train_scores": dict(self.final_train_scores),
            "baseline_holdout_scores": dict(self.baseline_holdout_scores),
            "final_holdout_scores": dict(self.final_holdout_scores),
            "decision": self.decision,
            "reason": self.reason,
            "promoted": self.promoted,
            "config_hash": self.config_hash,
            "regression_failures": list(self.regression_failures),
            "regression_suite_passed": self.regression_suite_passed,
            "learning_curve_monotone": self.learning_curve_monotone,
            "reproducibility_passed": self.reproducibility_passed,
        }

    def save_json(self, path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(self.to_dict(), sort_keys=True, indent=2),
            encoding="utf-8")


# --------------------------------------------------------------------- #
# The benchmark                                                          #
# --------------------------------------------------------------------- #
class LearningBenchmark:
    """Closed-loop cycles scored across training AND unseen worlds."""

    def __init__(
        self,
        train_seeds: Sequence[int] = (11, 23, 37, 41, 53),
        holdout_seeds: Sequence[int] = (7, 19, 29, 47, 59),
        iterations: int = 6,
        population_size: int = 8,
        generations_per_iteration: int = 2,
        mutation_sigma: float = 0.25,
        promotion_margin: float = 0.01,
        seed: int = 13,
        legs: int = 4,
        storage_dir: Optional[str] = None,
    ) -> None:
        if set(train_seeds) & set(holdout_seeds):
            raise ValueError(
                "training and holdout seed sets must be disjoint -- "
                "'unseen' means never evaluated during adaptation")
        if iterations < 1:
            raise ValueError("iterations must be >= 1")

        self.train_seeds = tuple(int(s) for s in train_seeds)
        self.holdout_seeds = tuple(int(s) for s in holdout_seeds)
        self.iterations = int(iterations)
        self.population_size = int(population_size)
        self.generations_per_iteration = int(generations_per_iteration)
        self.mutation_sigma = float(mutation_sigma)
        self.promotion_margin = float(promotion_margin)
        self.seed = int(seed)
        self.legs = int(legs)
        self.storage_dir = storage_dir

    # -- helpers ------------------------------------------------------------ #
    def _scenarios(self, seeds: Sequence[int],
                   tag: str) -> List[PatrolScenario]:
        return [scenario_from_seed(s, legs=self.legs, name=f"{tag}_{s}")
                for s in seeds]

    @staticmethod
    def _aggregate_task(pairs: Sequence[Tuple[str, EvalTask]]) -> EvalTask:
        """Mean score across a scenario set; the optimization objective."""
        def objective(config: Dict[str, Any]) -> float:
            return statistics.fmean(task(config) for _, task in pairs)
        return objective

    @staticmethod
    def _record_engagement(experience: ExperienceMemory,
                           scenario: PatrolScenario,
                           score: float) -> EngagementHistory:
        engagement = EngagementHistory(
            engagement_id=f"episode::{scenario.name}",
            attacker_id="agent:scout-01",
            target_id="target:waypoint-set",
            domain="land",
            engagement_type="patrol",
            outcome=(EngagementOutcome.SUCCESSFUL if score > 30.0
                     else EngagementOutcome.PARTIAL),
            duration_ms=float(scenario.tick_budget),
            kill_chain_phases=["move", "engage"],
            tactics_used=[scenario.name],
            casualties=0,
            damage_dealt=max(score, 0.0),
            notes=f"score={score}",
        )
        experience.record_engagement(engagement)
        return engagement

    # -- main entry --------------------------------------------------------- #
    def run(self) -> BenchmarkReport:
        train_scenarios = self._scenarios(self.train_seeds, "train")
        holdout_scenarios = self._scenarios(self.holdout_seeds, "holdout")
        train_pairs = [(sc.name, make_patrol_task(sc))
                       for sc in train_scenarios]
        holdout_pairs = [(sc.name, make_patrol_task(sc))
                         for sc in holdout_scenarios]

        baseline_config = default_patrol_registry().snapshot()
        baseline_train = {name: task(baseline_config)
                          for name, task in train_pairs}
        baseline_holdout = {name: task(baseline_config)
                            for name, task in holdout_pairs}

        # Steps 1-2: episodes run under baseline; experience recorded so
        # reflection has something to read.
        experience = ExperienceMemory(max_history=len(self.train_seeds) * 10)
        for scenario in train_scenarios:
            self._record_engagement(experience, scenario,
                                    baseline_train[scenario.name])

        # Step 3: reflection proposes an advisory delta from experience;
        # step 4: search refines that starting point against the
        # *aggregate* training objective (never the holdout set).
        working_registry = default_patrol_registry()
        proposal = reflect_on_experience(experience.engagements[-1],
                                         working_registry)
        if proposal.overrides:
            working_registry.apply(proposal.overrides)

        train_objective = self._aggregate_task(train_pairs)
        optimizer = AdaptiveOptimizer(
            working_registry,
            Evaluator(task=train_objective, margin=self.promotion_margin,
                      repeats=3),
            population_size=self.population_size,
            mutation_sigma=self.mutation_sigma,
            seed=self.seed,
        )

        report = BenchmarkReport(
            train_seeds=self.train_seeds,
            holdout_seeds=self.holdout_seeds,
            baseline_train_scores=baseline_train,
            baseline_holdout_scores=baseline_holdout,
        )

        global_best: Optional[Candidate] = None
        for iteration in range(1, self.iterations + 1):
            challenger = optimizer.run(
                generations=self.generations_per_iteration).best
            if global_best is None or challenger.score > global_best.score:
                global_best = challenger
            elif challenger.score == global_best.score:
                # Deterministic tie-break keeps runs bit-reproducible.
                global_best = min((global_best, challenger),
                                  key=lambda c: config_hash(c.config))
            # Warm-start the next cycle from the champion so the
            # iteration scores form a monotone learning curve.
            optimizer.registry.apply(global_best.config)
            report.iterations.append(IterationRecord(
                iteration=iteration,
                train_score=round(global_best.score, 6),
                config_hash=config_hash(global_best.config)))

        assert global_best is not None
        final_config = global_best.config
        final_hash = config_hash(final_config)
        report.final_train_scores = {
            name: task(final_config) for name, task in train_pairs}
        report.final_holdout_scores = {
            name: task(final_config) for name, task in holdout_pairs}

        # Steps 5-7: governed promotion through reproducibility + margin
        # gates and the audited PromotionGate / BrainStore pair.
        evaluation = Evaluator(task=train_objective,
                               margin=self.promotion_margin,
                               repeats=3).evaluate(final_config,
                                                   baseline_config)
        gate = PromotionGate()
        record = gate.review(evaluation, final_config, final_hash)
        report.decision = record.decision
        report.reason = record.reason
        if record.decision == "promote":
            store = BrainStore(storage_dir=self.storage_dir)
            store.set_config("baseline", baseline_config)
            store.promote(final_config, record, gate)
            report.promoted = True
        report.config_hash = (
            final_hash if report.promoted else baseline_hash)

        # Step 8a: regression suite -- no previously passing scenario
        # may degrade beyond tolerance because of promotion.
        report.regression_failures = [
            f"{name}: {baseline_train[name]:.6f} -> "
            f"{report.final_train_scores[name]:.6f}"
            for name, base in baseline_train.items()
            if report.final_train_scores[name] < base - REGRESSION_TOLERANCE]

        # Step 8b: reproducibility -- replay every measured scenario a
        # second time and require bitwise-equal results.
        replay_final = {name: task(final_config)
                        for name, task in train_pairs}
        replay_baseline = {name: task(baseline_config)
                           for name, task in train_pairs}
        report.reproducibility_passed = (
            evaluation.decision != "non_reproducible"
            and replay_final == report.final_train_scores
            and replay_baseline == baseline_train)

        return report


if __name__ == "__main__":
    # The headline table uses ↑/↓/→ glyphs; Windows consoles default to
    # cp1252, which cannot encode them. Force UTF-8 before printing.
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:               # non-standard stream: leave alone
        pass
    benchmark = LearningBenchmark()
    print(benchmark.run().to_table())
