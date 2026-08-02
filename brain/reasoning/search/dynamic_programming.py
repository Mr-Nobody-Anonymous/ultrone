# Copyright (c) Ultrone Contributors. All rights reserved.
"""Dynamic Programming (DP) planner for optimal planning."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from .base import Planner, PlanningAction, PlanningDomain, PlanningGoal, PlanningResult

logger = logging.getLogger("Ultrone.Brain.Reasoning.Search.DP")


@dataclass
class DPConfig:
    """Configuration for DP planner."""
    max_states: int = 1000
    max_horizon: int = 50
    gamma: float = 0.99
    max_iterations: int = 200
    convergence_threshold: float = 1e-3
    horizon: int = 50


class DPPlanner(Planner):
    """Dynamic Programming planner using value iteration.

    Computes optimal plans for finite-horizon problems using
    backward induction (value iteration). Suitable for well-defined
    MDPs with small state spaces.
    """

    def __init__(self, config: Optional[DPConfig] = None) -> None:
        super().__init__()
        self.config = config or DPConfig()
        self._value_table: Dict[Any, float] = {}
        self._policy: Dict[Any, PlanningAction] = {}
        self._state_enumeration: Optional[List[Any]] = None

    def initialize(self, domain: PlanningDomain, state_enumeration: Optional[List[Any]] = None) -> None:
        super().initialize(domain)
        self._state_enumeration = state_enumeration

    def _compute_value(self, state: Any, goal: Any, depth: int, domain: PlanningDomain) -> float:
        """Compute value of state using backward induction.

        Memoized on ``(state, depth)`` to avoid the exponential blow-up that
        occurs when the same state is reachable along many different action
        sequences (which previously made the planner hang on any non-trivial
        grid).
        """
        if depth >= self.config.max_horizon:
            return 0.0
        if state == goal:
            return 1.0

        key = (state, depth)
        if key in self._value_table:
            return self._value_table[key]

        best_value = float("-inf")
        best_action = None
        for action in domain.discrete_actions:
            # Compute next state
            if isinstance(state, tuple) and len(state) == 2:
                x, y = state
                nx = x + action.parameters.get("dx", 0)
                ny = y + action.parameters.get("dy", 0)
                next_state = (nx, ny)
            else:
                next_state = state

            reward = 1.0 if next_state == goal else 0.0
            value = reward + self.config.gamma * self._compute_value(next_state, goal, depth + 1, domain)
            if value > best_value:
                best_value = value
                best_action = action

        if best_action is not None:
            self._value_table[key] = best_value
            self._policy[key] = best_action
        else:
            self._value_table[key] = 0.0

        return self._value_table[key]

    def plan(self, state: Any, goal: PlanningGoal) -> PlanningResult:
        domain = self._domain
        if domain is None:
            raise RuntimeError("DPPlanner not initialised — call .initialize() first.")

        target = goal.target_state if goal.target_state is not None else state
        self._value_table.clear()
        self._policy.clear()

        # Start is the goal: trivially successful empty plan.
        if state == target:
            result = PlanningResult(success=True, actions=[], cost=0.0, plan_length=0)
            return self._record_result(result)

        self._compute_value(state, target, 0, domain)

        # Extract plan following the depth-indexed policy.
        actions: List[PlanningAction] = []
        current = state
        visited = set()
        for step in range(self.config.max_horizon):
            key = (current, step)
            if key in self._policy:
                action = self._policy[key]
                actions.append(action)
                if isinstance(current, tuple) and len(current) == 2:
                    x, y = current
                    nx = x + action.parameters.get("dx", 0)
                    ny = y + action.parameters.get("dy", 0)
                    current = (nx, ny)
                if current == target:
                    break
                if current in visited:  # cycle guard
                    break
                visited.add(current)
            else:
                break

        result = PlanningResult(
            success=len(actions) > 0,
            actions=actions,
            cost=len(actions),
            plan_length=len(actions),
        )
        logger.info("DP plan found: %d actions", result.plan_length)
        return self._record_result(result)

    def get_stats(self) -> Dict[str, Any]:
        stats = super().get_stats()
        stats["has_policy"] = len(self._policy)
        return stats
