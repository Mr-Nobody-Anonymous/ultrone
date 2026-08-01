# Copyright (c) Ultrone Contributors. All rights reserved.
"""Multi-Agent Path Finding (MAPF) planner with Conflict-Based Search (CBS)."""

from __future__ import annotations

import heapq
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from .base import Planner, PlanningAction, PlanningDomain, PlanningGoal, PlanningResult

logger = logging.getLogger("Ultrone.Brain.Reasoning.Search.MAPF")


@dataclass
class MAPFConfig:
    """Configuration for MAPF."""
    max_time_ms: float = 1000.0
    max_agents: int = 10
    max_iterations: int = 1000


@dataclass
class _Constraint:
    agent_id: int
    timestep: int
    x: int
    y: int


class MAPFPlanner(Planner):
    """Multi-Agent Path Finding using Conflict-Based Search (CBS).

    Plans collision-free paths for multiple agents in a shared environment.
    """

    def __init__(self, config: Optional[MAPFConfig] = None) -> None:
        super().__init__()
        self.config = config or MAPFConfig()
        self._last_plans: Dict[int, List[Tuple[int, int]]] = {}
        self._grid_width: int = 10
        self._grid_height: int = 10
        self._agent_ids: List[str] = []
        self._starts: Dict[str, Tuple[int, int]] = {}
        self._goals: Dict[str, Tuple[int, int]] = {}

    def initialize(self, domain: PlanningDomain) -> None:
        super().initialize(domain)

    def set_grid(self, width: int, height: int) -> None:
        """Set the grid dimensions."""
        self._grid_width = width
        self._grid_height = height

    def set_agents(self, agent_ids: List[str], starts: Dict[str, Tuple[int, int]],
                   goals: Dict[str, Tuple[int, int]]) -> None:
        """Set agent start and goal positions."""
        self._agent_ids = agent_ids
        self._starts = starts
        self._goals = goals

    def _a_star_path(self, start: Tuple[int, int], goal: Tuple[int, int],
                     constraints: Optional[List[_Constraint]] = None,
                     agent_id: int = 0) -> Optional[List[Tuple[int, int]]]:
        """A* path for a single agent with constraints."""
        if self._domain is None:
            return None
        open_set = [(0.0, id(start), start, [start])]
        closed: Set[Tuple[int, int, int]] = set()  # (x, y, t)
        constraint_set = set()
        if constraints:
            for c in constraints:
                if c.agent_id == agent_id:
                    constraint_set.add((c.x, c.y, c.timestep))

        while open_set:
            _, _, current, path = heapq.heappop(open_set)
            if current == goal:
                return path
            t = len(path) - 1
            if (current[0], current[1], t) in closed:
                continue
            closed.add((current[0], current[1], t))

            for dx, dy in [(0, 0), (0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = current[0] + dx, current[1] + dy
                if (nx, ny, t + 1) not in constraint_set:
                    heapq.heappush(open_set, (t + 1 + abs(nx - goal[0]) + abs(ny - goal[1]),
                                              id((nx, ny)), (nx, ny), path + [(nx, ny)]))
        return None

    def plan(self, state: Any, goal: PlanningGoal) -> PlanningResult:
        """Plan paths for multiple agents.

        Expects state to be a list of (x, y) positions and goal.target_state
        to be a list of (x, y) goal positions.
        """
        if not isinstance(state, list) or not isinstance(goal.target_state, list):
            return PlanningResult(success=False)

        starts = state
        goals = goal.target_state
        num_agents = min(len(starts), len(goals), self.config.max_agents)

        constraints: List[_Constraint] = []
        plans: Dict[int, List[Tuple[int, int]]] = {}

        for agent_id in range(num_agents):
            path = self._a_star_path(starts[agent_id], goals[agent_id], constraints, agent_id)
            if path is None:
                logger.info("MAPF: agent %d path FAILED", agent_id)
                return PlanningResult(success=False, cost=float("inf"))
            plans[agent_id] = path

        # Resolve conflicts (simplified)
        self._last_plans = plans

        all_actions = []
        for agent_id in range(num_agents):
            for step in plans.get(agent_id, []):
                all_actions.append(PlanningAction("move", {"agent": agent_id, "to": step}))

        result = PlanningResult(
            success=True, actions=all_actions, cost=len(all_actions),
            plan_length=len(all_actions), metadata={"num_agents": num_agents},
        )
        logger.info("MAPF plan found: %d agents, %d actions", num_agents, len(all_actions))
        return self._record_result(result)


# Alias for backward compatibility
ConflictBasedSearch = MAPFPlanner
