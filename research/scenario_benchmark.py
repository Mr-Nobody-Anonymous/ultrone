"""Scenario-based benchmarking for agents and algorithms."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("Ultrone.Research.Benchmark")


@dataclass
class BenchmarkConfig:
    """Configuration for scenario benchmarking."""
    num_runs: int = 10
    timeout_seconds: float = 300.0
    metrics: List[str] = field(default_factory=lambda: ["reward", "success", "steps"])


@dataclass
class BenchmarkResult:
    """Result of a benchmark run."""
    scenario_name: str
    agent_name: str
    metrics: Dict[str, float]
    duration_ms: float
    success: bool = True


class ScenarioBenchmark:
    """Benchmarking framework for comparing agents and algorithms.

    Runs multiple trials of different scenarios and collects
    statistical performance metrics for comparison.
    """

    def __init__(self, config: Optional[BenchmarkConfig] = None):
        self.config = config or BenchmarkConfig()
        self._results: List[BenchmarkResult] = []

    def run(
        self,
        scenario_name: str,
        agent_name: str,
        agent_fn: Callable,
        env_fn: Callable,
    ) -> BenchmarkResult:
        """Run a benchmark trial."""
        start = time.time()
        metrics = {}
        success = True
        try:
            env = env_fn()
            for _ in range(self.config.num_runs):
                result = agent_fn(env)
                for m in self.config.metrics:
                    if m in result:
                        metrics[m] = metrics.get(m, 0.0) + result[m]
            # Average
            for k in metrics:
                metrics[k] /= self.config.num_runs
        except Exception as e:
            logger.error("Benchmark failed: %s", e)
            success = False

        duration_ms = (time.time() - start) * 1000
        result = BenchmarkResult(
            scenario_name=scenario_name,
            agent_name=agent_name,
            metrics=metrics,
            duration_ms=duration_ms,
            success=success,
        )
        self._results.append(result)
        return result

    def get_stats(self) -> Dict[str, Any]:
        return {"type": "ScenarioBenchmark", "results": len(self._results)}
