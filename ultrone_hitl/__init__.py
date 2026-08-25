# Copyright (c) Ultrone Contributors. All rights reserved.
"""Canonical ULTRONE HITL decision-control package.

Provides the human-in-the-loop proposal workflow and its append-only,
tamper-evident audit store, operating exclusively on the canonical
:class:`core.contracts.DecisionTrace` / ``DecisionPipeline`` contracts from the
``core`` package. This is deliberately a *clean* ULTRONE-owned surface -- it
does **not** reuse the vendored ``backend/`` ("Argus") package.

Public API:
    AuditStore / InMemoryAuditStore / JSONLAuditStore   - append-only audit log
    Authorizer, DecisionWorkflow, Decision, Evidence    - HITL state machine
    DecisionApplication (FastAPI)             - HTTP endpoints for the workflow

Lifecycle of a decision (server-enforced states)::

    submit --proposed--> PENDING --approve--> APPROVED --execute--> EXECUTED
                      PENDING --reject--> REJECTED        (terminal)
                      PENDING --override--> OVERRIDDEN   (terminal for parent,
                                          spawns a new PENDING child)
"""

from ultrone_hitl.audit_store import (
    AuditStore,
    AuditStoreError,
    DuplicateDecisionError,
    InMemoryAuditStore,
    JSONLAuditStore,
    TamperDetectedError,
)
from ultrone_hitl.decision_workflow import (
    Authorizer,
    Decision,
    DecisionWorkflow,
    InvalidTransitionError,
    Role,
    UnauthorizedActionError,
    UnknownDecisionError,
)
from ultrone_hitl.pipeline_bridge import HITLBridge, validate_lifecycle_history

__all__ = [
    "AuditStore",
    "AuditStoreError",
    "DuplicateDecisionError",
    "InMemoryAuditStore",
    "JSONLAuditStore",
    "TamperDetectedError",
    "Authorizer",
    "Decision",
    "DecisionWorkflow",
    "InvalidTransitionError",
    "Role",
    "UnauthorizedActionError",
    "UnknownDecisionError",
    "HITLBridge",
    "validate_lifecycle_history",
]

# Convenience re-export of the ship-ready FastAPI app (import lazily so that
# importing this package does not require fastapi unless requested).
def DecisionApplication(*args, **kwargs):
    from ultrone_hitl.api import create_app

    return create_app(*args, **kwargs)