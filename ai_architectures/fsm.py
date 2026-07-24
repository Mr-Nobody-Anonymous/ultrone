"""Finite State Machine architecture."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set

from .base import AIArchitecture, AIArchitectureConfig

logger = logging.getLogger("Ultrone.AIArchitectures.FSM")


@dataclass
class FSMConfig(AIArchitectureConfig):
    """Configuration for FSM."""
    initial_state: str = "idle"


@dataclass
class State:
    """A state in the FSM."""
    name: str
    on_enter: Optional[Callable] = None
    on_exit: Optional[Callable] = None
    on_update: Optional[Callable] = None


@dataclass
class Transition:
    """A transition between states."""
    from_state: str
    to_state: str
    condition: Callable[[Dict[str, Any]], bool]


class FSM(AIArchitecture):
    """Finite State Machine for agent behavior control.

    Supports deterministic state transitions with entry/exit
    callbacks. Suitable for well-defined tactical procedures.
    """

    def __init__(self, config: Optional[FSMConfig] = None):
        super().__init__(config or FSMConfig())
        self._states: Dict[str, State] = {}
        self._transitions: List[Transition] = []
        self._current_state: Optional[State] = None

    def add_state(self, state: State) -> None:
        self._states[state.name] = state

    def add_transition(self, transition: Transition) -> None:
        self._transitions.append(transition)

    def initialize(self) -> None:
        initial = self._states.get(self.config.initial_state)
        if initial:
            self._current_state = initial
            if initial.on_enter:
                initial.on_enter()

    def decide(self, state: Dict[str, Any]) -> str:
        if self._current_state is None:
            return "unknown"

        # Check transitions
        for t in self._transitions:
            if t.from_state == self._current_state.name and t.condition(state):
                # Transition
                if self._current_state.on_exit:
                    self._current_state.on_exit()
                self._current_state = self._states.get(t.to_state)
                if self._current_state and self._current_state.on_enter:
                    self._current_state.on_enter()
                self._last_action = t.to_state
                return t.to_state

        # Stay in current state
        if self._current_state.on_update:
            self._current_state.on_update()
        self._last_action = self._current_state.name
        return self._current_state.name

    @property
    def current_state(self) -> Optional[str]:
        return self._current_state.name if self._current_state else None

    def reset(self) -> None:
        self._current_state = None
        self.initialize()
