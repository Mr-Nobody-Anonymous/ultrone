# Copyright (c) Ultrone Contributors. All rights reserved.
"""Simulated Annealing optimizer."""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

from .base import BaseOptimizer, OptimizerConfig, OptimizationResult

logger = logging.getLogger("Ultrone.Brain.Learning.Optimization.SA")


@dataclass
class SAConfig(OptimizerConfig):
    """Configuration for Simulated Annealing."""
    initial_temperature: float = 100.0
    cooling_rate: float = 0.95
    min_temperature: float = 1e-6
    steps_per_temp: int = 10


class SimulatedAnnealing(BaseOptimizer):
    """Simulated Annealing optimizer."""

    def __init__(self, config: Optional[SAConfig] = None):
        super().__init__(config or SAConfig())

    def optimize(self, objective_fn, bounds):
        dim = len(bounds)
        current = np.array([np.random.uniform(b[0], b[1]) for b in bounds])
        current_fitness = objective_fn(current)
        self._n_evaluations += 1
        best = current.copy()
        best_fitness = current_fitness
        temp = self._config.initial_temperature

        while temp > self._config.min_temperature:
            for _ in range(self._config.steps_per_temp):
                candidate = current + np.random.normal(0, 0.1, dim)
                candidate = np.clip(candidate, [b[0] for b in bounds], [b[1] for b in bounds])
                candidate_fitness = objective_fn(candidate)
                self._n_evaluations += 1
                delta = candidate_fitness - current_fitness
                if delta < 0 or np.random.random() < np.exp(-delta / temp):
                    current = candidate
                    current_fitness = candidate_fitness
                    if current_fitness < best_fitness:
                        best = current.copy()
                        best_fitness = current_fitness
            self._history.append(best_fitness)
            temp *= self._config.cooling_rate

        return OptimizationResult(
            best_params=best, best_value=best_fitness,
            n_iterations=self._config.max_iterations,
            n_evaluations=self._n_evaluations,
            convergence_history=self._history,
        )