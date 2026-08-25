# Copyright (c) Ultrone Contributors. All rights reserved.
"""Bridge between the canonical DecisionPipeline and the HITL/audit layer.

This closes the decision loop (Sprint B-A): every finalized
:class:`core.contracts.DecisionTrace` produced by
``core.pipeline.DecisionPipeline`` is automatically submitted into the
append-only, hash-chained audit store through this bridge -- no second
manual HTTP submission is required.

Guarantees:

- **Exactly one canonical trace per decision.** Submission is idempotent;
  the store's existing ``DuplicateDecisionError`` guard makes a duplicate
  proposal impossible, and the bridge treats it as "already recorded".
- **Immutable/hash-chained audit semantics preserved.** The bridge only
  ever *appends* events through ``DecisionWorkflow`` / ``AuditStore``;
  it never mutates or deletes prior records.
- **Rejected/overridden decisions cannot execute.** Execution is recorded
  only through ``record_execution``, which requires the stored state to be
  APPROVED (the server-owned state machine refuses REJECTED/OVERRIDDEN).
- **Lifecycle enforced end-to-end** against ``core.lifecycle``'s
  allow-list, mirrored into each trace's ``execution["lifecycle"]``.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from core.contracts import DecisionTrace
from core.lifecycle import IllegalTransitionError, LifecycleState

from ultrone_hitl.audit_store import (
    AuditStore,
    DuplicateDecisionError,
    InMemoryAuditStore,
)
from ultrone_hitl.decision_workflow import Decision, DecisionWorkflow

logger = logging.getLogger("Ultrone.HITL.PipelineBridge")


class HITLBridge:
    """Mediates pipeline <-> HITL workflow <-> audit store."""

    def __init__(
        self,
        store: Optional[AuditStore] = None,
        workflow: Optional[DecisionWorkflow] = None,
        system_actor: str = "bob",
    ) -> None:
        self.store = store if store is not None else InMemoryAuditStore()
        self.workflow = workflow if workflow is not None else DecisionWorkflow(self.store)
        self.system_actor = system_actor

    # -- submission (automatic, idempotent) ------------------------------- #
    def submit_trace(
        self, trace: DecisionTrace, scenario_id: str = "", summary: str = "",
    ) -> str:
        """Persist exactly one proposal record for this trace's decision_id.

        Safe to call multiple times: a repeat call is a no-op because the
        audit store rejects duplicate proposals.
        """
        try:
            self.workflow.submit(
                trace,
                actor=self.system_actor,
                scenario_id=scenario_id,
                summary=summary or f"auto-submitted by DecisionPipeline (tick={trace.tick})",
            )
        except DuplicateDecisionError:
            logger.debug("decision %s already submitted; ignoring", trace.decision_id)
        return trace.decision_id

    # -- human transitions ------------------------------------------------ #
    def approve(self, decision_id: str, actor: str, note: str = "") -> Decision:
        return self.workflow.approve(decision_id, actor, note=note)

    def reject(self, decision_id: str, actor: str, reason: str) -> Decision:
        return self.workflow.reject(decision_id, actor, reason)

    def override(
        self, decision_id: str, actor: str, target: Dict[str, Any], note: str = "",
    ) -> Tuple[Decision, Decision]:
        return self.workflow.override(decision_id, actor, target, note=note)

    # -- execution / outcome recording ------------------------------------ #
    def record_execution(self, decision_id: str, actor: str) -> Decision:
        """APPROVED -> EXECUTED. Refuses anything but APPROVED."""
        state = self.store.current_state(decision_id)
        if state != "APPROVED":
            raise IllegalTransitionError(str(state), "EXECUTE", decision_id)
        return self.workflow.execute(decision_id, actor)

    def record_autonomous_execution(self, decision_id: str) -> Decision:
        """Record an approval-free (system-approved) execution, fully audited."""
        state = self.store.current_state(decision_id)
        if state != "PENDING":
            raise IllegalTransitionError(str(state), "EXECUTE", decision_id)
        self.workflow.approve(decision_id, self.system_actor, note="autonomous mode")
        return self.workflow.execute(decision_id, self.system_actor)

    def record_refusal(self, decision_id: str, reason: str = "") -> Decision:
        """Close an autonomously safety-rejected decision as REJECTED (terminal)."""
        state = self.store.current_state(decision_id)
        if state != "PENDING":
            raise IllegalTransitionError(str(state), "REJECTED", decision_id)
        return self.workflow.reject(
            decision_id, self.system_actor, reason or "safety-gate rejection",
        )


    def record_outcome(self, decision_id: str, outcome: Dict[str, Any]) -> str:
        """Append the immutable outcome event (only valid post-execution)."""
        state = self.store.current_state(decision_id)
        if state != "EXECUTED":
            raise IllegalTransitionError(str(state), "OUTCOME", decision_id)
        return self.store.append_event(
            "outcome", decision_id, "EXECUTED", self.system_actor,
            {"outcome": outcome},
        )

    # -- introspection ----------------------------------------------------- #
    def state_of(self, decision_id: str) -> Optional[str]:
        return self.store.current_state(decision_id)

    def verify_chain(self) -> bool:
        """Recompute the full hash chain; raises TamperDetectedError on tamper."""
        return self.store.verify()

    def replay(self) -> List[Dict[str, Any]]:
        return self.store.replay()


def validate_lifecycle_history(history) -> bool:
    """True if a recorded lifecycle history follows the canonical allow-list."""
    states = [
        h if isinstance(h, LifecycleState) else LifecycleState(h) for h in history
    ]
    if not states or states[0] is not LifecycleState.SENSE:
        return False
    from core.lifecycle import validate_transition

    for cur, nxt in zip(states, states[1:]):
        try:
            validate_transition(cur, nxt)
        except IllegalTransitionError:
            return False
    return True
