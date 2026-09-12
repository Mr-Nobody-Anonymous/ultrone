"""Goal-Oriented Action Planning architecture."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set

from .base import AIArchitecture, AIArchitectureConfig

logger = logging.getLogger("Ultrone.AIArchitectures.GOAP")


@dataclass
class GOAPConfig(AIArchitectureConfig):
    """Configuration for GOAP."""
    max_plan_depth: int = 10


@dataclass
class GOAPGoal:
    """A goal for the GOAP planner."""
    name: str
    conditions: Dict[str, Any]
    priority: float = 1.0


@dataclass
class GOAPAction:
    """An action for the GOAP planner."""
    name: str
    cost: float = 1.0
    preconditions: Dict[str, Any] = field(default_factory=dict)
    effects: Dict[str, Any] = field(default_factory=dict)
    duration: float = 0.0


class GOAP(AIArchitecture):
    """Goal-Oriented Action Planning.

    Plans a sequence of actions to achieve a goal by
    searching through action effects backwards from the goal state.
    """

    def __init__(self, config: Optional[GOAPConfig] = None):
        super().__init__(config or GOAPConfig())
        self._actions: Dict[str, GOAPAction] = {}
        self._goals: List[GOAPGoal] = []
        self._current_plan: List[GOAPAction] = []

    def register_action(self, action: GOAPAction) -> None:
        self._actions[action.name] = action

    def register_goal(self, goal: GOAPGoal) -> None:
        self._goals.append(goal)

    def decide(self, state: Dict[str, Any]) -> str:
        if not self._current_plan:
            # Find best achievable goal
            self._goals.sort(key=lambda g: g.priority, reverse=True)
            for goal in self._goals:
                if self._find_plan(state, goal):
                    break
            if not self._current_plan:
                return "idle"

        next_action = self._current_plan.pop(0)
        self._last_action = next_action.name
        return next_action.name

    def _find_plan(self, state: Dict[str, Any], goal: GOAPGoal) -> bool:
        """A* search for plan achieving the goal."""
        self._current_plan = []
        # Simplified: check if any action directly achieves a goal condition
        for action in self._actions.values():
            if all(k in action.effects and action.effects[k] == v for k, v in goal.conditions.items()):
                self._current_plan = [action]
                return True
        return False

    def reset(self) -> None:
        self._current_plan.clear()
