"""ULTRONE Device Interface Standard (UDIS) - 10-State Device State Machine.

Implements MHS-aligned explicit state machine preventing generic boolean state inference.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set


class DeviceState(str, Enum):
    """Explicit 10-state machine for all UDIS hardware and digital twins."""
    DISCOVERING = "DISCOVERING"
    READY = "READY"
    DEGRADED = "DEGRADED"
    BUSY = "BUSY"
    PAUSED = "PAUSED"
    FAULT = "FAULT"
    EMERGENCY_STOP = "EMERGENCY_STOP"
    OFFLINE = "OFFLINE"
    MAINTENANCE = "MAINTENANCE"
    SIMULATION = "SIMULATION"


class InvalidStateTransitionError(Exception):
    """Raised when an illegal device state transition is attempted."""
    pass


@dataclass(frozen=True)
class DeviceStateTransition:
    """Immutable record of state transition with provenance."""
    device_id: str
    from_state: DeviceState
    to_state: DeviceState
    timestamp: float
    reason: str
    authorized_by: str


class DeviceStateMachine:
    """State machine governing device lifecycle and enforcing valid transition guards."""

    # Explicit allowed transitions table
    _ALLOWED_TRANSITIONS: Dict[DeviceState, Set[DeviceState]] = {
        DeviceState.DISCOVERING: {
            DeviceState.READY,
            DeviceState.SIMULATION,
            DeviceState.FAULT,
            DeviceState.OFFLINE,
        },
        DeviceState.READY: {
            DeviceState.BUSY,
            DeviceState.DEGRADED,
            DeviceState.PAUSED,
            DeviceState.FAULT,
            DeviceState.EMERGENCY_STOP,
            DeviceState.OFFLINE,
            DeviceState.MAINTENANCE,
        },
        DeviceState.SIMULATION: {
            DeviceState.BUSY,
            DeviceState.PAUSED,
            DeviceState.FAULT,
            DeviceState.EMERGENCY_STOP,
            DeviceState.OFFLINE,
            DeviceState.READY,
        },
        DeviceState.BUSY: {
            DeviceState.READY,
            DeviceState.SIMULATION,
            DeviceState.DEGRADED,
            DeviceState.FAULT,
            DeviceState.EMERGENCY_STOP,
            DeviceState.PAUSED,
        },
        DeviceState.DEGRADED: {
            DeviceState.READY,
            DeviceState.BUSY,
            DeviceState.FAULT,
            DeviceState.EMERGENCY_STOP,
            DeviceState.OFFLINE,
            DeviceState.MAINTENANCE,
        },
        DeviceState.PAUSED: {
            DeviceState.READY,
            DeviceState.SIMULATION,
            DeviceState.EMERGENCY_STOP,
            DeviceState.FAULT,
            DeviceState.OFFLINE,
        },
        DeviceState.FAULT: {
            DeviceState.MAINTENANCE,
            DeviceState.DISCOVERING,
            DeviceState.OFFLINE,
            DeviceState.EMERGENCY_STOP,
        },
        DeviceState.MAINTENANCE: {
            DeviceState.DISCOVERING,
            DeviceState.READY,
            DeviceState.SIMULATION,
            DeviceState.OFFLINE,
        },
        DeviceState.EMERGENCY_STOP: {
            DeviceState.MAINTENANCE,
            DeviceState.OFFLINE,
        },
        DeviceState.OFFLINE: {
            DeviceState.DISCOVERING,
        },
    }

    def __init__(self, device_id: str, initial_state: DeviceState = DeviceState.DISCOVERING):
        self.device_id = device_id
        self._current_state = initial_state
        self._history: List[DeviceStateTransition] = []
        self._e_stop_reason: Optional[str] = None

    @property
    def current_state(self) -> DeviceState:
        return self._current_state

    @property
    def history(self) -> List[DeviceStateTransition]:
        return list(self._history)

    def transition_to(
        self,
        new_state: DeviceState,
        reason: str,
        authorized_by: str = "system",
    ) -> DeviceStateTransition:
        """Execute a state transition with guard checks and immutable history."""
        if new_state == self._current_state:
            return self._history[-1] if self._history else DeviceStateTransition(
                device_id=self.device_id,
                from_state=self._current_state,
                to_state=new_state,
                timestamp=time.time(),
                reason="no-op",
                authorized_by=authorized_by,
            )

        allowed = self._ALLOWED_TRANSITIONS.get(self._current_state, set())
        if new_state not in allowed:
            raise InvalidStateTransitionError(
                f"Device '{self.device_id}' cannot transition from {self._current_state.value} "
                f"to {new_state.value}. Allowed targets: {[s.value for s in allowed]}"
            )

        transition = DeviceStateTransition(
            device_id=self.device_id,
            from_state=self._current_state,
            to_state=new_state,
            timestamp=time.time(),
            reason=reason,
            authorized_by=authorized_by,
        )
        self._current_state = new_state
        self._history.append(transition)

        if new_state == DeviceState.EMERGENCY_STOP:
            self._e_stop_reason = reason

        return transition

    def emergency_stop(self, reason: str, authorized_by: str = "operator") -> DeviceStateTransition:
        """Trigger an immediate Emergency Stop from any operational state."""
        if self._current_state in (DeviceState.OFFLINE, DeviceState.EMERGENCY_STOP):
            return self._history[-1]
        
        transition = DeviceStateTransition(
            device_id=self.device_id,
            from_state=self._current_state,
            to_state=DeviceState.EMERGENCY_STOP,
            timestamp=time.time(),
            reason=f"EMERGENCY STOP TRIGGERED: {reason}",
            authorized_by=authorized_by,
        )
        self._current_state = DeviceState.EMERGENCY_STOP
        self._e_stop_reason = reason
        self._history.append(transition)
        return transition

    def is_operational(self) -> bool:
        """Returns True if the device can accept command execution."""
        return self._current_state in (DeviceState.READY, DeviceState.SIMULATION)

    def allowed_transitions(self, from_state: Optional[DeviceState] = None) -> Set[DeviceState]:
        """Public view of the legal successor states for the FSM diagram.

        Returns the successors of *from_state* (defaults to the current state).
        Used by the cockpit to render the 10-state machine and to explain why a
        transition was refused.
        """
        source = self._current_state if from_state is None else from_state
        return set(self._ALLOWED_TRANSITIONS.get(source, set()))

    def can_transition_to(self, new_state: DeviceState) -> bool:
        """Whether the proposed transition is legal from the current state."""
        return new_state in self.allowed_transitions()


# Standard alias for state machine
DeviceFSM = DeviceStateMachine
