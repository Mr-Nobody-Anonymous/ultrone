# Copyright (c) Ultrone Contributors. All rights reserved.
"""Monte Carlo Tree Search (MCTS) planner.

MCTS is a best-first, rollout-based search algorithm that builds a
search tree incrementally by balancing exploration (UCB) against
exploitation of known good trajectories.

Integration
-----------
Plugs into :class:`~brain.reasoning.tactical_engine.TacticalEngine`
as any other :class:`Planner` implementation.  Replaces the existing
``MonteCarloEngine`` stub with a full algorithm.
"""

from __future__ import annotations

import logging
import math
import random
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from .base import Planner, PlanningAction, PlanningDomain, PlanningGoal, PlanningResult

logger = logging.getLogger("Ultrone.Brain.Reasoning.Search.MCTS")


@dataclass
class MCTSConfig:
    """Configuration for the MCTS planner.

    Attributes
    ----------
    num_simulations:
        Number of rollouts per ``plan()`` call.
    max_depth:
        Maximum tree depth before a node is treated as terminal.
    exploration_constant:
        UCB1 exploration parameter (higher = more exploration).
    rollout_policy:
        One of ``"random"``, ``"heuristic"``, or ``"mixed"``.
    discount_factor:
        Discount factor for future rewards (γ).
    time_budget_ms:
        Optional hard time limit per ``plan()`` call.
    temperature:
        Softmax temperature for action selection during rollouts.
    """
    num_simulations: int = 1_000
    max_depth: int = 50
    exploration_constant: float = 1.414  # √2
    rollout_policy: str = "mixed"
    discount_factor: float = 0.99
    time_budget_ms: float = 0.0
    temperature: float = 1.0


# ── Tree node ────────────────────────────────────────────────────────


@dataclass
class _MCTSNode:
    """A single node in the MCTS search tree."""
    state: Any
    action: Optional[PlanningAction] = None
    parent: Optional["_MCTSNode"] = None
    children: List["_MCTSNode"] = field(default_factory=list)
    visits: int = 0
    total_reward: float = 0.0
    untried_actions: List[PlanningAction] = field(default_factory=list)
    depth: int = 0

    @property
    def is_fully_expanded(self) -> bool:
        return len(self.untried_actions) == 0

    @property
    def mean_reward(self) -> float:
        return self.total_reward / max(1, self.visits)

    @property
    def ucb1(self) -> float:
        """Upper Confidence Bound (exploration bonus)."""
        if self.visits == 0:
            return float("inf")
        if self.parent is None:
            return self.mean_reward
        return self.mean_reward + math.sqrt(
            math.log(self.parent.visits + 1) / (self.visits + 1e-6)
        )


# ── MCTS Planner ─────────────────────────────────────────────────────


