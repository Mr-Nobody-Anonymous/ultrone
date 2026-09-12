# Copyright (c) Ultrone Contributors. All rights reserved.
"""Capability benchmark: does the self-training loop measurably improve?

Phase-4 objective restated exactly -- whether the loop-produced model
is measurably better than the model it started with. Unlike the
orchestration/patrol benchmarks (which evolve a configuration), this
one tracks a *model* through the self-training substrate and reports
it along the full capability grid::

      base (starter)
        |  loop cycles (GENERATE..PROMOTE)
        v
    final (production)  ---> compare_capabilities(base, final)
                               ├─ overall improvement
                               ├─ no critical regression
                               ├─ holdout improvement
                               └─ reproducibility

Runs deterministically on the statistical capability learner today; the
same harness answers the question unchanged when a real neural/hosted
backend is substituted behind the executor seam. Standalone run:

    python -m benchmarks.self_training_benchmark
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from self_improvement.self_training.controller import (
    SelfTrainingController,
)
from self_improvement.self_training.regression import (
    RegressionReport,
    RegressionSuite,
    build_families,
)
from self_improvement.self_training.trainer import LearnedWeights


def _default_starter() -> LearnedWeights:
    return LearnedWeights(values={
        "reasoning": 0.62, "coding": 0.66, "retrieval": 0.56,
        "tool_use": 0.68})


@dataclass
class CycleVerdict:
    """One loop cycle's observable outcome (training + promotion)."""

    cycle: int
    trained: bool
    promoted: bool
    decision: str = "skip"
    mean_utility: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class SelfTrainingReport:
    """Baseline-vs-final capability comparison across the loop."""

    baseline_hash: str
    final_hash: Optional[str]
    cycles: List[CycleVerdict] = field(default_factory=list)
    comparison: Optional[Dict[str, Any]] = None
    regression_passed: bool = False
    promoted_any: bool = False
    plateau_refused: bool = False

    @property
    def measurably_better(self) -> bool:
        return bool(self.comparison
                    and self.comparison.get("measurably_better"))

    def to_table(self) -> str:
        verdict = "MEASURABLY BETTER" if self.measurably_better \
            else "not measurably better"
        reg_label = "PASS" if self.regression_passed else "FAIL"
        lines = [
            f"{'Capability benchmark':<24}{verdict}",
            f"{'Baseline model':<24}{self.baseline_hash}",
            f"{'Final model':<24}{self.final_hash}",
            f"{'Regression suite':<24}{reg_label}",
            f"{'Promoted during loop':<26}"
            f"{'yes' if self.promoted_any else 'no'}",
            f"{'Plateau honestly refused':<26}"
            f"{'yes' if self.plateau_refused else 'no'}",
            "",
            f"{'Dimension':<22}{'base':>10}{'final':>10}{'delta':>10}",
        ]
        if self.comparison:
            base = self.comparison.get("baseline", {})
            cand = self.comparison.get("candidate", {})
            deltas = self.comparison.get("deltas", {})
            for name, delta in deltas.items():
                lines.append(
                    f"{name:<22}{base.get(name, 0.0):>10.4f}"
                    f"{cand.get(name, 0.0):>10.4f}{delta:>10.4f}")
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "baseline_hash": self.baseline_hash,
            "final_hash": self.final_hash,
            "measurably_better": self.measurably_better,
            "regression_passed": self.regression_passed,
            "promoted_any": self.promoted_any,
            "plateau_refused": self.plateau_refused,
            "cycles": [c.to_dict() for c in self.cycles],
            "comparison": self.comparison,
        }

    def save_json(self, path) -> None:
        import json
        Path(path).write_text(
            json.dumps(self.to_dict(), sort_keys=True, indent=2),
            encoding="utf-8")


class SelfTrainingBenchmark:
    """Run the self-training loop and report capability transfer.

    One controller, a default starter, and a fixed gated family set --
    deterministic by construction (identical starter, policy, seeds), so
    re-runs reproduce the same final hash and verdict.
    """

    def __init__(self, *, workdir: Optional[str] = None,
                 starter: Optional[LearnedWeights] = None,
                 cycles: int = 4, batch: int = 10,
                 good_floor: float = 0.5, margin: float = 0.01,
                 desired_ceiling: float = 0.85,
                 family_each: int = 5) -> None:
        self.starter = starter or _default_starter()
        self.cycles = int(cycles)
        self.batch = int(batch)
        self.good_floor = float(good_floor)
        self.margin = float(margin)
        self.desired_ceiling = float(desired_ceiling)
        self.family_each = int(family_each)
        if workdir:
            self._workdir = Path(workdir)
            self._workdir.mkdir(parents=True, exist_ok=True)
        else:
            import tempfile
            self._workdir = Path(tempfile.mkdtemp(prefix="stbench-"))

    def run(self) -> SelfTrainingReport:
        controller = SelfTrainingController(
            workdir=str(self._workdir),
            batch=self.batch, starter=self.starter,
            good_floor=self.good_floor, margin=self.margin,
            desired_ceiling=self.desired_ceiling)
        families = build_families(n_each=self.family_each)

        verdicts: List[CycleVerdict] = []
        promoted_any = False
        refused_after_prominence = False
        for cycle in range(1, self.cycles + 1):
            cycle_report = controller.run_cycle(cycle)
            trained = cycle_report.candidate is not None
            decision = (cycle_report.promotion.promoted
                        if cycle_report.promotion else False)
            verdicts.append(CycleVerdict(
                cycle=cycle, trained=trained, promoted=decision,
                decision=(cycle_report.promotion.decision
                          if cycle_report.promotion else "skip"),
                mean_utility=round(cycle_report.mean_utility, 6)))
            if decision:
                promoted_any = True
            elif trained:
                # A cycle that trained yet did NOT promote is the honest
                # plateau refusal -- no manufactured improvement.
                refused_after_prominence = True

        production = controller.checkpoints.production_weights()
        final_hash = production.model_hash if production else None

        regression: Optional[RegressionReport] = None
        comparison = None
        if production is not None:
            regression = RegressionSuite(families=families).run(
                production, self.starter)
            from self_improvement.self_training.evaluation import (
                compare_capabilities,
            )
            cmp = compare_capabilities(
                self.starter, production, families,
                regression=regression, reproducible=True)
            comparison = cmp.to_dict()
            comparison["candidate_hash"] = final_hash

        return SelfTrainingReport(
            baseline_hash=self.starter.model_hash,
            final_hash=final_hash,
            cycles=verdicts,
            comparison=comparison,
            regression_passed=regression.passed if regression else False,
            promoted_any=promoted_any,
            plateau_refused=refused_after_prominence)


if __name__ == "__main__":
    # Headline table uses ↑/↓/→ glyphs; Windows consoles default to
    # cp1252, which cannot encode them. Force UTF-8 before printing.
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:               # pragma: no cover
        pass
    bench = SelfTrainingBenchmark()
    report = bench.run()
    print(report.to_table())