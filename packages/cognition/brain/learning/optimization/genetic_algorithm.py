# Copyright (c) Ultrone Contributors. All rights reserved.
"""Genetic Algorithm (GA) optimizer for population-based evolutionary optimization."""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

from .base import BaseOptimizer, OptimizerConfig, OptimizationResult

logger = logging.getLogger("Ultrone.Brain.Learning.Optimization.GA")


@dataclass
class GAConfig(OptimizerConfig):
    """Configuration for Genetic Algorithm."""
    population_size: int = 100
    mutation_rate: float = 0.1
    crossover_rate: float = 0.8
    elitism_count: int = 2
    tournament_size: int = 3


class GeneticAlgorithm(BaseOptimizer):
    """Genetic Algorithm optimizer using tournament selection,
    uniform crossover, and Gaussian mutation."""

    def __init__(self, config: Optional[GAConfig] = None):
        super().__init__(config or GAConfig())
        self._config: GAConfig = self.config  # type: ignore

    def optimize(
        self,
        objective_fn: Callable[[np.ndarray], float],
        bounds: List[Tuple[float, float]],
        max_iter: Optional[int] = None,
    ) -> OptimizationResult:
        dim = len(bounds)
        num_iterations = max_iter if max_iter is not None else self._config.max_iterations
        pop = np.random.uniform(
            [b[0] for b in bounds], [b[1] for b in bounds],
            (self._config.population_size, dim),
        )
        best_solution = None
        best_fitness = float("inf")

        for iteration in range(num_iterations):
            fitness = np.array([objective_fn(ind) for ind in pop])
            self._n_evaluations += len(pop)

            idx = np.argmin(fitness)
            if fitness[idx] < best_fitness:
                best_fitness = fitness[idx]
                best_solution = pop[idx].copy()

            self._history.append(best_fitness)

            # Selection (tournament)
            new_pop = []
            for _ in range(self._config.population_size):
                t_idx = np.random.choice(len(pop), self._config.tournament_size, replace=False)
                winner = t_idx[np.argmin(fitness[t_idx])]
                new_pop.append(pop[winner])
            new_pop = np.array(new_pop)

            # Crossover
            for i in range(0, len(new_pop) - 1, 2):
                if np.random.random() < self._config.crossover_rate:
                    mask = np.random.random(dim) < 0.5
                    temp = new_pop[i].copy()
                    new_pop[i][mask] = new_pop[i + 1][mask]
                    new_pop[i + 1][mask] = temp[mask]

            # Mutation
            for i in range(self._config.elitism_count, len(new_pop)):
                mask = np.random.random(dim) < self._config.mutation_rate
                new_pop[i][mask] += np.random.normal(0, 0.1, mask.sum())
                # Clip to bounds
                for d in range(dim):
                    new_pop[i, d] = np.clip(new_pop[i, d], bounds[d][0], bounds[d][1])

            pop = new_pop

        return OptimizationResult(
            best_params=best_solution,
            best_value=best_fitness,
            n_iterations=num_iterations,
            n_evaluations=self._n_evaluations,
            convergence_history=self._history,
        )
