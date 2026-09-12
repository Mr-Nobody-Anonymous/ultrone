# Copyright (c) Ultrone Contributors. All rights reserved.
"""Stackelberg game models for leader-follower strategic interactions."""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Ultrone.Brain.Reasoning.GameTheory.Stackelberg")


@dataclass
class StackelbergConfig:
    """Configuration for Stackelberg game solver."""
    max_iterations: int = 100
    tolerance: float = 1e-4


class StackelbergGame:
    """Stackelberg leader-follower game solver.

    The leader commits to a strategy first; the follower best-responds.
    The leader optimizes anticipating the follower's response.
    """

    def __init__(self, config: Optional[StackelbergConfig] = None):
        self.config = config or StackelbergConfig()

    def solve(self, num_actions: int = 5) -> Dict[str, Any]:
        """Solve a Stackelberg game with random payoff matrices.

        Compatible convenience wrapper used by tests: ``solve(num_actions=5)``.

        Args:
            num_actions: Number of actions for both leader and follower.

        Returns:
            Dict with optimal leader strategy and expected payoff.
        """
        rng = np.random.default_rng(42)
        leader_payoffs = rng.uniform(0, 10, size=(num_actions, num_actions))
        follower_payoffs = rng.uniform(0, 10, size=(num_actions, num_actions))
        result = self.solve_leader(leader_payoffs, follower_payoffs)
        result.update({
            "leader_strategy": np.eye(num_actions)[result["leader_action"]].tolist(),
            "num_actions": num_actions,
        })
        return result

    def solve_leader(self, leader_payoffs: np.ndarray, follower_payoffs: np.ndarray) -> Dict[str, Any]:
        """Solve for the leader's optimal strategy.

        Args:
            leader_payoffs: (n_leader_actions, n_follower_actions) payoff matrix
            follower_payoffs: (n_leader_actions, n_follower_actions) payoff matrix

        Returns:
            Dict with optimal leader strategy and expected payoff
        """
        n_leader, n_follower = leader_payoffs.shape
        best_value = float("-inf")
        best_action = 0

        for a in range(n_leader):
            # Follower best-responds to leader action a
            follower_br = np.argmax(follower_payoffs[a])
            leader_value = leader_payoffs[a, follower_br]
            if leader_value > best_value:
                best_value = leader_value
                best_action = a

        return {
            "leader_action": int(best_action),
            "leader_value": float(best_value),
            "follower_response": int(np.argmax(follower_payoffs[best_action])),
        }

    def get_stats(self) -> Dict[str, Any]:
        return {"type": "StackelbergGame"}