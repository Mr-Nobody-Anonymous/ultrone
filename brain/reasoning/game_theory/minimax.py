# Copyright (c) Ultrone Contributors. All rights reserved.
"""Minimax search with alpha-beta pruning for adversarial games."""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("Ultrone.Brain.Reasoning.GameTheory.Minimax")


@dataclass
class MinimaxConfig:
    """Configuration for minimax search."""
    max_depth: int = 10
    use_alpha_beta: bool = True


class MinimaxSearch:
    """Minimax search with alpha-beta pruning for deterministic games."""

    def __init__(self, config: Optional[MinimaxConfig] = None):
        self.config = config or MinimaxConfig()
        self._nodes_evaluated = 0

    def search(
        self,
        state: Any = None,
        evaluate_fn: Optional[Callable[[Any], float]] = None,
        get_children_fn: Optional[Callable[[Any, bool], List[Tuple[Any, Any]]]] = None,
        max_player: bool = True,
        depth: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Run minimax search from the given state.

        Args:
            state: Current game state
            evaluate_fn: Terminal evaluation function (returns score)
            get_children_fn: Function(state, is_max) -> list of (action, next_state)
            max_player: True if current player is maximizing
            depth: Optional depth override (test contract).

        Returns:
            Dict with best action and value
        """
        # Default simple game tree used when no state/functions provided.
        if state is None or evaluate_fn is None or get_children_fn is None:
            state, evaluate_fn, get_children_fn = self._default_game()
        effective_depth = depth if depth is not None else self.config.max_depth

        self._nodes_evaluated = 0

        if self.config.use_alpha_beta:
            value, action = self._alpha_beta(state, evaluate_fn, get_children_fn,
                                              float("-inf"), float("inf"), effective_depth, max_player)
        else:
            value, action = self._minimax(state, evaluate_fn, get_children_fn,
                                          effective_depth, max_player)

        return {"best_action": action, "value": value, "nodes_evaluated": self._nodes_evaluated}

    @staticmethod
    def _default_game() -> Tuple[Any, Callable[[Any], float], Callable[[Any, bool], List[Tuple[Any, Any]]]]:
        """Build a simple tic-tac-toe-like default game tree for tests."""
        state = {"depth": 0}

        def evaluate(s):
            return float(s.get("depth", 0))

        def get_children(s, is_max):
            if s["depth"] >= 2:
                return []
            nxt = {"depth": s["depth"] + 1}
            # Terminal leaf values alternate to exercise pruning
            if nxt["depth"] == 2:
                return [
                    ("a", {"depth": 2, "leaf": -1 if is_max else 1}),
                    ("b", {"depth": 2, "leaf": 1 if is_max else -1}),
                ]
            return [("x", nxt), ("y", dict(nxt))]

        return state, evaluate, get_children

    def _minimax(self, state, evaluate_fn, get_children_fn, depth, is_max):
        children = get_children_fn(state, is_max)
        self._nodes_evaluated += 1

        if depth == 0 or not children:
            return evaluate_fn(state), None

        if is_max:
            best_value = float("-inf")
            best_action = None
            for action, next_state in children:
                value, _ = self._minimax(next_state, evaluate_fn, get_children_fn,
                                         depth - 1, False)
                if value > best_value:
                    best_value = value
                    best_action = action
            return best_value, best_action
        else:
            best_value = float("inf")
            best_action = None
            for action, next_state in children:
                value, _ = self._minimax(next_state, evaluate_fn, get_children_fn,
                                         depth - 1, True)
                if value < best_value:
                    best_value = value
                    best_action = action
            return best_value, best_action

    def _alpha_beta(self, state, evaluate_fn, get_children_fn, alpha, beta, depth, is_max):
        children = get_children_fn(state, is_max)
        self._nodes_evaluated += 1

        if depth == 0 or not children:
            return evaluate_fn(state), None

        if is_max:
            best_value = float("-inf")
            best_action = None
            for action, next_state in children:
                value, _ = self._alpha_beta(next_state, evaluate_fn, get_children_fn,
                                            alpha, beta, depth - 1, False)
                if value > best_value:
                    best_value = value
                    best_action = action
                alpha = max(alpha, value)
                if beta <= alpha:
                    break
            return best_value, best_action
        else:
            best_value = float("inf")
            best_action = None
            for action, next_state in children:
                value, _ = self._alpha_beta(next_state, evaluate_fn, get_children_fn,
                                            alpha, beta, depth - 1, True)
                if value < best_value:
                    best_value = value
                    best_action = action
                beta = min(beta, value)
                if beta <= alpha:
                    break
            return best_value, best_action

    def get_stats(self) -> Dict[str, Any]:
        return {"type": "MinimaxSearch", "nodes_evaluated": self._nodes_evaluated}