# Copyright (c) Ultrone Contributors. All rights reserved.
"""Canonical decision lifecycle for ULTRONE.

One authoritative state machine governs every decision cycle:

    SENSE -> FUSE -> ESTIMATE -> PLAN -> SAFETY_GATE -> PENDING
        -> HUMAN_DECISION -> EXECUTE -> OUTCOME

with two terminal branches out of HUMAN_DECISION:

    REJECTED, OVERRIDDEN

Rules enforced structurally (illegal transitions are impossible):

1. Transitions are validated against an explicit allow-list table; any
   transition not present raises :class:`IllegalTransitionError`.
2. Terminal states (OUTCOME, REJECTED, OVERRIDDEN) have *no* outgoing
   edges, so a rejected or overridden decision can never reach EXECUTE.
3. Only SAFETY_GATE may lead to PENDING, and only PENDING leads to
   HUMAN_DECISION -- a decision cannot be reviewed without having passed
   the independent safety gate first.
4. When no HITL review is attached, SAFETY_GATE may go straight to
   EXECUTE (autonomous mode), preserving Phase 1 behavior.

The same table backs both the in-process lifecycle tracker
(:class:`DecisionLifecycle`) used by ``core.pipeline.DecisionPipeline``
and the audit-layer enforcement in ``ultrone_hitl.pipeline_bridge``.
"""

from __future__ import annotations

import enum
from typing import List, Tuple


class LifecycleState(str, enum.Enum):
    """States of one decision cycle, in canonical order."""

    SENSE = "SENSE"
    FUSE = "FUSE"
    ESTIMATE = "ESTIMATE"
    PLAN = "PLAN"
    SAFETY_GATE = "SAFETY_GATE"
    PENDING = "PENDING"
    HUMAN_DECISION = "HUMAN_DECISION"
    EXECUTE = "EXECUTE"
    OUTCOME = "OUTCOME"
    REJECTED = "REJECTED"          # terminal: human refused the proposal
    OVERRIDDEN = "OVERRIDDEN"      # terminal for parent: child spawned


class IllegalTransitionError(Exception):
    """A lifecycle transition that the allow-list forbids was attempted."""

    def __init__(self, current: str, attempted: str, decision_id: str = "") -> None:
        super().__init__(
            f"illegal lifecycle transition {current} -> {attempted}"
            + (f" (decision {decision_id})" if decision_id else "")
        )
        self.current = current
        self.attempted = attempted
        self.decision_id = decision_id


#: Explicit allow-list. If a (from, to) pair is absent here, it is illegal.
ALLOWED_TRANSITIONS = {
    LifecycleState.SENSE: frozenset({LifecycleState.FUSE}),
    LifecycleState.FUSE: frozenset({LifecycleState.ESTIMATE}),
    LifecycleState.ESTIMATE: frozenset({LifecycleState.PLAN}),
    LifecycleState.PLAN: frozenset({LifecycleState.SAFETY_GATE}),
    # Autonomous decisions skip review; reviewed decisions enter PENDING.
    LifecycleState.SAFETY_GATE: frozenset({
        LifecycleState.PENDING, LifecycleState.EXECUTE,
    }),
    LifecycleState.PENDING: frozenset({LifecycleState.HUMAN_DECISION}),
    # Review resolves into execution OR a terminal refusal.
    LifecycleState.HUMAN_DECISION: frozenset({
        LifecycleState.EXECUTE, LifecycleState.REJECTED, LifecycleState.OVERRIDDEN,
    }),
    LifecycleState.EXECUTE: frozenset({LifecycleState.OUTCOME}),
    # Terminal states: no outgoing edges, ever.
    LifecycleState.OUTCOME: frozenset(),
    LifecycleState.REJECTED: frozenset(),
    LifecycleState.OVERRIDDEN: frozenset(),
}

TERMINAL_STATES = frozenset({
    LifecycleState.OUTCOME,
    LifecycleState.REJECTED,
    LifecycleState.OVERRIDDEN,
})


def validate_transition(
    current: "LifecycleState | str", attempted: "LifecycleState | str",
    decision_id: str = "",
) -> None:
    """Raise :class:`IllegalTransitionError` unless current -> attempted is allowed."""
    cur = LifecycleState(current)
    nxt = LifecycleState(attempted)
    if nxt not in ALLOWED_TRANSITIONS[cur]:
        raise IllegalTransitionError(cur.value, nxt.value, decision_id)


class DecisionLifecycle:
    """Tracks and enforces the lifecycle of exactly one decision."""

    def __init__(self, decision_id: str = "") -> None:
        self.decision_id = decision_id
        self._history: List[LifecycleState] = []

    @property
    def history(self) -> Tuple[LifecycleState, ...]:
        return tuple(self._history)

    @property
    def current(self) -> "LifecycleState | None":
        return self._history[-1] if self._history else None

    def advance(self, state: "LifecycleState | str") -> LifecycleState:
        """Validate and record a forward transition; returns the new state."""
        nxt = LifecycleState(state)
        if self._history:
            validate_transition(self._history[-1], nxt, self.decision_id)
        elif nxt is not LifecycleState.SENSE:
            raise IllegalTransitionError("<start>", nxt.value, self.decision_id)
        self._history.append(nxt)
        return nxt

    def as_list(self) -> List[str]:
        return [s.value for s in self._history]
