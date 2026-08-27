# Copyright (c) Ultrone Contributors. All rights reserved.
"""Measurable routing-policy optimization over task families.

The orchestration charter's payoff: the SAME adaptive machinery that
evolved patrol configurations now evolves the *routing policy itself*.
Routing knobs live in ``orchestration.router.default_routing_registry``
(regime thresholds, cost/latency aversion, memory appetite, planning
depth, validator intercept), so ``AdaptiveOptimizer`` mutates policy
the way it mutated ``patrol.speed`` -- and the result flows through the
identical Evaluator / PromotionGate / BrainStore pipeline::

                 Routing Candidate (registry snapshot)
                           |
              +------------+------------+
              v                         v
        Training tasks            Holdout tasks   (disjoint seeds)
              |                         |
              +----------+--------------+
                         v
                    mean utility  ->  AdaptiveOptimizer
                         v
                PromotionGate (audited)  ->  BrainStore production

Utility per task is SLO-based (``orchestration.router``): delivered
credit saturates just past the demand bar while spend bills in full,
so the optimizer's honest route to profit is spending *less* on easy
work and *more precisely* on hard work -- not chasing raw quality.

Reuses the report/table machinery from ``benchmarks.learning_benchmark``
so both benchmarks read identically in papers and dashboards. Run
standalone: ``python -m benchmarks.orchestration_benchmark``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from adaptive.evaluator import EvaluationResult, Evaluator
from adaptive.optimizer import (
    AdaptiveOptimizer,
    Candidate,
    config_hash,
)
from adaptive.parameter_registry import ParameterRegistry
from adaptive.promotion import BrainStore, PromotionGate

from benchmarks.learning_benchmark import (
    REGRESSION_TOLERANCE,
    BenchmarkReport,
    IterationRecord,
)

from orchestration.router import (
    Orchestrator,
    RoutingPolicy,
    default_routing_registry,
)
from orchestration.task_classifier import TaskProfile, synthetic_profile

#: Disjoint synthetic-task families; holdout tasks are NEVER seen by
#: the optimizer, so improvement there evidences generalization of the
#: *policy*, not memorized task answers.
DEFAULT_TRAIN_SEEDS = (11, 23, 37, 41, 53, 67, 71, 83)
DEFAULT_HOLDOUT_SEEDS = (7, 19, 29, 47, 59, 73)


class OrchestrationBenchmark:
    """Closed-loop evolution of a routing policy over task families."""

    def __init__(
        self,
        train_seeds: Sequence[int] = DEFAULT_TRAIN_SEEDS,
        holdout_seeds: Sequence[int] = DEFAULT_HOLDOUT_SEEDS,
        iterations: int = 5,
        population_size: int = 8,
        generations_per_iteration: int = 3,
        seed: int = 17,
        promotion_margin: float = 0.01,
        legs: Optional[int] = None,     # unused; parity with learning bench
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
        self.seed = int(seed)
        self.promotion_margin = float(promotion_margin)
        self.storage_dir = storage_dir
        # Per-task baseline utilities, captured once run() starts; the
        # objective folds them into a regression penalty so evolution
        # is shaped AWAY from sacrifices instead of merely audited.
        self._baseline_train: Optional[Dict[str, float]] = None

    #: Utility units deducted per point of per-task regression below
    #: the task's baseline score.
    REGRESSION_PRESSURE = 3.0

    # -- task families -------------------------------------------------------- #
    def _profiles(self, seeds: Sequence[int],
                  tag: str) -> List[TaskProfile]:
        return [synthetic_profile(s, name_prefix=tag) for s in seeds]

    def _run_policy(self, config, profiles) -> Dict[str, float]:
        """Score every profile under one policy snapshot config.

        Deterministic by construction (no RNG anywhere in the loop), so
        identical configs reproduce identical per-task utilities.
        """
        registry = default_routing_registry()
        registry.apply(config)
        orchestrator = Orchestrator(RoutingPolicy(registry))
        outcomes = orchestrator.run_many(profiles)
        return {o.task_id: o.score for o in outcomes}

    def _objective(self, config) -> float:
        """Regression-aware training utility; optimizer maximizes it.

        Mean task utility minus a steep penalty for dipping below any
        task's baseline -- 'gains on average' must not be purchasable
        with hidden sacrifices, otherwise the Evaluator would wave
        through policies the regression suite rightly refuses.
        """
        scores = self._run_policy(
            config, self._profiles(self.train_seeds, "train"))
        mean_score = sum(scores.values()) / len(scores)
        penalty = 0.0
        if self._baseline_train:
            for name, base in self._baseline_train.items():
                dip = min(0.0,
                          scores.get(name, -1.0) - base
                          - REGRESSION_TOLERANCE)
                penalty += self.REGRESSION_PRESSURE * dip
        return round(mean_score + penalty, 6)

    # -- main entry --------------------------------------------------------- #
    def run(self) -> BenchmarkReport:
        train_profiles = self._profiles(self.train_seeds, "train")
        holdout_profiles = self._profiles(self.holdout_seeds, "holdout")
        baseline_config = default_routing_registry().snapshot()
        baseline_hash = config_hash(baseline_config)

        baseline_train = self._run_policy(baseline_config, train_profiles)
        baseline_holdout = self._run_policy(baseline_config,
                                            holdout_profiles)
        self._baseline_train = dict(baseline_train)

        optimizer_registry = default_routing_registry()
        evaluator = Evaluator(task=self._objective,
                              margin=self.promotion_margin, repeats=3)
        optimizer = AdaptiveOptimizer(
            optimizer_registry, evaluator,
            population_size=self.population_size, seed=self.seed)

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
                global_best = min((global_best, challenger),
                                  key=lambda c: config_hash(c.config))
            # Warm-start the next cycle from the champion so iteration
            # scores form a monotone best-so-far curve.
            optimizer.registry.apply(global_best.config)
            report.iterations.append(IterationRecord(
                iteration=iteration,
                train_score=round(global_best.score, 6),
                config_hash=config_hash(global_best.config)))

        assert global_best is not None
        final_config = dict(global_best.config)
        final_hash = config_hash(final_config)
        report.final_train_scores = self._run_policy(final_config,
                                                     train_profiles)
        report.final_holdout_scores = self._run_policy(final_config,
                                                       holdout_profiles)

        # Regression suite FIRST: a candidate that damages previously
        # solved tasks is refused promotion regardless of its margin --
        # and the refusal is what the audit trail records.
        report.regression_failures = [
            f"{name}: {baseline_train[name]:.6f} -> "
            f"{report.final_train_scores[name]:.6f}"
            for name, base in baseline_train.items()
            if report.final_train_scores[name]
            < base - REGRESSION_TOLERANCE]

        # Governed promotion through Evaluator gates + audited store.
        evaluation = Evaluator(
            task=self._objective, margin=self.promotion_margin,
            repeats=3).evaluate(final_config, baseline_config)
        if report.regression_failures:
            evaluation = EvaluationResult(
                decision="reject",
                candidate_score=evaluation.candidate_score,
                baseline_score=evaluation.baseline_score,
                margin_required=self.promotion_margin, repeats=3,
                reason=f"regression suite failed "
                       f"({len(report.regression_failures)} tasks)")
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

        # Reproducibility: replay every training task once more under a
        # fresh interpreter-side orchestrator and require equality.
        replay = self._run_policy(final_config, train_profiles)
        report.reproducibility_passed = (
            evaluation.decision != "non_reproducible"
            and replay == report.final_train_scores)

        return report


if __name__ == "__main__":
    # The headline table uses ↑/↓/→ glyphs; Windows consoles default to
    # cp1252, which cannot encode them. Force UTF-8 before printing.
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:               # non-standard stream: leave alone
        pass
    benchmark = OrchestrationBenchmark()
    print(benchmark.run().to_table())