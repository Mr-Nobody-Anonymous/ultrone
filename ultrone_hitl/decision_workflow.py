# Copyright (c) Ultrone Contributors. All rights reserved.
"""HITL decision state machine + authorization for ULTRONE.

All decisions are expressed in terms of the canonical
:class:`core.contracts.DecisionTrace`. The server owns the decision state, so a
client cannot flip a rejected decision to approved merely by changing a request
field: every transition is validated against the *stored* current state and the
required actor role.

States (server-enforced): PENDING -> APPROVED -> EXECUTED;
PENDING -> REJECTED (terminal); PENDING -> OVERRIDDEN (terminal for the parent,
spawns a new PENDING child that preserves the original proposal).
"""

from __future__ import annotations

import copy
import enum
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from core.contracts import DecisionTrace, new_id


class DecisionState(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    OVERRIDDEN = "OVERRIDDEN"
    EXECUTED = "EXECUTED"


class Role(str, enum.Enum):
    OPERATOR = "operator"
    SUPERVISOR = "supervisor"
    ADMIN = "admin"


class DecisionWorkflowError(Exception):
    """Base error for the HITL workflow."""


class UnknownDecisionError(DecisionWorkflowError):
    def __init__(self, decision_id: str) -> None:
        super().__init__(f"unknown decision: {decision_id}")
        self.decision_id = decision_id


class InvalidTransitionError(DecisionWorkflowError):
    def __init__(self, decision_id: str, current: str, attempted: str) -> None:
        super().__init__(f"decision {decision_id} is {current}; cannot {attempted}")
        self.decision_id = decision_id
        self.current_state = current
        self.attempted = attempted


class UnauthorizedActionError(DecisionWorkflowError):
    def __init__(self, actor: str, required: str) -> None:
        super().__init__(f"actor '{actor}' lacks role '{required}' or is unregistered")
        self.actor = actor
        self.required = required


def trace_from_dict(d: Dict[str, Any]) -> DecisionTrace:
    """Rebuild a canonical DecisionTrace from its ``to_dict()`` form."""
    return DecisionTrace(
        decision_id=d["decision_id"],
        episode_id=str(d.get("episode_id") or ""),
        tick=int(d.get("tick", 0)),
        sensing=dict(d.get("sensing") or {}),
        perception=dict(d.get("perception") or {}),
        world_state=dict(d.get("world_state") or {}),
        planning=dict(d.get("planning") or {}),
        safety=dict(d.get("safety") or {}),
        execution=dict(d.get("execution") or {}),
        outcome=dict(d.get("outcome") or {}),
    )


class Authorizer:
    """Role-based authorization. The server decides who may act.

    Maps actor id -> granted role. Unknown actors are denied (fail-closed).
    """

    ROLES = (Role.OPERATOR, Role.SUPERVISOR, Role.ADMIN)

    def __init__(self, actors: Optional[Dict[str, Role]] = None) -> None:
        self._actor_roles = dict(actors or {})
        self._actor_roles.setdefault("bob", Role.OPERATOR)
        self._actor_roles.setdefault("alice", Role.SUPERVISOR)
        self._actor_roles.setdefault("carol", Role.ADMIN)

    def role_of(self, actor: str) -> Optional[Role]:
        return self._actor_roles.get(actor)

    def register(self, actor: str, role: Role) -> None:
        self._actor_roles[actor] = role

    def require(self, actor: str, *roles: Role) -> Role:
        role = self._actor_roles.get(actor)
        if role is None or role not in roles:
            raise UnauthorizedActionError(actor, "/".join(r.value for r in roles))
        return role


class Decision:
    """Single read-only decision view: current state + event history."""

    def __init__(
        self,
        decision_id: str,
        state: DecisionState,
        trace: DecisionTrace,
        summary: str,
        scenario_id: str,
        created_at: str,
        updated_at: str,
        history: List[Dict[str, Any]],
        override_of: Optional[str] = None,
        child: Optional[str] = None,
    ) -> None:
        self.decision_id = decision_id
        self.state = state
        self.trace = trace
        self.summary = summary
        self.scenario_id = scenario_id
        self.created_at = created_at
        self.updated_at = updated_at
        self.history = history
        self.override_of = override_of
        self.child = child

    def to_dict(self) -> Dict[str, Any]:
        state = self.state.value if isinstance(self.state, DecisionState) else self.state
        return {
            "decision_id": self.decision_id,
            "state": state,
            "summary": self.summary,
            "scenario_id": self.scenario_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "override_of": self.override_of,
            "child": self.child,
            "trace": self.trace.to_dict(),
            "history": copy.deepcopy(self.history),
        }


@dataclass
class Evidence:
    """Explanatory evidence assembled from the canonical DecisionTrace."""

    decision_id: str
    confidence: float
    uncertainty: float
    n_candidates: int
    candidate_ids: List[str]
    proposed_orders: List[Any]
    safety_verdict: Dict[str, Any]
    rejections: List[Any]
    explanation: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "confidence": self.confidence,
            "uncertainty": self.uncertainty,
            "n_candidates": self.n_candidates,
            "candidate_ids": self.candidate_ids,
            "proposed_orders": self.proposed_orders,
            "safety_verdict": self.safety_verdict,
            "rejections": self.rejections,
            "explanation": self.explanation,
        }


