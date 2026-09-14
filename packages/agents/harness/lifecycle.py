# Copyright (c) Ultrone Contributors. All rights reserved.
"""Universal Agent Lifecycle State Machine."""

from __future__ import annotations

import logging
import time
from typing import Callable, Dict, List, Optional, Set

from .schemas import LifecycleState

logger = logging.getLogger("Ultrone.Harness.Lifecycle")


class InvalidStateTransitionError(Exception):
    """Raised when an illegal lifecycle transition is attempted."""


class LifecycleStateMachine:
    """Manages universal state transitions with guardrails and auditing."""

    # Valid direct transitions
    TRANSITIONS: Dict[LifecycleState, Set[LifecycleState]] = {
        LifecycleState.CREATED: {LifecycleState.PLANNING, LifecycleState.CANCELLED, LifecycleState.FAILED},
        LifecycleState.PLANNING: {LifecycleState.READY, LifecycleState.EXECUTING, LifecycleState.FAILED, LifecycleState.CANCELLED},
        LifecycleState.READY: {LifecycleState.EXECUTING, LifecycleState.CANCELLED},
        LifecycleState.EXECUTING: {LifecycleState.OBSERVING, LifecycleState.VERIFYING, LifecycleState.RECOVERING, LifecycleState.FAILED, LifecycleState.CANCELLED},
        LifecycleState.OBSERVING: {LifecycleState.VERIFYING, LifecycleState.EXECUTING, LifecycleState.RECOVERING, LifecycleState.FAILED, LifecycleState.CANCELLED},
        LifecycleState.VERIFYING: {LifecycleState.COMPLETED, LifecycleState.RECOVERING, LifecycleState.FAILED, LifecycleState.CANCELLED},
        LifecycleState.RECOVERING: {LifecycleState.PLANNING, LifecycleState.EXECUTING, LifecycleState.FAILED, LifecycleState.CANCELLED},
        LifecycleState.COMPLETED: set(),
        LifecycleState.FAILED: set(),
        LifecycleState.CANCELLED: set(),
    }

    def __init__(self, initial_state: LifecycleState = LifecycleState.CREATED) -> None:
        self._current_state: LifecycleState = initial_state
        self._history: List[Dict[str, Any]] = [
            {"from": None, "to": initial_state.value, "timestamp": time.time(), "reason": "Initial creation"}
        ]
        self._listeners: List[Callable[[LifecycleState, LifecycleState, Optional[str]], None]] = []

    @property
    def current_state(self) -> LifecycleState:
        return self._current_state

    def can_transition_to(self, target_state: LifecycleState) -> bool:
        """Check if target state is a valid transition from current state."""
        return target_state in self.TRANSITIONS.get(self._current_state, set())

    def transition(self, target_state: LifecycleState, reason: Optional[str] = None) -> None:
        """Transition to a new lifecycle state if valid.

        Raises
        ------
        InvalidStateTransitionError
            If the transition is illegal from the current state.
        """
        if not self.can_transition_to(target_state):
            raise InvalidStateTransitionError(
                f"Illegal transition from {self._current_state.value} to {target_state.value}. "
                f"Allowed transitions: {[s.value for s in self.TRANSITIONS.get(self._current_state, set())]}"
            )

        previous_state = self._current_state
        self._current_state = target_state
        entry = {
            "from": previous_state.value,
            "to": target_state.value,
            "timestamp": time.time(),
            "reason": reason or "",
        }
        self._history.append(entry)
        logger.info("Lifecycle transition: %s -> %s (reason: %s)", previous_state.value, target_state.value, reason or "None")

        for listener in self._listeners:
            try:
                listener(previous_state, target_state, reason)
            except Exception as e:
                logger.warning("Error in lifecycle transition listener: %s", e)

    def add_listener(self, listener: Callable[[LifecycleState, LifecycleState, Optional[str]], None]) -> None:
        """Add a callback invoked on each transition."""
        self._listeners.append(listener)

    def get_history(self) -> List[Dict[str, Any]]:
        """Return audit history of state transitions."""
        return list(self._history)
