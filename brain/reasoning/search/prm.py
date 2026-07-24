"""PRM: Probabilistic Roadmap for multi-query motion planning."""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from .base import Planner, PlanningDomain, PlanningGoal, PlanningResult, PlanningAction

logger = logging.getLogger("Ultrone.Brain.Reasoning.Search.PRM")


@dataclass
class PRMConfig:
    """Configuration for PRM planning."""
    n_samples: int = 500
    k_neighbors: int = 10
    connection_radius: float = 15.0


class PRMPlanner(Planner):
    """Probabilistic Roadmap (PRM) for multi-query planning.

    PRM builds a graph of feasible configurations in configuration
    space, then uses graph search (A*) to find paths. Efficient for
    multiple queries in the same environment.

    Use cases in ULTRONE:
    - Repeated path planning in static environments
    - Swarm coordination with shared roadmap
    - Airspace deconfliction
    """

    def __init__(self, config: Optional[PRMConfig] = None):
        super().__init__()
        self.config = config or PRMConfig()
        self._roadmap: Dict[int, List[int]] = {}
        self._nodes: List[np.ndarray] = []
        self._built = False
        self._collision_fn: Optional[Callable] = None

    def initialize(self, domain: PlanningDomain) -> None:
        super().initialize(domain)

    def build_roadmap(self, bounds: List[Tuple[float, float]]) -> None:
        """Build the probabilistic roadmap."""
        dim = len(bounds)
        self._nodes = []
        for _ in range(self.config.n_samples):
            node = np.array([np.random.uniform(b[0], b[1]) for b in bounds])
            if self._collision_fn and self._collision_fn(node):
                continue
            self._nodes.append(node)

        # Connect k-nearest neighbors
        self._roadmap = {i: [] for i in range(len(self._nodes))}
        for i in range(len(self._nodes)):
            dists = [(j, np.linalg.norm(self._nodes[i] - self._nodes[j]))
                      for j in range(len(self._nodes)) if j != i]
            dists.sort(key=lambda x: x[1])
            for j, d in dists[:self.config.k_neighbors]:
                if d < self.config.connection_radius:
                    self._roadmap[i].append(j)
                    self._roadmap[j].append(i)

        self._built = True
        logger.info("PRM roadmap built: %d nodes, %d edges", len(self._nodes),
                     sum(len(v) for v in self._roadmap.values()) // 2)

    def plan(self, state: np.ndarray, goal: PlanningGoal) -> PlanningResult:
        """Plan using the pre-built roadmap + A* search."""
        if not self._built:
            return PlanningResult(success=False)

        start = np.array(state)
        goal_pos = np.array(goal.target_state) if goal.target_state is not None else state

        start_idx = np.argmin([np.linalg.norm(n - start) for n in self._nodes])
        goal_idx = np.argmin([np.linalg.norm(n - goal_pos) for n in self._nodes])

        # A* on roadmap
        import heapq
        pq = [(0.0, start_idx, [start_idx])]
        visited = set()
        g_costs = {start_idx: 0.0}

        while pq:
            f, current, path = heapq.heappop(pq)
            if current == goal_idx:
                actions = [PlanningAction(name="move", parameters={"position": self._nodes[i].tolist()}) for i in path]
                total_cost = sum(np.linalg.norm(self._nodes[path[i+1]] - self._nodes[path[i]]) for i in range(len(path)-1))
                return PlanningResult(success=True, actions=actions, cost=total_cost,
                                       nodes_expanded=len(path), plan_length=len(path))
            if current in visited:
                continue
            visited.add(current)

            for neighbor in self._roadmap.get(current, []):
                edge_cost = np.linalg.norm(self._nodes[neighbor] - self._nodes[current])
                g = g_costs[current] + edge_cost
                if neighbor not in g_costs or g < g_costs[neighbor]:
                    g_costs[neighbor] = g
                    h = np.linalg.norm(self._nodes[neighbor] - goal_pos)
                    heapq.heappush(pq, (g + h, neighbor, path + [neighbor]))

        return PlanningResult(success=False)

    def set_collision_fn(self, fn: Callable) -> None:
        self._collision_fn = fn

    def get_stats(self) -> Dict[str, Any]:
        return {**super().get_stats(), "nodes": len(self._nodes), "built": self._built}
