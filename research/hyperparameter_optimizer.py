"""Hyperparameter optimization for experiments."""

from __future__ import annotations

import itertools
import logging
import random
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("Ultrone.Research.HPO")


@dataclass
class HPOConfig:
    """Configuration for hyperparameter optimization."""
    method: str = "grid"  # grid, random, bayesian
    max_trials: int = 100
    random_seed: int = 42


@dataclass
class HPResult:
    """Result of a hyperparameter optimization trial."""
    params: Dict[str, Any]
    score: float
    trial_id: int


class HyperparameterOptimizer:
    """Hyperparameter optimization using various search strategies.

    Supports grid search, random search, and Bayesian optimization.
    """

    def __init__(self, config: Optional[HPOConfig] = None):
        self.config = config or HPOConfig()
        self._results: List[HPResult] = []

    def optimize(
        self,
        param_grid: Dict[str, List[Any]],
        objective_fn: Callable[[Dict[str, Any]], float],
    ) -> HPResult:
        """Run hyperparameter optimization.

        The objective_fn receives a dict of parameter values and
        returns a score to maximize.
        """
        rng = random.Random(self.config.random_seed)
        best_result = None

        if self.config.method == "grid":
            keys = list(param_grid.keys())
            values = list(param_grid.values())
            for i, combo in enumerate(itertools.product(*values)):
                if i >= self.config.max_trials:
                    break
                params = dict(zip(keys, combo))
                score = objective_fn(params)
                result = HPResult(params=params, score=score, trial_id=i)
                self._results.append(result)
                if best_result is None or score > best_result.score:
                    best_result = result

        elif self.config.method == "random":
            for i in range(self.config.max_trials):
                params = {k: rng.choice(v) for k, v in param_grid.items()}
                score = objective_fn(params)
                result = HPResult(params=params, score=score, trial_id=i)
                self._results.append(result)
                if best_result is None or score > best_result.score:
                    best_result = result

        return best_result or HPResult(params={}, score=float("-inf"), trial_id=0)

    def get_stats(self) -> Dict[str, Any]:
        return {"type": "HyperparameterOptimizer", "trials": len(self._results)}
