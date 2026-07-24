# Copyright (c) Ultrone Contributors. All rights reserved.
"""CMA-ES (Covariance Matrix Adaptation Evolution Strategy)."""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

from .base import BaseOptimizer, OptimizerConfig, OptimizationResult

logger = logging.getLogger("Ultrone.Brain.Learning.Optimization.CMAES")


@dataclass
class CMAESConfig(OptimizerConfig):
    """Configuration for CMA-ES."""
    population_size: int = 20
    sigma: float = 0.5


class CMAES(BaseOptimizer):
    """CMA-ES implementation for continuous black-box optimization."""

    def __init__(self, config: Optional[CMAESConfig] = None):
        super().__init__(config or CMAESConfig())

    def optimize(self, objective_fn, bounds):
        dim = len(bounds)
        mean = np.array([(b[0] + b[1]) / 2 for b in bounds])
        sigma = self._config.sigma
        n = self._config.population_size
        cov = np.eye(dim) * sigma ** 2

        for iteration in range(self._config.max_iterations):
            samples = np.random.multivariate_normal(mean, cov, n)
            fitness = np.array([objective_fn(s) for s in samples])
            self._n_evaluations += n
            idx = np.argsort(fitness)
            mean = samples[idx[:n // 2]].mean(axis=0)
            self._history.append(fitness.min())

        return OptimizationResult(
            best_params=mean, best_value=fitness.min(),
            n_iterations=self._config.max_iterations,
            n_evaluations=self._n_evaluations,
            convergence_history=self._history,
        )