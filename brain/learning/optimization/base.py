# Copyright (c) Ultrone Contributors. All rights reserved.
"""Base interface for all optimization algorithms."""

from __future__ import annotations

import logging
import numpy as np
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("Ultrone.Brain.Learning.Optimization.Base")


@dataclass
class OptimizerConfig:
    """Base configuration for optimizers."""
    max_iterations: int = 1000
    tolerance: float = 1e-6
    seed: int = 42
    verbose: bool = False


@dataclass
class OptimizationResult:
    """Result of an optimization run."""
    best_params: np.ndarray
    best_value: float
    n_iterations: int
    n_evaluations: int
    convergence_history: List[float] = field(default_factory=list)
    success: bool = True

    def __iter__(self):
        """Allow tuple unpacking as (best_value, best_params) for test compatibility."""
        yield self.best_value
        yield self.best_params


class BaseOptimizer(ABC):
    """Abstract interface every optimizer must implement."""

    def __init__(self, config: OptimizerConfig):
        self.config = config
        self._n_evaluations = 0
        self._history: List[float] = []

    @abstractmethod
    def optimize(
        self,
        objective_fn: Callable[[np.ndarray], float],
        bounds: List[Tuple[float, float]],
    ) -> OptimizationResult:
        """Run optimization and return best solution."""
        ...

    def get_stats(self) -> Dict[str, Any]:
        return {
            "type": type(self).__name__,
            "n_evaluations": self._n_evaluations,
            "best_value": self._history[-1] if self._history else None,
        }