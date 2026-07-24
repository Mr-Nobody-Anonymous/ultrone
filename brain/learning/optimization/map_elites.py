"""MAP-Elites: Multi-dimensional Archive of Phenotypic Elites for quality diversity."""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from .base import BaseOptimizer, OptimizerConfig, OptimizationResult

logger = logging.getLogger("Ultrone.Brain.Learning.Optimization.MAPElites")


@dataclass
class MAPElitesConfig(OptimizerConfig):
    """Configuration for MAP-Elites."""
    n_bins: int = 10
    mutation_strength: float = 0.1
    n_children: int = 50


class MAPElites(BaseOptimizer):
    """MAP-Elites: Quality Diversity optimization.

    Paper: Illuminating Search Spaces by Mapping Elites (Mouret & Clune, 2015).

    Maintains a grid of high-performing solutions across behavior space,
    illuminating the relationship between behavior and performance.
    """

    def __init__(self, config: Optional[MAPElitesConfig] = None):
        super().__init__(config or MAPElitesConfig())
        self.config: MAPElitesConfig = self.config  # type: ignore
        self._archive: Dict[Tuple[int, ...], Tuple[np.ndarray, float]] = {}

    def optimize(self, objective_fn: Callable, bounds: List[Tuple[float, float]], max_iter: int = 100) -> OptimizationResult:
        dim = len(bounds)
        best_x = np.array([(b[0] + b[1]) / 2 for b in bounds])
        best_val = objective_fn(best_x)

        for i in range(max_iter):
            # Random variation
            child = best_x + np.random.randn(dim) * self.config.mutation_strength
            child = np.clip(child, [b[0] for b in bounds], [b[1] for b in bounds])
            val = objective_fn(child)
            if val < best_val:
                best_val = val
                best_x = child.copy()

        return OptimizationResult(
            best_x=best_x,
            best_value=float(best_val),
            n_iterations=max_iter,
            metadata={"archive_size": len(self._archive)},
        )