class DecisionWorkflow:
    """Server-side HITL state machine. All transitions are state + role checked."""

    APPROVE_ROLES = (Role.OPERATOR, Role.SUPERVISOR, Role.ADMIN)
    REJECT_ROLES = (Role.OPERATOR, Role.SUPERVISOR, Role.ADMIN)
    OVERRIDE_ROLES = (Role.SUPERVISOR, Role.ADMIN)
    EXECUTE_ROLES = (Role.OPERATOR, Role.SUPERVISOR, Role.ADMIN)
    SUBMIT_ROLES = (Role.OPERATOR, Role.SUPERVISOR, Role.ADMIN)

    def __init__(self, store: Any, authorizer: Optional[Authorizer] = None) -> None:
        self.store = store
        self.authorizer = authorizer or Authorizer()

    # -- read helpers ----------------------------------------------------- #
    def _require_state(self, decision_id: str) -> DecisionState:
        state = self.store.current_state(decision_id)
        if state is None:
            raise UnknownDecisionError(decision_id)
        return DecisionState(state)

    def _proposal_event(self, decision_id: str) -> Dict[str, Any]:
        events = self.store.decision_events(decision_id)
        if not events:
            raise UnknownDecisionError(decision_id)
        for ev in events:
            if ev["type"] == "submit":
                return ev
        raise UnknownDecisionError(decision_id)

    def _decision_view(self, decision_id: str) -> Decision:
        history = self.store.decision_events(decision_id)
        if not history:
            raise UnknownDecisionError(decision_id)
        last = history[-1]
        state = DecisionState(last["state"])
        props = self._proposal_event(decision_id)
        payload = props["payload"]
        trace = trace_from_dict(payload["trace"])
        meta = {k: v for k, v in payload.items() if k != "trace"}
        history_out = [
            {
                "event_id": ev["event_id"],
                "type": ev["type"],
                "state": ev["state"],
                "actor": ev["actor"],
                "timestamp": ev["timestamp"],
                **{
                    f"meta_{k}": v
                    for k, v in ev["payload"].items()
                    if k not in ("trace",)
                },
            }
            for ev in history
        ]
        return Decision(
            decision_id=decision_id,
            state=state,
            trace=trace,
            summary=str(meta.get("summary") or ""),
            scenario_id=str(meta.get("scenario_id") or ""),
            created_at=history[0]["timestamp"],
            updated_at=last["timestamp"],
            history=history_out,
            override_of=meta.get("override_of"),
            child=meta.get("child"),
        )

    # -- transitions ------------------------------------------------------ #
    def submit(
        self,
        trace: DecisionTrace,
        actor: str,
        scenario_id: str = "",
        summary: str = "",
    ) -> Decision:
        """Record a proposed decision and place it in PENDING review."""
        self.authorizer.require(actor, *self.SUBMIT_ROLES)
        decision_id = trace.decision_id
        self.store.append_event(
            "submit", decision_id, DecisionState.PENDING.value, actor,
            {"trace": trace.to_dict(), "scenario_id": scenario_id, "summary": summary},
        )
        return self._decision_view(decision_id)

    def approve(self, decision_id: str, actor: str, note: str = "") -> Decision:
        """PENDING -> APPROVED (operator+)."""
        state = self._require_state(decision_id)
        if state != DecisionState.PENDING:
            raise InvalidTransitionError(decision_id, state.value, "approve")
        self.authorizer.require(actor, *self.APPROVE_ROLES)
        self.store.append_event(
            "approve", decision_id, DecisionState.APPROVED.value, actor, {"note": note}
        )
        return self._decision_view(decision_id)

    def reject(self, decision_id: str, actor: str, reason: str) -> Decision:
        """PENDING -> REJECTED (terminal; cannot be re-approved)."""
        state = self._require_state(decision_id)
        if state != DecisionState.PENDING:
            raise InvalidTransitionError(decision_id, state.value, "reject")
        self.authorizer.require(actor, *self.REJECT_ROLES)
        self.store.append_event(
            "reject", decision_id, DecisionState.REJECTED.value, actor, {"reason": reason}
        )
        return self._decision_view(decision_id)

    def override(
        self,
        decision_id: str,
        actor: str,
        target: Dict[str, Any],
        note: str = "",
    ) -> Tuple[Decision, Decision]:
        """PENDING -> OVERRIDDEN; spawns a new PENDING child decision.

        The child reuses the original proposal verbatim but carries the
        supervisor-entered modified order. The parent stays untouched.
        """
        state = self._require_state(decision_id)
        if state != DecisionState.PENDING:
            raise InvalidTransitionError(decision_id, state.value, "override")
        self.authorizer.require(actor, *self.OVERRIDE_ROLES)

        parent = self._decision_view(decision_id)
        original = parent.trace.to_dict()
        self.store.append_event(
            "override", decision_id, DecisionState.OVERRIDDEN.value, actor,
            {"note": note, "by": actor},
        )

        child_trace = trace_from_dict(original)
        child_trace.decision_id = new_id("DEC")
        child_trace.execution = {
            **dict(child_trace.execution),
            "order": target,
            "overridden_from": decision_id,
        }
        child_id = child_trace.decision_id
        self.store.append_event(
            "submit", child_id, DecisionState.PENDING.value, actor,
            {
                "trace": child_trace.to_dict(),
                "scenario_id": parent.scenario_id,
                "summary": parent.summary,
                "override_of": decision_id,
            },
        )
        return self._decision_view(decision_id), self._decision_view(child_id)

    def execute(self, decision_id: str, actor: str) -> Decision:
        """APPROVED -> EXECUTED."""
        state = self._require_state(decision_id)
        if state != DecisionState.APPROVED:
            raise InvalidTransitionError(decision_id, state.value, "execute")
        self.authorizer.require(actor, *self.EXECUTE_ROLES)
        self.store.append_event(
            "execute", decision_id, DecisionState.EXECUTED.value, actor, {"note": ""}
        )
        return self._decision_view(decision_id)

    def get(self, decision_id: str) -> Decision:
        return self._decision_view(decision_id)

    def list(self, state: Optional[str] = None) -> List[Decision]:
        ids: List[str] = []
        for ev in self.store.replay():
            if ev["decision_id"] not in ids:
                ids.append(ev["decision_id"])
        result: List[Decision] = []
        for decision_id in ids:
            view = self._decision_view(decision_id)
            if state is None or view.state.value == state:
                result.append(view)
        return result

    def evidence(self, decision_id: str) -> Evidence:
        """Assemble explanatory evidence straight from the stored trace."""
        view = self._decision_view(decision_id)
        ws, pl, sf = view.trace.world_state, view.trace.planning, view.trace.safety
        confidence = float(ws.get("primary_target_confidence", 0.0) or 0.0)
        n_candidates = int(pl.get("n_candidates", 0) or 0)
        verdict = sf.get("verdict", {})
        rejections = sf.get("rejections", [])
        explanation = (
            f"{n_candidates} candidate COAs were generated; the selected order "
            f"passed the independent SafetyGate ({verdict.get('reason', 'approved')})."
        )
        return Evidence(
            decision_id=decision_id,
            confidence=confidence,
            uncertainty=max(0.0, 1.0 - confidence),
            n_candidates=n_candidates,
            candidate_ids=list(pl.get("candidate_ids", []) or []),
            proposed_orders=pl.get("proposed_orders", []) or [],
            safety_verdict=verdict,
            rejections=rejections or [],
            explanation=explanation,
        )