class MCTS(Planner):
    """Monte Carlo Tree Search planner.

    Parameters
    ----------
    config:
        Algorithm hyper-parameters (see :class:`MCTSConfig`).
    """

    def __init__(self, config: Optional[MCTSConfig] = None) -> None:
        super().__init__()
        self.config = config or MCTSConfig()
        self._root: Optional[_MCTSNode] = None
        self._simulate_fn: Optional[Callable] = None

    # ── Lifecycle ────────────────────────────────────────────────────

    def initialize(self, domain: PlanningDomain) -> None:
        super().initialize(domain)
        self._simulate_fn = self._build_simulator(domain)

    def _build_simulator(self, domain: PlanningDomain) -> Callable:
        """Create a simulation function from the domain description."""
        if domain.action_cost_fn is not None:
            return domain.action_cost_fn
        # Default: return a simple random-walk simulator
        return None

    # ── Core MCTS ────────────────────────────────────────────────────

    def plan(self, state: Any, goal: PlanningGoal) -> PlanningResult:
        """Run MCTS and return the best action sequence found.

        The algorithm follows the standard four-step loop:
        1. **Select**: traverse tree using UCB1 until a leaf is reached.
        2. **Expand**: add one child node for an untried action.
        3. **Simulate** (rollout): run a random/heuristic policy to a terminal state.
        4. **Backpropagate**: propagate the result up to the root.
        """
        domain = self._domain
        if domain is None:
            raise RuntimeError("MCTS not initialized — call .initialize() first.")

        self._root = _MCTSNode(
            state=state,
            untried_actions=list(domain.discrete_actions),
        )

        deadline = (
            time.monotonic_ns() + int(self.config.time_budget_ms * 1e6)
            if self.config.time_budget_ms > 0
            else None
        )

        nodes_expanded = 0
        for sim_idx in range(self.config.num_simulations):
            if deadline is not None and time.monotonic_ns() > deadline:
                logger.debug("MCTS time budget exhausted after %d sims.", sim_idx)
                break

            # 1. Select
            node = self._select(self._root)

            # 2. Expand
            if node.untried_actions and node.depth < self.config.max_depth:
                node = self._expand(node)
                nodes_expanded += 1

            # 3. Simulate
            reward = self._simulate(node, goal)

            # 4. Backpropagate
            self._backpropagate(node, reward)

        # Extract best plan from tree
        best_path = self._best_sequence(self._root)
        success = len(best_path) > 0

        result = PlanningResult(
            success=success,
            actions=best_path,
            cost=sum(a.cost for a in best_path),
            nodes_expanded=nodes_expanded,
            plan_length=len(best_path),
            metadata={
                "root_visits": self._root.visits,
                "root_value": self._root.mean_reward,
                "simulations_run": sim_idx + 1,
            },
        )
        logger.info(
            "MCTS plan: %s (len=%d, cost=%.2f, nodes=%d)",
            "FOUND" if success else "FAILED",
            result.plan_length,
            result.cost,
            nodes_expanded,
        )
        return self._record_result(result)

    # ── MCTS internals ───────────────────────────────────────────────

    def _select(self, node: _MCTSNode) -> _MCTSNode:
        """Traverse tree using UCB1 until an expandable node is found."""
        while node.is_fully_expanded and node.children:
            node = max(node.children, key=lambda c: c.ucb1)
        return node

    def _expand(self, node: _MCTSNode) -> _MCTSNode:
        """Add one new child node for an untried action."""
        action = node.untried_actions.pop(random.randint(0, len(node.untried_actions) - 1))
        next_state = self._transition(node.state, action)
        child = _MCTSNode(
            state=next_state,
            action=action,
            parent=node,
            depth=node.depth + 1,
        )
        node.children.append(child)
        return child

    def _simulate(self, node: _MCTSNode, goal: PlanningGoal) -> float:
        """Run a rollout from *node* to a terminal state and return discounted reward."""
        state = node.state
        total_reward = 0.0
        discount = 1.0
        depth = node.depth

        for step in range(self.config.max_depth - depth):
            # Terminal check
            if self._is_terminal(state, goal):
                break

            # Select action according to rollout policy
            if self.config.rollout_policy == "random":
                action = random.choice(self._domain.discrete_actions)
            elif self.config.rollout_policy == "heuristic":
                action = max(
                    self._domain.discrete_actions,
                    key=lambda a: self._reward_fn(state, a, goal),
                )
            else:  # mixed
                if random.random() < self.config.temperature:
                    action = random.choice(self._domain.discrete_actions)
                else:
                    action = max(
                        self._domain.discrete_actions,
                        key=lambda a: self._reward_fn(state, a, goal),
                    )

            state = self._transition(state, action)
            r = self._reward_fn(state, action, goal)
            total_reward += discount * r
            discount *= self.config.discount_factor

        return total_reward

    def _backpropagate(self, node: _MCTSNode, reward: float) -> None:
        """Propagate simulation reward up the tree to the root."""
        while node is not None:
            node.visits += 1
            node.total_reward += reward
            node = node.parent

    def _best_sequence(self, node: _MCTSNode) -> List[PlanningAction]:
        """Extract the action sequence with highest visit count from root."""
        actions: List[PlanningAction] = []
        while node.children:
            # Robust child selection: maximise visits (exploitation)
            best = max(node.children, key=lambda c: c.visits)
            if best.action is None:
                break
            actions.append(best.action)
            node = best
        return actions

    # ── Domain helpers ───────────────────────────────────────────────

    def _transition(self, state: Any, action: PlanningAction) -> Any:
        """Apply *action* to *state* and return successor state.

        Subclasses may override this for domain-specific dynamics.
        The default returns state unchanged (identity model).
        """
        return state

    def _reward_fn(self, state: Any, action: PlanningAction, goal: PlanningGoal) -> float:
        """Heuristic reward for being in *state* after taking *action*.

        Override in domain-specific subclasses.  Default returns negative
        action cost (minimisation).
        """
        return -action.cost

    def _is_terminal(self, state: Any, goal: PlanningGoal) -> bool:
        """Check if *state* satisfies the goal."""
        if self._domain and self._domain.is_terminal_fn:
            return self._domain.is_terminal_fn(state)
        return False

