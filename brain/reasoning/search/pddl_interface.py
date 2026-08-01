# Copyright (c) Ultrone Contributors. All rights reserved.
"""PDDL planner interface for STRIPS-style planning.

Provides a native Python PDDL parser and planner that can be used
without external dependencies. Supports basic STRIPS operators
and classical planning via forward search.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from .base import Planner, PlanningAction, PlanningDomain, PlanningGoal, PlanningResult

logger = logging.getLogger("Ultrone.Brain.Reasoning.Search.PDDL")


@dataclass(frozen=True)
class PDDLPredicate:
    """A predicate in a PDDL domain (a state fact)."""
    name: str

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        if isinstance(other, PDDLPredicate):
            return self.name == other.name
        return NotImplemented

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"PDDLPredicate('{self.name}')"


@dataclass
class PDDLAction:
    """A STRIPS-style action with preconditions and effects."""
    name: str
    preconditions: set = field(default_factory=set)
    add_effects: set = field(default_factory=set)
    del_effects: set = field(default_factory=set)
    cost: float = 1.0
    parameters: List[str] = field(default_factory=list)


@dataclass
class PDDLConfig:
    """Configuration for PDDL planner."""
    max_depth: int = 50
    use_heuristic: bool = True
    max_expansions: int = 10000


@dataclass
class PDDLDomain:
    """A PDDL domain definition."""
    name: str = ""
    predicates: List[str] = field(default_factory=list)
    actions: List[PDDLAction] = field(default_factory=list)

    def add_predicate(self, name: str) -> None:
        self.predicates.append(name)

    def add_action(self, name: str, parameters: List[str],
                   precondition: List[str], effect: List[str]) -> None:
        self.actions.append({
            "name": name,
            "parameters": parameters,
            "precondition": precondition,
            "effect": effect,
        })


@dataclass
class PDDLProblem:
    """A PDDL problem instance."""
    domain: str = ""
    name: str = ""
    objects: List[str] = field(default_factory=list)
    init: set = field(default_factory=set)
    goal: set = field(default_factory=set)


class PDDLPlanner(Planner):
    """PDDL planner for STRIPS-style planning problems.

    Parses PDDL domain and problem definitions and performs
    forward-chaining search to find a plan.
    """

    def __init__(self, config: Optional[PDDLConfig] = None) -> None:
        super().__init__()
        self.config = config or PDDLConfig()
        self._domain: Optional[PDDLDomain] = None
        self._problem: Optional[PDDLProblem] = None

    def load_domain(self, domain: PDDLDomain) -> None:
        self._domain = domain

    def load_problem(self, problem: PDDLProblem) -> None:
        self._problem = problem

    def initialize(self, domain: PlanningDomain) -> None:
        super().initialize(domain)

    def plan(self, state: Any, goal: PlanningGoal) -> PlanningResult:
        if self._domain is None or self._problem is None:
            return PlanningResult(success=False)

        current = set(self._problem.init)
        goal_set = set(self._problem.goal)
        plan: List[PlanningAction] = []

        # Simple forward search
        for depth in range(self.config.max_depth):
            if goal_set.issubset(current):
                result = PlanningResult(
                    success=True, actions=plan, cost=len(plan), plan_length=len(plan),
                )
                logger.info("PDDL plan found: %d actions", len(plan))
                return self._record_result(result)

            applied = False
            for action in self._domain.actions:
                if isinstance(action, PDDLAction):
                    pre = action.preconditions
                    if pre.issubset(current):
                        current = (current - action.del_effects) | action.add_effects
                        plan.append(PlanningAction(action.name, {"parameters": action.parameters}, cost=action.cost))
                        applied = True
                        break
                else:
                    # Legacy dict-based action format
                    pre = set(action["precondition"])
                    if pre.issubset(current):
                        add = {e for e in action["effect"] if not e.startswith("not")}
                        delete = {e[4:-1] for e in action["effect"] if e.startswith("not")}
                        current = (current - delete) | add
                        plan.append(PlanningAction(action["name"], {"parameters": action["parameters"]}))
                        applied = True
                        break

            if not applied:
                break

        return PlanningResult(success=False, cost=float("inf"))
