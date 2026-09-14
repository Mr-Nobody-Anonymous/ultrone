# Copyright (c) Ultrone Contributors. All rights reserved.
import pytest

from packages.agents.harness.lifecycle import (
    InvalidStateTransitionError,
    LifecycleStateMachine,
)
from packages.agents.harness.schemas import LifecycleState


def test_valid_lifecycle_transitions():
    sm = LifecycleStateMachine(LifecycleState.CREATED)
    assert sm.current_state == LifecycleState.CREATED

    sm.transition(LifecycleState.PLANNING)
    assert sm.current_state == LifecycleState.PLANNING

    sm.transition(LifecycleState.READY)
    assert sm.current_state == LifecycleState.READY

    sm.transition(LifecycleState.EXECUTING)
    assert sm.current_state == LifecycleState.EXECUTING

    sm.transition(LifecycleState.OBSERVING)
    assert sm.current_state == LifecycleState.OBSERVING

    sm.transition(LifecycleState.VERIFYING)
    assert sm.current_state == LifecycleState.VERIFYING

    sm.transition(LifecycleState.COMPLETED)
    assert sm.current_state == LifecycleState.COMPLETED
    assert sm.current_state.is_terminal


def test_invalid_lifecycle_transition_raises():
    sm = LifecycleStateMachine(LifecycleState.CREATED)
    with pytest.raises(InvalidStateTransitionError):
        sm.transition(LifecycleState.COMPLETED)  # Cannot skip directly to COMPLETED from CREATED


def test_lifecycle_history_and_listeners():
    sm = LifecycleStateMachine()
    transitions_seen = []

    def on_change(prev, target, reason):
        transitions_seen.append((prev, target))

    sm.add_listener(on_change)
    sm.transition(LifecycleState.PLANNING, reason="Start planning")
    sm.transition(LifecycleState.READY, reason="Ready")

    assert len(transitions_seen) == 2
    assert transitions_seen[0] == (LifecycleState.CREATED, LifecycleState.PLANNING)
    assert len(sm.get_history()) == 3  # Initial + 2 transitions
