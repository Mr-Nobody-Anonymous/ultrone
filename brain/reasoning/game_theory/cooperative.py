# Copyright (c) Ultrone Contributors. All rights reserved.
"""Cooperative game theory for coalitional decision-making.

Provides algorithms for solving cooperative (coalitional) games,
including Shapley value computation, Core stability checking,
and Nash bargaining solutions for multi-agent resource allocation.
"""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("Ultrone.Brain.Reasoning.GameTheory.Cooperative")


@dataclass
class CooperativeConfig:
    """Configuration for cooperative game solvers."""
    method: str = "shapley"  # shapley, core, bargaining, nucleolus
    max_iterations: int = 1000
    tolerance: float = 1e-6


class CooperativeGame:
    """Solver for cooperative (coalitional) games.

    In cooperative game theory, agents form coalitions and share the
    resulting payoff.  Key solution concepts:

    - **Shapley value**: Fair distribution of payoffs based on marginal contribution
    - **Core**: Set of payoff distributions that no coalition can improve upon
    - **Nash bargaining**: Symmetric bargaining solution for two-player games

    Integration
    -----------
    Used by :class:`~brain.reasoning.coordination.coalition.CoalitionFormation`
    to evaluate fairness of payoff distribution in agent coalitions.
    """

    def __init__(self, config: Optional[CooperativeConfig] = None):
        self.config = config or CooperativeConfig()

    def shapley_value(
        self,
        num_players: int,
        value_function: Callable[[Set[int]], float],
    ) -> Dict[int, float]:
        """Compute Shapley values for all players.

        The Shapley value of player i is the average marginal contribution
        of i over all possible coalitions and orderings.

        Parameters
        ----------
        num_players:
            Number of players in the game.
        value_function:
            Characteristic function v(S) -> payoff of coalition S (set of player indices).

        Returns
        -------
        Dict[int, float]
            Player index -> Shapley value.
        """
        players = list(range(num_players))
        shapley = {i: 0.0 for i in players}
        n = num_players

        # For efficiency, use sampling if n is large
        if n > 10:
            return self._shapley_sampling(num_players, value_function)

        # Exact computation for small n
        from itertools import permutations
        total_permutations = 0
        for perm in permutations(players):
            total_permutations += 1
            coalition: Set[int] = set()
            for idx, player in enumerate(perm):
                coalition_without = coalition.copy()
                coalition.add(player)
                marginal = value_function(coalition) - value_function(coalition_without)
                shapley[player] += marginal

        # Average over all permutations
        for player in shapley:
            shapley[player] /= max(1, total_permutations)

        return shapley

    def _shapley_sampling(
        self,
        num_players: int,
        value_function: Callable[[Set[int]], float],
        num_samples: int = 1000,
    ) -> Dict[int, float]:
        """Approximate Shapley values via Monte Carlo sampling."""
        players = list(range(num_players))
        shapley = {i: 0.0 for i in players}

        for _ in range(num_samples):
            perm = list(np.random.permutation(players))
            coalition: Set[int] = set()
            for player in perm:
                coalition_without = coalition.copy()
                coalition.add(player)
                marginal = value_function(coalition) - value_function(coalition_without)
                shapley[player] += marginal

        for player in shapley:
            shapley[player] /= num_samples

        return shapley

    def core_stability(
        self,
        num_players: int,
        value_function: Callable[[Set[int]], float],
        allocation: Dict[int, float],
    ) -> Dict[str, Any]:
        """Check if a payoff allocation is in the Core.

        An allocation is in the Core if no coalition can deviate and
        obtain a higher total payoff for its members.

        Parameters
        ----------
        num_players:
            Number of players.
        value_function:
            Characteristic function v(S).
        allocation:
            Proposed payoff distribution {player: payoff}.

        Returns
        -------
        Dict with stability status and blocking coalitions.
        """
        players = set(range(num_players))
        total_allocation = sum(allocation.values())

        # Grand coalition efficiency
        grand_value = value_function(players)
        efficient = abs(total_allocation - grand_value) < self.config.tolerance

        # Check all possible coalitions (2^n - 1)
        blocking: List[Set[int]] = []
        from itertools import combinations
        for r in range(1, num_players + 1):
            for coalition in combinations(range(num_players), r):
                coalition_set = set(coalition)
                coalition_value = value_function(coalition_set)
                coalition_allocation = sum(allocation[i] for i in coalition_set)

                if coalition_allocation < coalition_value - self.config.tolerance:
                    blocking.append(coalition_set)

        return {
            "in_core": len(blocking) == 0 and efficient,
            "efficient": efficient,
            "num_blocking_coalitions": len(blocking),
            "blocking_coalitions": [list(c) for c in blocking[:10]],  # Top 10
            "grand_coalition_value": grand_value,
            "total_allocation": total_allocation,
        }

    def nash_bargaining(
        self,
        disagreement: Tuple[float, float],
        utility_set: List[Tuple[float, float]],
    ) -> Dict[str, Any]:
        """Find the Nash bargaining solution for two players.

        The Nash bargaining solution maximizes the product of utilities
        above the disagreement point: argmax (u1 - d1) * (u2 - d2).

        Parameters
        ----------
        disagreement:
            Disagreement payoffs (d1, d2).
        utility_set:
            List of feasible utility pairs (u1, u2).

        Returns
        -------
        Dict with bargaining solution.
        """
        d1, d2 = disagreement
        best_solution = None
        best_product = -float("inf")

        for u1, u2 in utility_set:
            if u1 > d1 and u2 > d2:
                product = (u1 - d1) * (u2 - d2)
                if product > best_product:
                    best_product = product
                    best_solution = (u1, u2)

        return {
            "solution": best_solution,
            "disagreement": disagreement,
            "nash_product": best_product if best_product > -float("inf") else 0.0,
            "feasible_solutions": len(utility_set),
        }

    def compute_shapley(self, values: Dict[str, float]) -> Dict[str, Any]:
        """Compute Shapley values from a simple value dictionary.

        Treats each key as a player and the value as that player's
        standalone contribution.  Used by the test contract.

        Args:
            values: Mapping of player_name -> contribution value.

        Returns:
            Dict with Shapley values per player.
        """
        players = list(values.keys())
        n = len(players)
        # For a simple additive value function, the Shapley value of each
        # player equals their standalone value exactly once per ordering —
        # average over all permutations reduces to the standalone value.
        total = sum(values.values())
        result: Dict[str, Any] = {}
        for p in players:
            # Marginal contribution of p when added after any subset S:
            # v(S ∪ {p}) - v(S) = values[p]. Averaging over all orderings
            # gives exactly values[p].
            result[p] = float(values[p])
        result["total_value"] = float(total)
        result["value_function_type"] = "additive"
        return result

    def solve(self, payoff_matrix: np.ndarray) -> Dict[str, Any]:
        """Convenience wrapper: solve a cooperative game from a payoff matrix.

        Treats each row as a player's contribution to coalitions.
        """
        n = payoff_matrix.shape[0]
        # Define value function from payoff matrix
        def v(S: Set[int]) -> float:
            return sum(payoff_matrix[i].sum() for i in S) / n

        shapley = self.shapley_value(n, v)
        allocation = {i: shapley[i] for i in range(n)}
        core = self.core_stability(n, v, allocation)

        return {
            "shapley_values": shapley,
            "allocation": allocation,
            "core_stability": core,
            "method": self.config.method,
            "num_players": n,
        }

    def get_stats(self) -> Dict[str, Any]:
        return {"type": "CooperativeGame", "method": self.config.method}

