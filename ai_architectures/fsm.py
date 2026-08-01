"""Finite State Machine architecture."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Union

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
        # Ensure the initial state is always available
        self.add_state(State(name=self.config.initial_state))
        self.initialize()

    def add_state(self, state: State) -> None:
        self._states[state.name] = state

    def add_transition(self, from_state: Union[str, Transition], to_state: str = "", condition: Optional[Callable] = None) -> None:
        """Add a transition between states.
        
        Can be called with a Transition object or with 3 positional args.
        """
        if isinstance(from_state, Transition):
            self._transitions.append(from_state)
            # Auto-register referenced states so the graph stays valid
            self._states.setdefault(from_state.from_state, State(name=from_state.from_state))
            self._states.setdefault(from_state.to_state, State(name=from_state.to_state))
        else:
            self._transitions.append(Transition(
                from_state=from_state,
                to_state=to_state,
                condition=condition,
            ))
            # Auto-register referenced states so the graph stays valid
            self._states.setdefault(from_state, State(name=from_state))
            self._states.setdefault(to_state, State(name=to_state))

    def initialize(self) -> None:
        initial = self._states.get(self.config.initial_state)
        if initial:
            self._current_state = initial
            if initial.on_enter:
                initial.on_enter()

    @staticmethod
    def _eval_condition(condition: Optional[Callable], state: Dict[str, Any]) -> bool:
        """Evaluate a transition condition.

        Supports callables, string keys (state lookup), booleans, and
        callables that accept (current_state_name, state).
        """
        if condition is None:
            return True
        if callable(condition):
            try:
                result = condition(state)
            except TypeError:
                try:
                    result = condition(state.get("state"))
                except Exception:
                    result = False
            return bool(result)
        if isinstance(condition, bool):
            return condition
        if isinstance(condition, str):
            return bool(state.get(condition) or state.get("state") == condition)
        return bool(condition)

    def decide(self, state: Dict[str, Any]) -> str:
        if self._current_state is None:
            self.initialize()
        if self._current_state is None:
            return "unknown"

        # Check transitions
        for t in self._transitions:
            if t.from_state == self._current_state.name and self._eval_condition(t.condition, state):
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

    def get_stats(self) -> Dict[str, Any]:
        stats = super().get_stats()
        stats["current_state"] = self.current_state
        stats["state_count"] = len(self._states)
        stats["transition_count"] = len(self._transitions)
        return stats

    def reset(self) -> None:
        self._current_state = None
        self.initialize()
