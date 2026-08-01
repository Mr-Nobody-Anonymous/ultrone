# Copyright (c) Ultrone Contributors. All rights reserved.
"""Particle Swarm Optimization (PSO)."""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

from .base import BaseOptimizer, OptimizerConfig, OptimizationResult

logger = logging.getLogger("Ultrone.Brain.Learning.Optimization.PSO")


@dataclass
class PSOConfig(OptimizerConfig):
    """Configuration for PSO."""
    population_size: int = 30
    inertia: float = 0.7
    cognitive_coef: float = 1.5
    social_coef: float = 1.5
    velocity_clip: float = 0.5


class ParticleSwarm(BaseOptimizer):
    """Particle Swarm Optimization implementation."""

    def __init__(self, config: Optional[PSOConfig] = None):
        super().__init__(config or PSOConfig())
        self._config: PSOConfig = self.config  # type: ignore

    def optimize(
        self,
        objective_fn: Callable[[np.ndarray], float],
        bounds: List[Tuple[float, float]],
        max_iter: Optional[int] = None,
    ) -> OptimizationResult:
        dim = len(bounds)
        n = self._config.population_size
        num_iterations = max_iter if max_iter is not None else self._config.max_iterations
        lb = np.array([b[0] for b in bounds])
        ub = np.array([b[1] for b in bounds])

        positions = np.random.uniform(lb, ub, (n, dim))
        velocities = np.random.uniform(-0.1, 0.1, (n, dim))
        personal_best = positions.copy()
        personal_best_fitness = np.array([objective_fn(p) for p in positions])
        self._n_evaluations += n
        global_best_idx = np.argmin(personal_best_fitness)
        global_best = personal_best[global_best_idx].copy()
        global_best_fitness = personal_best_fitness[global_best_idx]

        w = self._config.inertia
        c1 = self._config.cognitive_coef
        c2 = self._config.social_coef

        for iteration in range(num_iterations):
            r1, r2 = np.random.random((2, n, dim))
            velocities = (w * velocities + c1 * r1 * (personal_best - positions) +
                          c2 * r2 * (global_best - positions))
            velocities = np.clip(velocities, -self._config.velocity_clip, self._config.velocity_clip)
            positions = np.clip(positions + velocities, lb, ub)

            fitness = np.array([objective_fn(p) for p in positions])
            self._n_evaluations += n

            improved = fitness < personal_best_fitness
            personal_best[improved] = positions[improved]
            personal_best_fitness[improved] = fitness[improved]

            current_best_idx = np.argmin(fitness)
            if fitness[current_best_idx] < global_best_fitness:
                global_best = positions[current_best_idx].copy()
                global_best_fitness = fitness[current_best_idx]

            self._history.append(global_best_fitness)

        return OptimizationResult(
            best_params=global_best,
            best_value=global_best_fitness,
            n_iterations=num_iterations,
            n_evaluations=self._n_evaluations,
            convergence_history=self._history,
        )
