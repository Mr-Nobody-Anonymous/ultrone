# Copyright (c) Ultrone Contributors. All rights reserved.
"""FastAPI HITL control plane for ULTRONE decisions.

Operates exclusively on the canonical :class:`core.contracts.DecisionTrace` /
``DecisionPipeline`` contracts via :class:`ultrone_hitl.decision_workflow`.
The server owns decision state: transitions are validated against the stored
audit log and the actor's role, never against client-supplied state.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from ultrone_hitl.audit_store import (
    AuditStore,
    DuplicateDecisionError,
    JSONLAuditStore,
)
from ultrone_hitl.decision_workflow import (
    Authorizer,
    DecisionWorkflow,
    InvalidTransitionError,
    UnauthorizedActionError,
    UnknownDecisionError,
    trace_from_dict,
)

logger = logging.getLogger("ultrone.hitl.api")

DEFAULT_STORE_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "hitl_audit" / "audit.jsonl"
)

# Annotation-only import: keeps ``import ultrone_hitl`` working without
# fastapi installed, while making ``Request`` resolvable to pydantic when
# routes are registered inside create_app().
try:  # pragma: no cover - exercised only without fastapi
    from fastapi import Request  # noqa: F401
except ImportError:  # pragma: no cover
    Request = Any  # type: ignore[assignment,misc]


# --------------------------------------------------------------------------- #
# HTTP wire DTOs (marrow wrappers around the canonical decision model)
# --------------------------------------------------------------------------- #
class SubmitRequest(BaseModel):
    trace: Dict[str, Any] = Field(description="canonical DecisionTrace.to_dict()")
    actor: str
    scenario_id: Optional[str] = None
    summary: Optional[str] = None


class ActorActionRequest(BaseModel):
    actor: str
    note: Optional[str] = None


class RejectRequest(BaseModel):
    actor: str
    reason: str
    note: Optional[str] = None


class OverrideRequest(BaseModel):
    actor: str
    target: Dict[str, Any] = Field(
        description="modified execution order (env action dict) entered by operator"
    )
    note: Optional[str] = None


class AskReasoningRequest(BaseModel):
    actor: str = "operator"
    question: Optional[str] = None


def _to_status(exc: Exception) -> int:
    if isinstance(exc, UnknownDecisionError):
        return 404
    if isinstance(exc, UnauthorizedActionError):
        return 403
    if isinstance(exc, DuplicateDecisionError):
        return 409
    if isinstance(exc, InvalidTransitionError):
        return 409
    return 500


def create_app(
    store: Optional[AuditStore] = None,
    authorizer: Optional[Authorizer] = None,
    authenticator: Optional[Any] = None,
) -> Any:
    from fastapi import FastAPI, HTTPException, Request

    store = store or JSONLAuditStore(DEFAULT_STORE_PATH)
    authorizer = authorizer or Authorizer()
    workflow = DecisionWorkflow(
        store=store, authorizer=authorizer, authenticator=authenticator,
    )

    def _credential(request: Request, req_actor: str) -> str:
        """Resolve the request credential -- NEVER the body's say-so alone.

        Priority: ``X-ULTRONE-Subject`` header (the authenticated wire
        credential) > legacy body ``actor`` field. When a header is
        present and disagrees with the body value, the request is rejected
        as an identity forgery attempt before any authorization runs.
        """
        header_subject = request.headers.get("x-ultrone-subject")
        if header_subject:
            if req_actor and header_subject != req_actor:
                raise HTTPException(
                    status_code=403,
                    detail=(
                        "identity mismatch: body actor does not match "
                        "authenticated credential"
                    ),
                )
            return header_subject
        return req_actor

    app = FastAPI(
        title="ULTRONE HITL + Decision Control API",
        description="Human-in-the-loop approval of ULTRONE decision traces.",
        version="0.1.0",
    )

    # -- submit a decision for human review ------------------------------ #
    @app.post("/api/human/decisions")
    def submit(req: SubmitRequest, request: Request):
        try:
            trace = trace_from_dict(req.trace)
            view = workflow.submit(
                trace, _credential(request, req.actor),
                scenario_id=req.scenario_id or "",
                summary=req.summary or "",
            )
            return {"decision": view.to_dict()}
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001 - uniform HTTP mapping
            raise HTTPException(status_code=_to_status(exc), detail=str(exc))

    # -- approve ---------------------------------------------------------- #
    @app.post("/api/human/decisions/{decision_id}/approve")
    def approve(decision_id: str, req: ActorActionRequest, request: Request):
        try:
            view = workflow.approve(
                decision_id, _credential(request, req.actor),
                note=req.note or "",
            )
            return {"decision": view.to_dict()}
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=_to_status(exc), detail=str(exc))

    # -- reject ----------------------------------------------------------- #
    @app.post("/api/human/decisions/{decision_id}/reject")
    def reject(decision_id: str, req: RejectRequest, request: Request):
        try:
            view = workflow.reject(
                decision_id, _credential(request, req.actor), reason=req.reason,
            )
            return {"decision": view.to_dict()}
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=_to_status(exc), detail=str(exc))

    # -- override / modify ------------------------------------------------ #
    @app.post("/api/human/decisions/{decision_id}/override")
    def override(decision_id: str, req: OverrideRequest, request: Request):
        try:
            parent, child = workflow.override(
                decision_id, _credential(request, req.actor), req.target,
                note=req.note or "",
            )
            return {"parent": parent.to_dict(), "child": child.to_dict()}
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=_to_status(exc), detail=str(exc))

    # -- execute ---------------------------------------------------------- #
    @app.post("/api/human/decisions/{decision_id}/execute")
    def execute(decision_id: str, req: ActorActionRequest, request: Request):
        try:
            view = workflow.execute(decision_id, _credential(request, req.actor))
            return {"decision": view.to_dict()}
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=_to_status(exc), detail=str(exc))

    # -- request reasoning / evidence ------------------------------------ #
    @app.post("/api/human/decisions/{decision_id}/ask_reasoning")
    def ask_reasoning(decision_id: str, req: AskReasoningRequest):
        try:
            evidence = workflow.evidence(decision_id)
            return {"decision_id": decision_id, "evidence": evidence.to_dict()}
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=_to_status(exc), detail=str(exc))

    # -- retrieve a decision + trace -------------------------------------- #
    @app.get("/api/human/decisions/{decision_id}")
    def get_decision(decision_id: str):
        try:
            return {"decision": workflow.get(decision_id).to_dict()}
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=_to_status(exc), detail=str(exc))

    # -- list decisions (optional ?state= filter) ------------------------- #
    @app.get("/api/human/decisions")
    def list_decisions(state: Optional[str] = None):
        try:
            views = workflow.list(state=state)
            return {"decisions": [v.to_dict() for v in views]}
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=_to_status(exc), detail=str(exc))

    # -- audit replay ------------------------------------------------------ #
    @app.get("/api/human/audit")
    def audit_replay():
        try:
            return {"events": store.replay()}
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=_to_status(exc), detail=str(exc))

    app.state.store = store
    app.state.authorizer = authorizer
    app.state.workflow = workflow
    app.state.authenticator = workflow.authenticator
    return app