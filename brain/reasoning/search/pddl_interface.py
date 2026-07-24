# Copyright (c) Ultrone Contributors. All rights reserved.
"""STRIPS/PDDL grounded planning interface.

This module provides a planner that operates on a grounded (propositional)
STRIPS representation.  The user defines actions in terms of preconditions
and effects as sets of predicates.  The planner performs forward state-space
search with heuristic guidance.

For true PDDL file parsing, integrate an external parser (e.g. ``tarski``,
``pyperplan``, or ``unified_planning``).  This implementation works directly
with in-memory domain descriptions.

Integration
-----------
Plugs into :class:`~brain.reasoning.tactical_engine.TacticalEngine`
as any other :class:`Planner` implementation.
"""

from __future__ import annotations

import heapq
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, FrozenSet, List, Optional, Set, Tuple

from .base import Planner, PlanningAction, PlanningDomain, PlanningGoal, PlanningResult

logger = logging.getLogger("Ultrone.Brain.Reasoning.Search.PDDL")


# ── PDDL types ───────────────────────────────────────────────────────


@dataclass(frozen=True)
class PDDLPredicate:
    """A logical predicate: ``name(arg1, arg2, ...)``."""
    name: str
    args: Tuple[str, ...] = ()

    def __str__(self) -> str:
        if self.args:
            return f"{self.name}({', '.join(self.args)})"
        return self.name


@dataclass
class PDDLAction:
    """A grounded STRIPS action.

    Attributes
    ----------
    name:
        Action name.
    preconditions:
        Set of predicates that must be True before execution.
    add_effects:
        Predicates made True by the action.
    del_effects:
        Predicates made False by the action.
    cost:
        Action cost.
    """
    name: str
    preconditions: Set[PDDLPredicate] = field(default_factory=set)
    add_effects: Set[PDDLPredicate] = field(default_factory=set)
    del_effects: Set[PDDLPredicate] = field(default_factory=set)
    cost: float = 1.0


@dataclass
class PDDLDomain:
    """A STRIPS planning domain.

    Attributes
    ----------
    name:
        Domain name.
    actions:
        All available grounded actions.
    predicates:
        All possible predicates in the domain.
    """
    name: str = "ultrone_domain"
    actions: List[PDDLAction] = field(default_factory=list)
    predicates: Set[PDDLPredicate] = field(default_factory=set)

    def add_action(self, action: PDDLAction) -> None:
        self.actions.append(action)
        self.predicates.update(action.preconditions)
        self.predicates.update(action.add_effects)
        self.predicates.update(action.del_effects)


@dataclass
class PDDLProblem:
    """A specific planning problem.

    Attributes
    ----------
    name:
        Problem name.
    domain:
        The domain this problem belongs to.
    init:
        Set of predicates true in the initial state.
    goal:
        Set of predicates that must be true in the goal state.
    """
    name: str = "ultrone_problem"
    domain: Optional[PDDLDomain] = None
    init: Set[PDDLPredicate] = field(default_factory=set)
    goal: Set[PDDLPredicate] = field(default_factory=set)


@dataclass
class PDDLConfig:
    """Configuration for the PDDL planner.

    Attributes
    ----------
    max_expansions:
        Maximum state expansions.
    use_goal_count_heuristic:
        If True, heuristic = number of goal predicates not yet achieved.
    """
    max_expansions: int = 100_000
    use_goal_count_heuristic: bool = True


# ── PDDL Planner ─────────────────────────────────────────────────────


