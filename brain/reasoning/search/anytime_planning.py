# Copyright (c) Ultrone Contributors. All rights reserved.
"""Anytime Planning wrapper.

Anytime planners return a first (quick) solution immediately and then
continue improving it as additional computation time is available.
This wrapper can be applied to any :class:`Planner` that supports
incremental improvement.

Integration
-----------
Wraps any :class:`Planner` implementation:

    planner = AnytimePlanner(MCTS(config=MCTSConfig(num_simulations=100)))
    result = planner.plan(state, goal)  # returns after 100 sims
    better = planner.plan(state, goal)  # continues with 100 more sims
"""

from __future__ import annotations

import copy
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .base import Planner, PlanningAction, PlanningDomain, PlanningGoal, PlanningResult

logger = logging.getLogger("Ultrone.Brain.Reasoning.Search.Anytime")


@dataclass
class AnytimeConfig:
    """Configuration for the Anytime wrapper.

    Attributes
    ----------
    time_budget_ms:
        Hard time limit for the entire anytime process (0 = unlimited).
    improvement_threshold:
        Stop improving if relative improvement drops below this.
    max_iterations:
        Maximum refinement iterations.
    """
    time_budget_ms: float = 5000.0
    improvement_threshold: float = 0.01
    max_iterations: int = 50


class AnytimePlanner(Planner):
    """Anytime wrapper that improves plans incrementally.

    Parameters
    ----------
    planner:
        The underlying planner to wrap.  It must support repeated
        ``plan()`` calls that produce increasingly better solutions.
    config:
        Anytime hyper-parameters.
    """

    def __init__(
        self,
        planner: Planner,
        config: Optional[AnytimeConfig] = None,
    ) -> None:
        super().__init__()
        self._inner = planner
        self.config = config or AnytimeConfig()
        self._best_result: Optional[PlanningResult] = None
        self._current_state: Any = None
        self._current_goal: Optional[PlanningGoal] = None

    def initialize(self, domain: PlanningDomain) -> None:
        super().initialize(domain)
        self._inner.initialize(domain)

    def plan(self, state: Any, goal: PlanningGoal) -> PlanningResult:
        """Return the best plan found within the time budget.

        The first call returns a possibly suboptimal plan quickly.
        Subsequent calls (with the same state and goal) continue
        refining the plan.
        """
        deadline = (
            time.monotonic_ns() + int(self.config.time_budget_ms * 1e6)
            if self.config.time_budget_ms > 0
            else None
        )

        # If state changed, reset
        if state != self._current_state or goal != self._current_goal:
            self._best_result = None
            self._current_state = state
            self._current_goal = goal

        best_cost = self._best_result.cost if self._best_result else float("inf")

        for iteration in range(self.config.max_iterations):
            if deadline is not None and time.monotonic_ns() > deadline:
                logger.debug("Anytime time budget exhausted at iteration %d.", iteration)
                break

            result = self._inner.plan(state, goal)

            if result.success and result.cost < best_cost:
                improvement = (best_cost - result.cost) / best_cost if best_cost < float("inf") else 1.0
                best_cost = result.cost
                self._best_result = result
                logger.info(
                    "Anytime iteration %d: improved to cost=%.2f (improvement=%.1f%%)",
                    iteration, result.cost, improvement * 100,
                )
                if improvement < self.config.improvement_threshold:
                    logger.debug("Anytime converged at iteration %d.", iteration)
                    break
            else:
                break  # no further improvement

        result = self._best_result or PlanningResult(success=False)
        return self._record_result(result)

    def update(self, observation: Any) -> None:
        self._inner.update(observation)

    def get_stats(self) -> Dict[str, Any]:
        stats = super().get_stats()
        stats["inner_planner"] = type(self._inner).__name__
        if self._best_result:
            stats["best_cost"] = self._best_result.cost
            stats["best_length"] = self._best_result.plan_length
        return stats

