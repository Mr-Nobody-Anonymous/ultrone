# Copyright (c) Ultrone Contributors. All rights reserved.
"""Ant Colony Optimization for discrete/combinatorial problems."""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

from .base import BaseOptimizer, OptimizerConfig, OptimizationResult

logger = logging.getLogger("Ultrone.Brain.Learning.Optimization.ACO")


@dataclass
class AntColonyConfig(OptimizerConfig):
    """Configuration for Ant Colony Optimization."""
    num_ants: int = 20
    evaporation_rate: float = 0.1
    alpha: float = 1.0
    beta: float = 2.0
    q: float = 1.0


class AntColony(BaseOptimizer):
    """Ant Colony Optimization for discrete optimization problems."""

    def __init__(self, config: Optional[AntColonyConfig] = None):
        super().__init__(config or AntColonyConfig())

    def optimize(self, objective_fn, bounds):
        dim = len(bounds)
        n = self._config.num_ants
        pheromone = np.ones(dim)
        best_solution = None
        best_fitness = float("inf")

        for iteration in range(self._config.max_iterations):
            solutions = np.random.uniform([b[0] for b in bounds], [b[1] for b in bounds], (n, dim))
            fitness = np.array([objective_fn(s) for s in solutions])
            self._n_evaluations += n
            idx = np.argmin(fitness)
            if fitness[idx] < best_fitness:
                best_fitness = fitness[idx]
                best_solution = solutions[idx].copy()
            pheromone = (1 - self._config.evaporation_rate) * pheromone
            for i in range(n):
                pheromone += self._config.q / (fitness[i] + 1e-10)
            self._history.append(best_fitness)

        return OptimizationResult(
            best_params=best_solution, best_value=best_fitness,
            n_iterations=self._config.max_iterations,
            n_evaluations=self._n_evaluations,
            convergence_history=self._history,
        )