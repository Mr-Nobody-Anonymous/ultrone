# Copyright (c) Ultrone Contributors. All rights reserved.
"""Nash equilibrium approximation for strategic games."""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("Ultrone.Brain.Reasoning.GameTheory.Nash")


@dataclass
class NashConfig:
    """Configuration for Nash equilibrium solver."""
    max_iterations: int = 10000
    tolerance: float = 1e-6
    method: str = "fictitious_play"  # fictitious_play, lemke_howson, replicator


class NashEquilibrium:
    """Nash equilibrium approximation using fictitious play.

    Finds mixed-strategy Nash equilibria for two-player games.
    """

    def __init__(self, config: Optional[NashConfig] = None):
        self.config = config or NashConfig()

    def solve(self, payoff_matrix_a: np.ndarray, payoff_matrix_b: Optional[np.ndarray] = None) -> Dict[str, Any]:
        """Approximate Nash equilibrium using fictitious play.

        Args:
            payoff_matrix_a: Payoff matrix for player A (num_actions_a x num_actions_b),
                or a stacked 3D array of shape (2, num_actions_a, num_actions_b)
                containing both players' payoffs.
            payoff_matrix_b: Payoff matrix for player B (num_actions_a x num_actions_b).
                If None, ``payoff_matrix_a`` must be a 3D array.

        Returns:
            Dict with mixed strategies for both players
        """
        # Support 3D stacked input: [A_payoffs, B_payoffs]
        if payoff_matrix_b is None:
            if payoff_matrix_a.ndim == 3:
                payoff_matrix_b = payoff_matrix_a[1]
                payoff_matrix_a = payoff_matrix_a[0]
            else:
                # Zero-sum default: B minimizes A's payoff
                payoff_matrix_b = -payoff_matrix_a

        n_a, n_b = payoff_matrix_a.shape
        strategy_a = np.ones(n_a) / n_a
        strategy_b = np.ones(n_b) / n_b
        counts_a = np.ones(n_a)
        counts_b = np.ones(n_b)

        for iteration in range(self.config.max_iterations):
            # Best response for A given B's strategy
            expected_a = payoff_matrix_a @ strategy_b
            br_a = np.zeros(n_a)
            br_a[np.argmax(expected_a)] = 1.0

            # Best response for B given A's strategy
            expected_b = payoff_matrix_b.T @ strategy_a
            br_b = np.zeros(n_b)
            br_b[np.argmax(expected_b)] = 1.0

            # Update counts and strategies
            counts_a += br_a
            counts_b += br_b
            new_strategy_a = counts_a / counts_a.sum()
            new_strategy_b = counts_b / counts_b.sum()

            # Check convergence
            if (np.max(np.abs(new_strategy_a - strategy_a)) < self.config.tolerance and
                    np.max(np.abs(new_strategy_b - strategy_b)) < self.config.tolerance):
                break

            strategy_a = new_strategy_a
            strategy_b = new_strategy_b

        # Compute expected payoffs
        value_a = strategy_a @ payoff_matrix_a @ strategy_b
        value_b = strategy_a @ payoff_matrix_b @ strategy_b

        return {
            "strategy_a": strategy_a.tolist(),
            "strategy_b": strategy_b.tolist(),
            "value_a": float(value_a),
            "value_b": float(value_b),
            "iterations": iteration + 1,
            "converged": iteration < self.config.max_iterations - 1,
        }

    def get_stats(self, payoff_matrix_a: Optional[np.ndarray] = None) -> Dict[str, Any]:
        stats: Dict[str, Any] = {
            "type": "NashEquilibrium",
            "method": self.config.method,
            "num_players": 2,
        }
        if payoff_matrix_a is not None:
            if payoff_matrix_a.ndim == 3:
                stats["num_actions_a"], stats["num_actions_b"] = payoff_matrix_a.shape[1], payoff_matrix_a.shape[2]
            else:
                stats["num_actions_a"], stats["num_actions_b"] = payoff_matrix_a.shape
        return stats
