# Copyright (c) Ultrone Contributors. All rights reserved.
"""Receding Horizon Control (RHC) planner.

RHC solves a short-horizon planning problem at each decision step,
executes the first action, re-observes the environment, and replans.
This makes it robust to uncertainty and dynamic changes—ideal for
real-time battlefield control.

Integration
-----------
Plugs into :class:`~brain.reasoning.tactical_engine.TacticalEngine`
as any other :class:`Planner` implementation.  The inner planner can
be any :class:`Planner` (e.g., ``AStar``, ``MCTS``).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable

from .base import Planner, PlanningAction, PlanningDomain, PlanningGoal, PlanningResult

logger = logging.getLogger("Ultrone.Brain.Reasoning.Search.RHC")


@dataclass
class RecedingHorizonConfig:
    """Configuration for Receding Horizon Control.

    Attributes
    ----------
    horizon:
        Planning horizon (number of steps to look ahead).
    receding_step:
        How many steps to execute before replanning (usually 1).
    max_total_steps:
        Maximum total steps across the entire mission.
    """
    horizon: int = 5
    receding_step: int = 1
    max_total_steps: int = 200


class RecedingHorizonPlanner(Planner):
    """Receding Horizon Control planner.

    Repeatedly plans over a short horizon, executes the first
    ``receding_step`` actions, and replans.

    Parameters
    ----------
    inner_planner:
        The planner used for the local planning sub-problem.
    config:
        RHC hyper-parameters.
    """

    def __init__(
        self,
        inner_planner: Planner,
        config: Optional[RecedingHorizonConfig] = None,
    ) -> None:
        super().__init__()
        self._inner = inner_planner
        self.config = config or RecedingHorizonConfig()
        self._step: int = 0
        self._state: Any = None
        self._transition_fn: Optional[Callable] = None

    def initialize(self, domain: PlanningDomain) -> None:
        super().initialize(domain)
        self._inner.initialize(domain)
        self._transition_fn = domain.action_cost_fn

    def plan(self, state: Any, goal: PlanningGoal) -> PlanningResult:
        """Run RHC until the goal is achieved or max steps reached.

        Returns a single combined plan across all receding-horizon
        iterations.
        """
        self._step = 0
        self._state = state
        all_actions: List[PlanningAction] = []
        total_cost = 0.0
        expansions = 0

        while self._step < self.config.max_total_steps:
            # Create subgoal at horizon
            sub_goal = PlanningGoal(
                description=goal.description,
                predicates=goal.predicates,
                target_state=goal.target_state,
            )

            # Plan over horizon
            result = self._inner.plan(self._state, sub_goal)
            expansions += result.nodes_expanded

            if not result.success or not result.actions:
                break

            # Execute first k actions
            k = min(self.config.receding_step, len(result.actions))
            for i in range(k):
                action = result.actions[i]
                all_actions.append(action)
                total_cost += action.cost
                self._state = self._transition(self._state, action)
                self._step += 1

            # Goal check
            if self._is_terminal(self._state, goal):
                final = PlanningResult(
                    success=True,
                    actions=all_actions,
                    cost=total_cost,
                    nodes_expanded=expansions,
                    plan_length=len(all_actions),
                )
                logger.info("RHC plan found: len=%d, cost=%.2f", final.plan_length, final.cost)
                return self._record_result(final)

        return PlanningResult(
            success=False,
            actions=all_actions,
            cost=total_cost,
            nodes_expanded=expansions,
            plan_length=len(all_actions),
            metadata={"reason": "step_limit_exceeded"},
        )

    def update(self, observation: Any) -> None:
        """Incorporate new observation (delegated to inner planner)."""
        self._inner.update(observation)

    # ── Domain helpers ───────────────────────────────────────────────

    def _transition(self, state: Any, action: PlanningAction) -> Any:
        """Apply action to state.

        Override in subclasses for domain-specific dynamics.
        """
        return state

    def _is_terminal(self, state: Any, goal: PlanningGoal) -> bool:
        """Check if state satisfies the goal."""
        if self._domain and self._domain.is_terminal_fn:
            return self._domain.is_terminal_fn(state)
        return False

    def get_stats(self) -> Dict[str, Any]:
        stats = super().get_stats()
        stats["inner_planner"] = type(self._inner).__name__
        stats["horizon"] = self.config.horizon
        stats["total_steps"] = self._step
        return stats

