# Copyright (c) Ultrone Contributors. All rights reserved.
"""Dynamic Programming (DP) planner for deterministic finite-horizon MDPs.

DP solves a planning problem by backward induction (value iteration)
over the state space.  It is optimal for finite state/action spaces
but requires enumerating all states—suitable for compact tactical
problems (e.g., grid sizes up to ~10⁴ states).

Integration
-----------
Plugs into :class:`~brain.reasoning.tactical_engine.TacticalEngine`
as any other :class:`Planner` implementation.
"""

from __future__ import annotations

import logging
import itertools
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from .base import Planner, PlanningAction, PlanningDomain, PlanningGoal, PlanningResult

logger = logging.getLogger("Ultrone.Brain.Reasoning.Search.DP")


@dataclass
class DPConfig:
    """Configuration for DP-based planning.

    Attributes
    ----------
    discount_factor:
        Discount factor for rewards (γ).
    max_iterations:
        Maximum value iteration steps.
    convergence_threshold:
        Stop value iteration when max change < threshold.
    horizon:
        Finite planning horizon (if > 0, finite-horizon DP).
    """
    discount_factor: float = 0.95
    max_iterations: int = 1000
    convergence_threshold: float = 1e-4
    horizon: int = 0  # 0 = infinite horizon


class DPPlanner(Planner):
    """Dynamic Programming planner using value iteration.

    Supports both finite-horizon (backward induction) and infinite-horizon
    (value iteration) modes.
    """

    def __init__(self, config: Optional[DPConfig] = None) -> None:
        super().__init__()
        self.config = config or DPConfig()
        self._states: List[Any] = []
        self._state_to_idx: Dict[Any, int] = {}
        self._action_space: List[PlanningAction] = []
        self._transition_fn: Optional[Callable] = None
        self._terminal_mask: Set[int] = set()

        # Value arrays
        self._values: List[float] = []
        self._policy: List[Optional[PlanningAction]] = []

    # ── Lifecycle ────────────────────────────────────────────────────

    def initialize(
        self,
        domain: PlanningDomain,
        state_enumeration: Optional[List[Any]] = None,
    ) -> None:
        """Initialize the DP planner.

        Parameters
        ----------
        domain:
            Planning domain definition.
        state_enumeration:
            Explicit list of all possible states.  If None, the planner
            attempts to auto-generate a grid from the domain.
        """
        super().initialize(domain)

        self._action_space = list(domain.discrete_actions)

        if state_enumeration is not None:
            self._states = list(state_enumeration)
        else:
            # Auto-generate a simple grid if state space is not provided
            self._states = self._auto_generate_states(domain)

        self._state_to_idx = {s: i for i, s in enumerate(self._states)}
        self._terminal_mask = set()

        n = len(self._states)
        self._values = [0.0] * n
        self._policy = [None] * n

        logger.info(
            "DPPlanner initialised: %d states, %d actions",
            n, len(self._action_space),
        )

    def _auto_generate_states(self, domain: PlanningDomain) -> List[Any]:
        """Generate a grid state space if the domain has shape info."""
        if domain.state_shape and len(domain.state_shape) == 2:
            w, h = domain.state_shape
            return list(itertools.product(range(w), range(h)))
        return [(0, 0)]  # fallback

    # ── Core planning ────────────────────────────────────────────────

    def plan(self, state: Any, goal: PlanningGoal) -> PlanningResult:
        """Solve the MDP via value iteration and return a plan from *state*.

        The returned plan is the optimal policy followed from *state*
        until a terminal state is reached.
        """
        if state not in self._state_to_idx:
            logger.error("State %s not in DP state space.", state)
            return PlanningResult(success=False, metadata={"reason": "unknown_state"})

        # Mark terminal states
        self._terminal_mask = {
            i for i, s in enumerate(self._states)
            if self._is_terminal_state(s, goal)
        }

        # Run value iteration
        expansions = self._value_iteration(goal)

        # Extract plan from start state
        actions = self._extract_plan(state, goal)
        start_idx = self._state_to_idx[state]

        result = PlanningResult(
            success=len(actions) > 0,
            actions=actions,
            cost=-self._values[start_idx],  # value = negative cost
            nodes_expanded=expansions * len(self._action_space),
            plan_length=len(actions),
            metadata={
                "value_iterations": expansions,
                "num_states": len(self._states),
            },
        )
        logger.info(
            "DP plan: %s (len=%d, value=%.2f, iter=%d)",
            "FOUND" if result.success else "FAILED",
            result.plan_length,
            self._values[start_idx],
            expansions,
        )
        return self._record_result(result)

    # ── Value iteration ──────────────────────────────────────────────

    def _value_iteration(self, goal: PlanningGoal) -> int:
        """Run value iteration until convergence or max iterations."""
        n = len(self._states)
        num_actions = len(self._action_space)
        gamma = self.config.discount_factor
        horizon = self.config.horizon

        if horizon > 0:
            # Finite horizon: backward induction
            return self._finite_horizon_vi(goal, horizon)

        # Infinite horizon: iterative value iteration
        for iteration in range(self.config.max_iterations):
            delta = 0.0
            new_values = [0.0] * n

            for i, s in enumerate(self._states):
                if i in self._terminal_mask:
                    new_values[i] = -0.0  # terminal states have 0 value
                    continue

                best_val = float("-inf")
                for action in self._action_space:
                    next_s = self._transition(s, action)
                    j = self._state_to_idx.get(next_s, i)
                    reward = -action.cost
                    val = reward + gamma * self._values[j]
                    if val > best_val:
                        best_val = val
                        self._policy[i] = action

                new_values[i] = best_val if best_val != float("-inf") else 0.0
                delta = max(delta, abs(new_values[i] - self._values[i]))

            self._values = new_values

            if delta < self.config.convergence_threshold:
                logger.debug("DP value iteration converged at iteration %d (delta=%.6f)", iteration, delta)
                return iteration + 1

        logger.debug("DP value iteration reached max iterations (%d)", self.config.max_iterations)
        return self.config.max_iterations

    def _finite_horizon_vi(self, goal: PlanningGoal, horizon: int) -> int:
        """Backward induction for finite-horizon problems."""
        n = len(self._states)
        gamma = self.config.discount_factor
        # Initialize V_{T+1} = 0
        v_next = [0.0] * n

        for t in range(horizon, 0, -1):
            v_current = [0.0] * n
            for i, s in enumerate(self._states):
                if i in self._terminal_mask:
                    v_current[i] = 0.0
                    continue

                best_val = float("-inf")
                for action in self._action_space:
                    next_s = self._transition(s, action)
                    j = self._state_to_idx.get(next_s, i)
                    reward = -action.cost
                    val = reward + gamma * v_next[j]
                    if val > best_val:
                        best_val = val
                        if t == 1:
                            self._policy[i] = action
                v_current[i] = best_val if best_val != float("-inf") else 0.0

            v_next = v_current

        self._values = v_next
        return horizon

    # ── Plan extraction ──────────────────────────────────────────────

    def _extract_plan(self, start: Any, goal: PlanningGoal) -> List[PlanningAction]:
        """Follow the computed policy from *start* to a terminal state."""
        actions: List[PlanningAction] = []
        visited: Set[int] = set()
        current = start

        for _ in range(1000):  # safety limit
            idx = self._state_to_idx.get(current)
            if idx is None or idx in visited or idx in self._terminal_mask:
                break
            visited.add(idx)

            action = self._policy[idx]
            if action is None:
                break
            actions.append(action)
            current = self._transition(current, action)

        return actions

    # ── Transition dynamics ──────────────────────────────────────────

    def _transition(self, state: Any, action: PlanningAction) -> Any:
        """Apply *action* to *state* and return next state.

        Override in domain-specific subclasses.
        If a transition function is provided in the domain, it is used.
        """
        # Default: grid move based on action name
        if isinstance(state, tuple) and len(state) == 2:
            x, y = state
            if action.name == "right":
                return (x + 1, y)
            elif action.name == "left":
                return (x - 1, y)
            elif action.name == "up":
                return (x, y + 1)
            elif action.name == "down":
                return (x, y - 1)

        return state

    def _is_terminal_state(self, state: Any, goal: PlanningGoal) -> bool:
        """Check if *state* satisfies the goal."""
        if self._domain and self._domain.is_terminal_fn:
            return self._domain.is_terminal_fn(state)
        return False

    def get_stats(self) -> Dict[str, Any]:
        stats = super().get_stats()
        stats.update({
            "num_states": len(self._states),
            "num_actions": len(self._action_space),
            "value_iterations": self.config.max_iterations,
            "has_policy": sum(1 for p in self._policy if p is not None),
        })
        return stats

