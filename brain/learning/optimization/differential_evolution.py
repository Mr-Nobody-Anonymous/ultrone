# Copyright (c) Ultrone Contributors. All rights reserved.
"""Differential Evolution optimizer."""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

from .base import BaseOptimizer, OptimizerConfig, OptimizationResult

logger = logging.getLogger("Ultrone.Brain.Learning.Optimization.DE")


@dataclass
class DEConfig(OptimizerConfig):
    """Configuration for Differential Evolution."""
    population_size: int = 50
    mutation_factor: float = 0.8
    crossover_rate: float = 0.9
    strategy: str = "best1bin"


class DifferentialEvolution(BaseOptimizer):
    """Differential Evolution optimizer."""

    def __init__(self, config: Optional[DEConfig] = None):
        super().__init__(config or DEConfig())

    def optimize(self, objective_fn, bounds):
        dim = len(bounds)
        n = self._config.population_size
        lb = np.array([b[0] for b in bounds])
        ub = np.array([b[1] for b in bounds])
        pop = np.random.uniform(lb, ub, (n, dim))
        fitness = np.array([objective_fn(p) for p in pop])
        self._n_evaluations += n
        best_idx = np.argmin(fitness)

        for iteration in range(self._config.max_iterations):
            for i in range(n):
                idxs = [idx for idx in range(n) if idx != i]
                a, b, c = pop[np.random.choice(idxs, 3, replace=False)]
                mutant = np.clip(a + self._config.mutation_factor * (b - c), lb, ub)
                cross_mask = np.random.random(dim) < self._config.crossover_rate
                trial = np.where(cross_mask, mutant, pop[i])
                trial_fitness = objective_fn(trial)
                self._n_evaluations += 1
                if trial_fitness < fitness[i]:
                    pop[i] = trial
                    fitness[i] = trial_fitness
            best_idx = np.argmin(fitness)
            self._history.append(fitness[best_idx])

        return OptimizationResult(
            best_params=pop[best_idx], best_value=fitness[best_idx],
            n_iterations=self._config.max_iterations,
            n_evaluations=self._n_evaluations,
            convergence_history=self._history,
        )