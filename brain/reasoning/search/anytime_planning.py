# Copyright (c) Ultrone Contributors. All rights reserved.
"""Anytime planning wrapper that improves plan quality over time."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from .base import Planner, PlanningAction, PlanningDomain, PlanningGoal, PlanningResult

logger = logging.getLogger("Ultrone.Brain.Reasoning.Search.Anytime")


@dataclass
class AnytimeConfig:
    """Configuration for anytime planning."""
    max_time_ms: float = 5000.0
    improvement_threshold: float = 0.05
    time_budget_ms: Optional[float] = None
    max_iterations: Optional[int] = None

    def __post_init__(self):
        if self.time_budget_ms is not None:
            self.max_time_ms = self.time_budget_ms


class AnytimePlanner(Planner):
    """Anytime planning wrapper.

    Wraps any Planner and allows it to run for a configurable time budget,
    continuously improving the plan quality. The planner is called
    repeatedly with increasing constraints to find better solutions.
    """

    def __init__(self, inner_planner: Optional[Planner] = None,
                 config: Optional[AnytimeConfig] = None) -> None:
        super().__init__()
        self.inner_planner = inner_planner
        self.config = config or AnytimeConfig()

    def set_inner_planner(self, planner: Planner) -> None:
        self.inner_planner = planner

    def initialize(self, domain: PlanningDomain) -> None:
        super().initialize(domain)
        if self.inner_planner:
            self.inner_planner.initialize(domain)

    def plan(self, state: Any, goal: PlanningGoal) -> PlanningResult:
        if self.inner_planner is None:
            return PlanningResult(success=False)

        best_result = PlanningResult(success=False, cost=float("inf"))
        timeout = time.time() + self.config.max_time_ms / 1000.0

        iteration = 0
        while time.time() < timeout:
            result = self.inner_planner.plan(state, goal)
            if result.success and result.cost < best_result.cost:
                improvement = (best_result.cost - result.cost) / best_result.cost if best_result.cost < float("inf") else 1.0
                best_result = result
                if improvement < self.config.improvement_threshold and iteration > 0:
                    break
            iteration += 1

        logger.info("Anytime planner: %d iterations, best cost=%.2f", iteration, best_result.cost)
        if best_result.success:
            return self._record_result(best_result)
        return best_result
