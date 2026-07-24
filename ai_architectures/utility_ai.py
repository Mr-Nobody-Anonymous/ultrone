"""Utility AI architecture for nuanced decision-making."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from .base import AIArchitecture, AIArchitectureConfig

logger = logging.getLogger("Ultrone.AIArchitectures.UtilityAI")


@dataclass
class Consideration:
    """A single factor in utility calculation."""
    name: str
    weight: float = 1.0
    curve_fn: Callable[[float], float] = lambda x: x  # default linear


@dataclass
class Option:
    """An action option with associated considerations."""
    name: str
    considerations: List[Consideration] = field(default_factory=list)


@dataclass
class UtilityAIConfig(AIArchitectureConfig):
    """Configuration for Utility AI."""


class UtilityAI(AIArchitecture):
    """Utility-based AI for nuanced decision-making.

    Scores each action option based on weighted considerations,
    selecting the highest-utility action. Useful for natural-looking
    agent behavior with smooth transitions.
    """

    def __init__(self, config: Optional[UtilityAIConfig] = None):
        super().__init__(config or UtilityAIConfig())
        self._options: Dict[str, Option] = {}

    def add_option(self, option: Option) -> None:
        self._options[option.name] = option

    def decide(self, state: Dict[str, Any]) -> str:
        best_option = None
        best_score = float("-inf")

        for name, option in self._options.items():
            score = 0.0
            total_weight = 0.0
            for c in option.considerations:
                raw = state.get(c.name, 0.0)
                curved = c.curve_fn(raw)
                score += c.weight * curved
                total_weight += c.weight

            utility = score / total_weight if total_weight > 0 else 0.0
            if utility > best_score:
                best_score = utility
                best_option = name

        self._last_action = best_option or "idle"
        return self._last_action

    def reset(self) -> None:
        pass
