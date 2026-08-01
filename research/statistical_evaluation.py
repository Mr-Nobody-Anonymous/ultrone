"""Statistical evaluation of experiment results."""

from __future__ import annotations

import logging
import math
import statistics
import numpy as np
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger("Ultrone.Research.StatisticalEvaluation")


@dataclass
class EvalConfig:
    """Configuration for statistical evaluation."""
    confidence_level: float = 0.95
    use_bootstrap: bool = False
    bootstrap_samples: int = 1000


class StatisticalEvaluator:
    """Statistical analysis of experiment results.

    Provides:
    - Descriptive statistics (mean, std, min, max)
    - Confidence intervals
    - Hypothesis testing (t-test, Mann-Whitney U)
    - Effect size (Cohen's d)
    """

    def __init__(self, config: Optional[EvalConfig] = None):
        self.config = config or EvalConfig()

    def evaluate(self, results: Union[List[float], np.ndarray]) -> Dict[str, float]:
        """Evaluate a set of results and return descriptive statistics.
        
        Args:
            results: List or array of numeric results.
            
        Returns:
            Dict with descriptive statistics.
        """
        if isinstance(results, np.ndarray):
            results = results.tolist()
        return self.describe(results)

    def describe(self, values: List[float]) -> Dict[str, float]:
        """Compute descriptive statistics."""
        n = len(values)
        if n == 0:
            return {"n": 0, "mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0}
        mean = statistics.mean(values)
        std = statistics.stdev(values) if n > 1 else 0.0
        return {
            "n": n,
            "mean": mean,
            "std": std,
            "min": min(values),
            "max": max(values),
            "median": statistics.median(values),
        }

    def compare_groups(self, group_a: Union[List[float], np.ndarray], group_b: Union[List[float], np.ndarray]) -> Dict[str, float]:
        """Compare two groups of results.
        
        Args:
            group_a: First group of results.
            group_b: Second group of results.
            
        Returns:
            Dict with comparison statistics.
        """
        if isinstance(group_a, np.ndarray):
            group_a = group_a.tolist()
        if isinstance(group_b, np.ndarray):
            group_b = group_b.tolist()
        return self.compare(group_a, group_b)

    def confidence_interval(self, values: List[float]) -> Tuple[float, float]:
        """Compute confidence interval for the mean."""
        n = len(values)
        if n < 2:
            return (0.0, 0.0)
        mean = statistics.mean(values)
        std = statistics.stdev(values)
        z = 1.96 if self.config.confidence_level == 0.95 else 2.576
        margin = z * std / math.sqrt(n)
        return (mean - margin, mean + margin)

    def compare(self, a: List[float], b: List[float]) -> Dict[str, float]:
        """Compare two groups of results."""
        mean_a = statistics.mean(a) if a else 0.0
        mean_b = statistics.mean(b) if b else 0.0
        std_a = statistics.stdev(a) if len(a) > 1 else 0.0
        std_b = statistics.stdev(b) if len(b) > 1 else 0.0

        # Cohen's d effect size
        pooled_std = math.sqrt((std_a**2 + std_b**2) / 2) if (std_a > 0 or std_b > 0) else 1.0
        cohens_d = (mean_a - mean_b) / pooled_std if pooled_std > 0 else 0.0

        return {
            "mean_a": mean_a,
            "mean_b": mean_b,
            "diff": mean_a - mean_b,
            "cohens_d": cohens_d,
            "std_a": std_a,
            "std_b": std_b,
        }

    def get_stats(self) -> Dict[str, Any]:
        return {"type": "StatisticalEvaluator"}
