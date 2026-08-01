# Copyright (c) Ultrone Contributors. All rights reserved.
"""Receding Horizon Control (RHC) planner for real-time planning."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from .base import Planner, PlanningAction, PlanningDomain, PlanningGoal, PlanningResult

logger = logging.getLogger("Ultrone.Brain.Reasoning.Search.RHC")


@dataclass
class RecedingHorizonConfig:
    """Configuration for Receding Horizon Control."""
    horizon: int = 5
    plan_frequency: int = 1
    receding_step: int = 1
    max_total_steps: int = 50


class RecedingHorizonPlanner(Planner):
    """Receding Horizon Control planner.

    Plans only for a limited horizon ahead, executes the first action,
    then replans. This reduces computational cost for real-time
    applications while maintaining adaptive behavior.
    """

    def __init__(self, inner_planner: Optional[Planner] = None,
                 config: Optional[RecedingHorizonConfig] = None) -> None:
        super().__init__()
        self.inner_planner = inner_planner
        self.config = config or RecedingHorizonConfig()

    def set_inner_planner(self, planner: Planner) -> None:
        self.inner_planner = planner

    def initialize(self, domain: PlanningDomain) -> None:
        super().initialize(domain)
        if self.inner_planner:
            self.inner_planner.initialize(domain)

    def plan(self, state: Any, goal: PlanningGoal) -> PlanningResult:
        if self.inner_planner is None:
            return PlanningResult(success=False)

        # Create a subgoal limited by horizon
        horizon_goal = PlanningGoal(
            description=goal.description,
            target_state=goal.target_state,
            tolerance=goal.tolerance,
        )

        full_result = self.inner_planner.plan(state, horizon_goal)
        if not full_result.success:
            return full_result

        # Truncate to horizon
        horizon_actions = full_result.actions[:self.config.horizon]
        truncated_cost = sum(a.cost for a in horizon_actions)

        result = PlanningResult(
            success=len(horizon_actions) > 0,
            actions=horizon_actions,
            cost=truncated_cost,
            nodes_expanded=full_result.nodes_expanded,
            plan_length=len(horizon_actions),
            metadata={"full_plan_length": len(full_result.actions)},
        )
        logger.info("RHC plan: %d actions (horizon %d)", result.plan_length, self.config.horizon)
        return self._record_result(result)