class PDDLPlanner(Planner):
    """Ground forward-state-space STRIPS planner.

    Parameters
    ----------
    config:
        Hyper-parameters (see :class:`PDDLConfig`).
    """

    def __init__(self, config: Optional[PDDLConfig] = None) -> None:
        super().__init__()
        self.config = config or PDDLConfig()
        self._domain: Optional[PDDLDomain] = None

    # ── Load domain ──────────────────────────────────────────────────

    def initialize(self, domain: PlanningDomain) -> None:
        # Convert generic PlanningDomain to PDDLDomain if possible
        super().initialize(domain)
        if hasattr(domain, "actions"):
            self._domain = domain  # type: ignore[assignment]
        else:
            # Build default empty domain
            self._domain = PDDLDomain()

    def load_domain(self, pddl_domain: PDDLDomain) -> None:
        """Explicitly set the PDDL domain."""
        self._domain = pddl_domain

    def load_problem(self, problem: PDDLProblem) -> None:
        """Set the current planning problem."""
        self._problem = problem
        if problem.domain:
            self._domain = problem.domain

    # ── Core planning ────────────────────────────────────────────────

    def plan(self, state: Any, goal: PlanningGoal) -> PlanningResult:
        """Search for a sequence of actions that achieves the goal.

        The action sequence is guaranteed to be executable in the
        initial state under the STRIPS semantics.
        """
        domain = self._domain
        if domain is None:
            raise RuntimeError("PDDLPlanner not initialised — call .load_domain() or .initialize() first.")

        # Convert state to a set of predicates
        init_set: Set[PDDLPredicate] = self._state_to_predicates(state)
        goal_set: Set[PDDLPredicate] = self._goal_to_predicates(goal)

        # A* search over state space
        open_set: List[Tuple[float, int, FrozenSet[PDDLPredicate]]] = []
        initial_frozen = frozenset(init_set)
        start_h = self._heuristic(init_set, goal_set)

        heapq.heappush(open_set, (start_h, 0, initial_frozen))
        came_from: Dict[FrozenSet[PDDLPredicate], FrozenSet[PDDLPredicate]] = {}
        action_map: Dict[FrozenSet[PDDLPredicate], PDDLAction] = {}
        g_score: Dict[FrozenSet[PDDLPredicate], float] = {initial_frozen: 0.0}

        expansions = 0
        _ctr = 0

        while open_set and expansions < self.config.max_expansions:
            expansions += 1
            _, _, current_frozen = heapq.heappop(open_set)
            current_set = set(current_frozen)

            # Goal check
            if goal_set.issubset(current_set):
                plan_actions = self._reconstruct_plan(
                    initial_frozen, current_frozen, came_from, action_map, domain,
                )
                logger.info("PDDL plan found: %d actions after %d expansions", len(plan_actions), expansions)
                return PlanningResult(
                    success=True,
                    actions=plan_actions,
                    cost=g_score.get(current_frozen, 0.0),
                    nodes_expanded=expansions,
                    plan_length=len(plan_actions),
                )

            # Expand actions
            for action in domain.actions:
                if action.preconditions.issubset(current_set):
                    new_set = (current_set - action.del_effects) | action.add_effects
                    new_frozen = frozenset(new_set)
                    tentative = g_score[current_frozen] + action.cost
                    if tentative < g_score.get(new_frozen, float("inf")):
                        g_score[new_frozen] = tentative
                        h = self._heuristic(new_set, goal_set)
                        _ctr += 1
                        heapq.heappush(open_set, (tentative + h, _ctr, new_frozen))
                        came_from[new_frozen] = current_frozen
                        action_map[new_frozen] = action

        return PlanningResult(
            success=False,
            cost=float("inf"),
            nodes_expanded=expansions,
            metadata={"reason": "exhausted_search"},
        )

    # ── Helpers ──────────────────────────────────────────────────────

    def _heuristic(
        self,
        state: Set[PDDLPredicate],
        goal: Set[PDDLPredicate],
    ) -> float:
        """Goal-count heuristic: number of goal predicates not achieved."""
        if not self.config.use_goal_count_heuristic:
            return 0.0
        return float(len(goal - state))

    def _state_to_predicates(self, state: Any) -> Set[PDDLPredicate]:
        """Convert a generic state to a set of PDDL predicates.

        Override in subclasses for domain-specific grounding.
        Default: treat all dict keys as unary predicates.
        """
        if isinstance(state, dict):
            return {PDDLPredicate(k) for k in state if state[k]}
        if isinstance(state, set):
            return state  # already predicates
        return set()

    def _goal_to_predicates(self, goal: PlanningGoal) -> Set[PDDLPredicate]:
        """Convert a PlanningGoal to a set of PDDL predicates."""
        return {PDDLPredicate(k, tuple(v) if isinstance(v, (list, tuple)) else (str(v),))
                for k, v in goal.predicates.items()}

    def _reconstruct_plan(
        self,
        start: FrozenSet[PDDLPredicate],
        goal_state: FrozenSet[PDDLPredicate],
        came_from: Dict[FrozenSet[PDDLPredicate], FrozenSet[PDDLPredicate]],
        action_map: Dict[FrozenSet[PDDLPredicate], PDDLAction],
        domain: PDDLDomain,
    ) -> List[PlanningAction]:
        """Reconstruct the action sequence from the search tree."""
        actions: List[PlanningAction] = []
        current = goal_state
        while current in came_from:
            pddl_action = action_map.get(current)
            if pddl_action:
                actions.append(
                    PlanningAction(
                        name=pddl_action.name,
                        cost=pddl_action.cost,
                    )
                )
            current = came_from[current]
        actions.reverse()
        return actions

    def get_stats(self) -> Dict[str, Any]:
        stats = super().get_stats()
        stats["num_actions"] = len(self._domain.actions) if self._domain else 0
        stats["num_predicates"] = len(self._domain.predicates) if self._domain else 0
        return stats

