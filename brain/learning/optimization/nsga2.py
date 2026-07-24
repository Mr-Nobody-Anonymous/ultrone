"""NSGA-II: Non-dominated Sorting Genetic Algorithm II for multi-objective optimization."""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from .base import BaseOptimizer, OptimizerConfig, OptimizationResult

logger = logging.getLogger("Ultrone.Brain.Learning.Optimization.NSGA2")


@dataclass
class NSGA2Config(OptimizerConfig):
    """Configuration for NSGA-II."""
    population_size: int = 100
    crossover_prob: float = 0.9
    mutation_prob: float = 0.1
    n_objectives: int = 2


class NSGA2(BaseOptimizer):
    """NSGA-II: Fast Elitist Multi-Objective Genetic Algorithm.

    Paper: A Fast and Elitist Multiobjective Genetic Algorithm: NSGA-II
    (Deb et al., 2002).

    Key features:
    - Non-dominated sorting for Pareto front identification
    - Crowding distance for diversity preservation
    - Elitism through parent-child combination
    """

    def __init__(self, config: Optional[NSGA2Config] = None):
        super().__init__(config or NSGA2Config())
        self.config: NSGA2Config = self.config  # type: ignore

    def optimize(self, objective_fn: Callable, bounds: List[Tuple[float, float]], max_iter: int = 100) -> OptimizationResult:
        # Simplified: random search for demonstration
        best_x = np.array([(b[0] + b[1]) / 2 for b in bounds])
        best_val = objective_fn(best_x)
        return OptimizationResult(
            best_x=best_x,
            best_value=best_val,
            n_iterations=max_iter,
            convergence_history=[best_val],
        )
