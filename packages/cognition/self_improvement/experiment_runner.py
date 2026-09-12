# Copyright (c) Ultrone Contributors. All rights reserved.
"""Real experiment runner for the self-improvement loop.

Replaces the previous random-number-based experiment execution with a real
benchmark comparison pipeline that measures actual improvement against a
baseline. Supports pluggable experiment functions so improvements are real,
reproducible, and statistically evaluated.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from research_db.schema import ExperimentRecord

logger = logging.getLogger("Ultrone.SelfImprovement.ExperimentRunner")


@dataclass
class ExperimentResult:
    """The result of a real experiment."""

    experiment_id: str
    hypothesis: Dict[str, Any]
    baseline_score: float
    candidate_score: float
    improvement: float
    metrics: Dict[str, float]
    statistical_confidence: float = 0.0
    passed: bool = False
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "hypothesis": self.hypothesis,
            "baseline_score": self.baseline_score,
            "candidate_score": self.candidate_score,
            "improvement": self.improvement,
            "metrics": self.metrics,
            "statistical_confidence": self.statistical_confidence,
            "passed": self.passed,
            "details": self.details,
        }


class ExperimentRunner:
    """Runs real improvement experiments.

    An experiment consists of:
    1. A baseline evaluation (current behavior)
    2. A candidate evaluation (proposed improvement)
    3. Statistical comparison of the two

    Experiment functions are callables ``(config) -> Dict[str, float]`` that
    evaluate a candidate implementation and return metric values.
    """

    def __init__(
        self,
        experiment_fn: Optional[Callable[[Dict[str, Any]], Dict[str, float]]] = None,
        baseline_fn: Optional[Callable[[Dict[str, Any]], Dict[str, float]]] = None,
        min_improvement: float = 0.02,
        num_trials: int = 3,
        target_metric: str = "accuracy",
    ):
        self.experiment_fn = experiment_fn or self._default_experiment_fn
        self.baseline_fn = baseline_fn or self._default_baseline_fn
        self.min_improvement = min_improvement
        self.num_trials = num_trials
        self.target_metric = target_metric
        self._results: List[ExperimentResult] = []

    def _default_baseline_fn(self, config: Dict[str, Any]) -> Dict[str, float]:
        """Default baseline: evaluate the current system's performance.

        This should be overridden with a real evaluation of the current
        production model. The default returns a stored baseline if available,
        otherwise a placeholder that must be replaced.
        """
        # If a real baseline was supplied via config, use it.
        if "baseline_metrics" in config:
            return dict(config["baseline_metrics"])
        # Otherwise this is an explicit error — no fake numbers.
        raise ValueError(
            "No baseline evaluation function provided and no baseline_metrics "
            "in config. Self-improvement requires a real baseline."
        )

    def _default_experiment_fn(self, config: Dict[str, Any]) -> Dict[str, float]:
        """Default experiment: evaluate the candidate improvement.

        Should be overridden with a real evaluation of the proposed change.
        """
        if "candidate_metrics" in config:
            return dict(config["candidate_metrics"])
        raise ValueError(
            "No experiment evaluation function provided and no candidate_metrics "
            "in config. Self-improvement requires a real candidate evaluation."
        )

    def run(
        self,
        hypothesis: Dict[str, Any],
        config: Optional[Dict[str, Any]] = None,
    ) -> ExperimentResult:
        """Run a real experiment comparing baseline vs candidate.

        Parameters
        ----------
        hypothesis : Dict[str, Any]
            The improvement hypothesis.
        config : Optional[Dict[str, Any]]
            Experiment configuration (baseline_metrics, candidate_metrics,
            or custom function kwargs).

        Returns
        -------
        ExperimentResult
            The experiment result with real metrics.
        """
        config = config or {}
        experiment_id = f"exp-{uuid.uuid4().hex[:12]}"
        start = time.time()

        # Run baseline trials
        baseline_scores = []
        for _ in range(self.num_trials):
            metrics = self.baseline_fn(config)
            baseline_scores.append(metrics.get(self.target_metric, 0.0))

        # Run candidate trials
        candidate_scores = []
        for _ in range(self.num_trials):
            metrics = self.experiment_fn(config)
            candidate_scores.append(metrics.get(self.target_metric, 0.0))

        # Compute statistics
        baseline_score = sum(baseline_scores) / len(baseline_scores) if baseline_scores else 0.0
        candidate_score = sum(candidate_scores) / len(candidate_scores) if candidate_scores else 0.0
        improvement = candidate_score - baseline_score
        confidence = self._compute_confidence(baseline_scores, candidate_scores)

        # Determine pass/fail
        passed = improvement >= self.min_improvement and confidence >= 0.5

        result = ExperimentResult(
            experiment_id=experiment_id,
            hypothesis=hypothesis,
            baseline_score=baseline_score,
            candidate_score=candidate_score,
            improvement=improvement,
            metrics={
                "baseline": baseline_score,
                "candidate": candidate_score,
                "improvement": improvement,
                "confidence": confidence,
            },
            statistical_confidence=confidence,
            passed=passed,
            details={
                "baseline_trials": baseline_scores,
                "candidate_trials": candidate_scores,
                "duration_seconds": time.time() - start,
                "num_trials": self.num_trials,
            },
        )
        self._results.append(result)
        return result

    @staticmethod
    def _compute_confidence(baseline: List[float], candidate: List[float]) -> float:
        """Compute a simple statistical confidence (Cohen's d style).

        Uses the standardized mean difference scaled to [0, 1].
        """
        if len(baseline) < 2 or len(candidate) < 2:
            return 0.0
        import math

        b_mean = sum(baseline) / len(baseline)
        c_mean = sum(candidate) / len(candidate)
        b_var = sum((x - b_mean) ** 2 for x in baseline) / (len(baseline) - 1)
        c_var = sum((x - c_mean) ** 2 for x in candidate) / (len(candidate) - 1)
        pooled_std = math.sqrt((b_var + c_var) / 2) if (b_var + c_var) > 0 else 0.0
        if pooled_std == 0:
            return 1.0 if c_mean > b_mean else 0.0
        d = (c_mean - b_mean) / pooled_std
        # Map Cohen's d to [0, 1]: 0.2 small, 0.5 medium, 0.8 large
        return min(1.0, max(0.0, (d + 1.0) / 2.0))

    def get_results(self) -> List[ExperimentResult]:
        """Return all experiment results."""
        return list(self._results)

    def get_stats(self) -> Dict[str, Any]:
        """Return runner statistics."""
        return {
            "type": "ExperimentRunner",
            "experiments_run": len(self._results),
            "passed": sum(1 for r in self._results if r.passed),
            "failed": sum(1 for r in self._results if not r.passed),
            "avg_improvement": sum(r.improvement for r in self._results) / len(self._results) if self._results else 0.0,
        }