"""Cross-Entropy Method for optimization."""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from .base import BaseOptimizer, OptimizerConfig, OptimizationResult

logger = logging.getLogger("Ultrone.Brain.Learning.Optimization.CEM")


@dataclass
class CEMConfig(OptimizerConfig):
    """Configuration for Cross-Entropy Method."""
    population_size: int = 100
    elite_frac: float = 0.2
    smoothing: float = 0.7


class CrossEntropyMethod(BaseOptimizer):
    """Cross-Entropy Method for stochastic optimization.

    Maintains a probability distribution over the search space,
    updating it based on elite samples to focus on promising regions.
    """

    def __init__(self, config: Optional[CEMConfig] = None):
        super().__init__(config or CEMConfig())
        self.config: CEMConfig = self.config  # type: ignore

    def optimize(self, objective_fn: Callable, bounds: List[Tuple[float, float]], max_iter: int = 100) -> OptimizationResult:
        dim = len(bounds)
        mean = np.array([(b[0] + b[1]) / 2 for b in bounds])
        std = np.array([(b[1] - b[0]) / 4 for b in bounds])

        for i in range(max_iter):
            samples = np.random.randn(self.config.population_size, dim) * std + mean
            samples = np.clip(samples, [b[0] for b in bounds], [b[1] for b in bounds])
            values = np.array([objective_fn(s) for s in samples])
            n_elite = int(self.config.population_size * self.config.elite_frac)
            elite_idx = np.argsort(values)[:n_elite]
            elite_samples = samples[elite_idx]
            new_mean = np.mean(elite_samples, axis=0)
            new_std = np.std(elite_samples, axis=0)
            mean = self.config.smoothing * mean + (1 - self.config.smoothing) * new_mean
            std = self.config.smoothing * std + (1 - self.config.smoothing) * new_std

        return OptimizationResult(
            best_x=mean,
            best_value=float(objective_fn(mean)),
            n_iterations=max_iter,
        )
