"""Belief–Desire–Intention (BDI) agent architecture."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set

from .base import AIArchitecture, AIArchitectureConfig

logger = logging.getLogger("Ultrone.AIArchitectures.BDI")


@dataclass
class Belief:
    """Agent's belief about the world state."""
    name: str
    value: Any = None
    confidence: float = 1.0


@dataclass
class Desire:
    """An agent's desire (goal)."""
    name: str
    priority: float = 1.0
    conditions: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Intention:
    """An agent's commitment to a plan of action."""
    name: str
    plan: List[str] = field(default_factory=list)
    progress: int = 0


@dataclass
class BDIConfig(AIArchitectureConfig):
    """Configuration for BDI agent."""
    max_intentions: int = 5


class BDIAgent(AIArchitecture):
    """Belief–Desire–Intention architecture.

    A cognitive architecture that reasons about:
    - **Beliefs**: What the agent knows about the world
    - **Desires**: What the agent wants to achieve
    - **Intentions**: What the agent is committed to doing

    Suitable for agents that need explicit reasoning about
    their own mental state (meta-cognition).
    """

    def __init__(self, config: Optional[BDIConfig] = None):
        super().__init__(config or BDIConfig())
        self._beliefs: Dict[str, Belief] = {}
        self._desires: List[Desire] = []
        self._intentions: List[Intention] = []

    def add_belief(self, belief: Belief) -> None:
        self._beliefs[belief.name] = belief

    def add_desire(self, desire: Desire) -> None:
        self._desires.append(desire)

    def update_belief(self, name: str, value: Any, confidence: float = 1.0) -> None:
        if name in self._beliefs:
            self._beliefs[name].value = value
            self._beliefs[name].confidence = confidence

    def decide(self, state: Dict[str, Any]) -> str:
        # Sort desires by priority
        self._desires.sort(key=lambda d: d.priority, reverse=True)

        # Check if current intention is still valid
        if self._intentions:
            current = self._intentions[0]
            if current.progress < len(current.plan):
                action = current.plan[current.progress]
                current.progress += 1
                self._last_action = action
                return action

        # Form new intention from highest priority achievable desire
        for desire in self._desires:
            if not self._intentions or len(self._intentions) < self.config.max_intentions:
                plan = self._create_plan(desire)
                if plan:
                    intention = Intention(name=desire.name, plan=plan, progress=0)
                    self._intentions.append(intention)
                    action = plan[0]
                    intention.progress = 1
                    self._last_action = action
                    return action

        self._last_action = "idle"
        return "idle"

    def _create_plan(self, desire: Desire) -> List[str]:
        """Create a plan to achieve a desire."""
        # Simplified plan creation
        return [f"achieve_{desire.name}_step1", f"achieve_{desire.name}_step2"]

    def reset(self) -> None:
        self._intentions.clear()
