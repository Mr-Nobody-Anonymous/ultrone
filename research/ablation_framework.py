"""Ablation testing framework for algorithm analysis."""

from __future__ import annotations

import logging
import copy
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("Ultrone.Research.Ablation")


@dataclass
class AblationConfig:
    """Configuration for ablation studies."""
    baseline_config: Dict[str, Any] = field(default_factory=dict)
    ablation_keys: List[str] = field(default_factory=list)
    num_runs: int = 5


@dataclass
class AblationResult:
    """Result of a single ablation trial."""
    config_name: str
    config: Dict[str, Any]
    metrics: Dict[str, float]
    delta_from_baseline: Dict[str, float]


class AblationFramework:
    """Ablation testing framework for analyzing component contributions.

    Systematically removes or modifies components to measure
    their impact on overall performance. Provides delta analysis
    and statistical comparison against baselines.
    """

    def __init__(self, config: Optional[AblationConfig] = None):
        self.config = config or AblationConfig()
        self._baseline: Optional[Dict[str, float]] = None
        self._results: List[AblationResult] = []

    def set_baseline(self, metrics: Dict[str, float]) -> None:
        """Set the baseline performance metrics."""
        self._baseline = metrics

    def run_ablation(
        self,
        config_name: str,
        modified_config: Dict[str, Any],
        run_fn: Callable[[Dict[str, Any]], Dict[str, float]],
    ) -> AblationResult:
        """Run a single ablation experiment."""
        metrics = run_fn(modified_config)
        baseline = self._baseline or metrics
        delta = {k: metrics.get(k, 0.0) - baseline.get(k, 0.0) for k in set(metrics) | set(baseline)}
        result = AblationResult(
            config_name=config_name,
            config=modified_config,
            metrics=metrics,
            delta_from_baseline=delta,
        )
        self._results.append(result)
        return result

    def get_stats(self) -> Dict[str, Any]:
        return {"type": "AblationFramework", "ablation_runs": len(self._results)}
