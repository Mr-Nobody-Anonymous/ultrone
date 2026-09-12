"""Reactive Planning architecture."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from .base import AIArchitecture, AIArchitectureConfig

logger = logging.getLogger("Ultrone.AIArchitectures.ReactivePlanning")


@dataclass
class ReactivePlanConfig(AIArchitectureConfig):
    """Configuration for Reactive Planner."""
    rule_based: bool = True


class ReactivePlanner(AIArchitecture):
    """Reactive Planning system.

    Uses a set of condition-action rules to map situations
    to actions without explicit search. Fast and predictable,
    suitable for time-critical tactical responses.
    """

    def __init__(self, config: Optional[ReactivePlanConfig] = None):
        super().__init__(config or ReactivePlanConfig())
        self._rules: List[Tuple[Callable[[Dict[str, Any]], bool], str]] = []

    def add_rule(self, condition: Callable[[Dict[str, Any]], bool], action: str) -> None:
        """Add a condition-action rule."""
        self._rules.append((condition, action))

    def decide(self, state: Dict[str, Any]) -> str:
        for condition, action in self._rules:
            if condition(state):
                self._last_action = action
                return action
        self._last_action = "idle"
        return "idle"

    def reset(self) -> None:
        pass
