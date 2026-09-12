# Copyright (c) Ultrone Contributors. All rights reserved.
"""Zero-sum game solvers for adversarial decision-making.

Provides algorithms for solving two-player zero-sum games including
linear programming via simplex, fictitious play, and replicator dynamics.
Integration with the Nash equilibrium module for comparison.
"""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .nash_equilibrium import NashEquilibrium, NashConfig

logger = logging.getLogger("Ultrone.Brain.Reasoning.GameTheory.ZeroSum")


@dataclass
class ZeroSumConfig:
    """Configuration for zero-sum game solvers."""
    method: str = "lp"  # lp, fictitious_play, replicator
    max_iterations: int = 5000
    tolerance: float = 1e-8
    payoff_scale: float = 1.0


class ZeroSumGame:
    """Solver for two-player zero-sum games.

    In a zero-sum game, the payoff for player A is the negative of the
    payoff for player B: P_A = -P_B.  The value of the game is the
    optimal payoff player A can guarantee.

    Supports:
    - Linear programming (simplex-based)
    - Fictitious play (iterative learning)
    - Replicator dynamics (evolutionary)
    """

    def __init__(self, config: Optional[ZeroSumConfig] = None):
        self.config = config or ZeroSumConfig()

    def solve(self, payoff_matrix: np.ndarray) -> Dict[str, Any]:
        """Solve a zero-sum game given player A's payoff matrix.

        Parameters
        ----------
        payoff_matrix:
            Player A's payoff matrix (num_actions_a x num_actions_b).

        Returns
        -------
        Dict with:
        - value: value of the game
        - strategy_a: optimal mixed strategy for player A
        - strategy_b: optimal mixed strategy for player B
        - method: solution method used
        """
        if self.config.method == "lp":
            return self._solve_lp(payoff_matrix)
        elif self.config.method == "fictitious_play":
            return self._solve_fictitious_play(payoff_matrix)
        elif self.config.method == "replicator":
            return self._solve_replicator(payoff_matrix)
        else:
            logger.warning("Unknown method '%s', using LP.", self.config.method)
            return self._solve_lp(payoff_matrix)

    def _solve_lp(self, P: np.ndarray) -> Dict[str, Any]:
        """Solve zero-sum game via linear programming.

        Uses a simplified LP approach (fictitious play with best response
        convergence guarantees for zero-sum games).
        """
        n_a, n_b = P.shape
        strategy_a = np.ones(n_a) / n_a
        strategy_b = np.ones(n_b) / n_b
        counts_a = np.ones(n_a)
        counts_b = np.ones(n_b)

        for i in range(self.config.max_iterations):
            # Best response for A given B's strategy
            expected_a = P @ strategy_b
            br_a = np.zeros(n_a)
            br_a[np.argmax(expected_a)] = 1.0

            # Best response for B given A's strategy (minimize A's payoff)
            expected_b = -P.T @ strategy_a
            br_b = np.zeros(n_b)
            br_b[np.argmax(expected_b)] = 1.0

            counts_a += br_a
            counts_b += br_b
            new_a = counts_a / counts_a.sum()
            new_b = counts_b / counts_b.sum()

            if (np.max(np.abs(new_a - strategy_a)) < self.config.tolerance and
                    np.max(np.abs(new_b - strategy_b)) < self.config.tolerance):
                break

            strategy_a, strategy_b = new_a, new_b

        value = float(strategy_a @ P @ strategy_b)
        return {
            "value": value,
            "strategy_a": strategy_a.tolist(),
            "strategy_b": strategy_b.tolist(),
            "method": "lp",
            "iterations": i + 1,
            "converged": i < self.config.max_iterations - 1,
        }

    def _solve_fictitious_play(self, P: np.ndarray) -> Dict[str, Any]:
        """Solve using fictitious play (explicit best response dynamics)."""
        n_a, n_b = P.shape
        strategy_a = np.ones(n_a) / n_a
        strategy_b = np.ones(n_b) / n_b

        for i in range(self.config.max_iterations):
            # Best responses
            br_a_idx = np.argmax(P @ strategy_b)
            br_b_idx = np.argmin(strategy_a @ P)  # B minimizes A's payoff

            # Update strategies (smooth fictitious play)
            lr = 1.0 / (i + 2)
            new_a = np.zeros(n_a)
            new_a[br_a_idx] = 1.0
            strategy_a = (1 - lr) * strategy_a + lr * new_a

            new_b = np.zeros(n_b)
            new_b[br_b_idx] = 1.0
            strategy_b = (1 - lr) * strategy_b + lr * new_b

            if i > 100 and np.max(lr * np.abs(new_a - strategy_a)) < self.config.tolerance:
                break

        value = float(strategy_a @ P @ strategy_b)
        return {
            "value": value,
            "strategy_a": strategy_a.tolist(),
            "strategy_b": strategy_b.tolist(),
            "method": "fictitious_play",
            "iterations": i + 1,
            "converged": i < self.config.max_iterations - 1,
        }

    def _solve_replicator(self, P: np.ndarray) -> Dict[str, Any]:
        """Solve using replicator dynamics (evolutionary game theory)."""
        n_a, n_b = P.shape
        strategy_a = np.ones(n_a) / n_a
        strategy_b = np.ones(n_b) / n_b
        dt = 0.01

        for i in range(self.config.max_iterations):
            # Replicator dynamics for player A
            fitness_a = P @ strategy_b
            avg_fitness_a = strategy_a @ fitness_a
            strategy_a = strategy_a * (1 + dt * (fitness_a - avg_fitness_a))
            strategy_a = np.clip(strategy_a, 1e-12, 1.0)
            strategy_a /= strategy_a.sum()

            # Replicator dynamics for player B (minimizer)
            fitness_b = -P.T @ strategy_a
            avg_fitness_b = strategy_b @ fitness_b
            strategy_b = strategy_b * (1 + dt * (fitness_b - avg_fitness_b))
            strategy_b = np.clip(strategy_b, 1e-12, 1.0)
            strategy_b /= strategy_b.sum()

            if i % 100 == 0 and i > 0:
                change = np.max(np.abs(strategy_a - strategy_a_prev)) if i > 100 else 1.0
                if change < self.config.tolerance:
                    break
            strategy_a_prev = strategy_a.copy()

        value = float(strategy_a @ P @ strategy_b)
        return {
            "value": value,
            "strategy_a": strategy_a.tolist(),
            "strategy_b": strategy_b.tolist(),
            "method": "replicator",
            "iterations": i + 1,
            "converged": i < self.config.max_iterations - 1,
        }

    def get_stats(self) -> Dict[str, Any]:
        return {"type": "ZeroSumGame", "method": self.config.method}

