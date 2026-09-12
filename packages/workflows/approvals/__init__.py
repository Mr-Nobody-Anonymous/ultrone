"""ULTRONE Workflows - Human-in-the-Loop (HITL) approval gates and safety policies."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class ApprovalRequest:
    """A high-consequence action request queued for human operator authorization."""
    request_id: str
    action_id: str
    initiator_id: str  # human or AI model
    target_entity_id: str
    rationale: str
    payload: Dict[str, Any] = field(default_factory=dict)
    status: ApprovalStatus = ApprovalStatus.PENDING
    approver_id: Optional[str] = None
    approval_timestamp: Optional[float] = None
    created_at: float = field(default_factory=time.time)
    timeout_seconds: float = 300.0

    def approve(self, approver_id: str) -> None:
        self.status = ApprovalStatus.APPROVED
        self.approver_id = approver_id
        self.approval_timestamp = time.time()

    def reject(self, approver_id: str, reason: str = "") -> None:
        self.status = ApprovalStatus.REJECTED
        self.approver_id = approver_id
        self.approval_timestamp = time.time()
        self.payload["rejection_reason"] = reason

    def is_expired(self) -> bool:
        if self.status == ApprovalStatus.PENDING:
            return (time.time() - self.created_at) > self.timeout_seconds
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "action_id": self.action_id,
            "initiator_id": self.initiator_id,
            "target_entity_id": self.target_entity_id,
            "rationale": self.rationale,
            "status": self.status.value,
            "approver_id": self.approver_id,
            "created_at": self.created_at,
            "timeout_seconds": self.timeout_seconds,
        }


class ApprovalGate:
    """Enforces human-in-the-loop policies before safety-critical workflows execute."""

    def __init__(self):
        self._requests: Dict[str, ApprovalRequest] = {}

    def submit_request(self, req: ApprovalRequest) -> ApprovalRequest:
        self._requests[req.request_id] = req
        return req

    def get_pending_requests(self) -> List[ApprovalRequest]:
        return [r for r in self._requests.values() if r.status == ApprovalStatus.PENDING and not r.is_expired()]

    def resolve_request(self, request_id: str, approved: bool, approver_id: str, reason: str = "") -> Optional[ApprovalRequest]:
        req = self._requests.get(request_id)
        if not req:
            return None
        if approved:
            req.approve(approver_id)
        else:
            req.reject(approver_id, reason)
        return req


__all__ = ["ApprovalStatus", "ApprovalRequest", "ApprovalGate"]
