# Copyright (c) Ultrone Contributors. All rights reserved.
"""Bayesian Optimization with Gaussian Processes."""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

from .base import BaseOptimizer, OptimizerConfig, OptimizationResult

logger = logging.getLogger("Ultrone.Brain.Learning.Optimization.BayesOpt")


@dataclass
class BayesOptConfig(OptimizerConfig):
    """Configuration for Bayesian Optimization."""
    n_initial_points: int = 10
    acquisition: str = "ucb"
    kappa: float = 2.5


class BayesianOptimization(BaseOptimizer):
    """Bayesian Optimization using Gaussian Process surrogate."""

    def __init__(self, config: Optional[BayesOptConfig] = None):
        super().__init__(config or BayesOptConfig())

    def optimize(self, objective_fn, bounds):
        dim = len(bounds)
        X = np.random.uniform([b[0] for b in bounds], [b[1] for b in bounds],
                              (self._config.n_initial_points, dim))
        y = np.array([objective_fn(x) for x in X])
        self._n_evaluations += len(X)
        best_idx = np.argmin(y)
        self._history.append(y[best_idx])

        for iteration in range(self._config.max_iterations - self._config.n_initial_points):
            # Simple random candidate search as placeholder for GP-based acquisition
            candidates = np.random.uniform([b[0] for b in bounds], [b[1] for b in bounds], (100, dim))
            # UCB-like: pick candidate farthest from observed points
            dists = np.array([[np.linalg.norm(c - x) for x in X] for c in candidates])
            best_candidate = candidates[dists.min(axis=1).argmax()]
            val = objective_fn(best_candidate)
            self._n_evaluations += 1
            X = np.vstack([X, best_candidate])
            y = np.append(y, val)
            best_idx = np.argmin(y)
            self._history.append(y[best_idx])

        return OptimizationResult(
            best_params=X[best_idx], best_value=y[best_idx],
            n_iterations=self._config.max_iterations,
            n_evaluations=self._n_evaluations,
            convergence_history=self._history,
        )