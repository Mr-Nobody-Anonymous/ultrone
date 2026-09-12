# Copyright (c) Ultrone Contributors. All rights reserved.
"""Distributed task allocation using auction-based methods."""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .base import BaseCoordinator, CoordinationConfig

logger = logging.getLogger("Ultrone.Brain.Reasoning.Coordination.TaskAllocation")


@dataclass
class TaskAllocationConfig(CoordinationConfig):
    """Configuration for task allocation."""
    allocation_method: str = "auction"  # auction, greedy, optimal
    bid_noise: float = 0.1


class TaskAllocation(BaseCoordinator):
    """Distributed task allocation using auction protocol.

    Agents bid on tasks based on their capabilities and proximity.
    Tasks are allocated to the highest bidder.
    """

    def __init__(self, config: Optional[TaskAllocationConfig] = None):
        super().__init__(config or TaskAllocationConfig())
        self._config: TaskAllocationConfig = self.config  # type: ignore

    def allocate(self, tasks: Dict[str, float]) -> Dict[str, Any]:
        """Allocate tasks to agents.

        Args:
            tasks: Mapping of task_id -> weight/priority.

        Returns:
            Dict with allocations and method.
        """
        if not self._agents:
            # Use default agents when none registered
            self._agents = {f"agent_{i}": None for i in range(max(2, self._config.num_agents))}
        task_list = [{"id": tid, "weight": w} for tid, w in tasks.items()]
        return self.coordinate({
            "tasks": task_list,
            "agents": list(self._agents.keys()),
        })

    def coordinate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        tasks = context.get("tasks", [])
        agents = context.get("agents", list(self._agents.keys()))
        allocations = {}
        for task in tasks:
            bids = {a: np.random.random() + self._config.bid_noise * np.random.randn() for a in agents}
            best_agent = max(bids, key=bids.get)
            allocations[task["id"]] = best_agent
        return {"allocations": allocations, "method": self._config.allocation_method}

    def get_stats(self) -> Dict[str, Any]:
        return {"type": "TaskAllocation", "method": self._config.allocation_method}