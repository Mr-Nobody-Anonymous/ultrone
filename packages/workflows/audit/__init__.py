"""ULTRONE Workflows - Tamper-evident audit trails and compliance logging."""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class WorkflowAuditEntry:
    """An immutable audit trail entry tracking workflow dispatches and authorizations."""
    entry_id: str
    workflow_name: str
    operator_id: str
    action_type: str
    details: Dict[str, Any]
    prev_hash: str
    timestamp: float = field(default_factory=time.time)
    entry_hash: str = ""

    def __post_init__(self):
        if not self.entry_hash:
            canonical = json.dumps(
                {
                    "entry_id": self.entry_id,
                    "workflow_name": self.workflow_name,
                    "operator_id": self.operator_id,
                    "action_type": self.action_type,
                    "details": self.details,
                    "prev_hash": self.prev_hash,
                    "timestamp": self.timestamp,
                },
                sort_keys=True,
            )
            self.entry_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "workflow_name": self.workflow_name,
            "operator_id": self.operator_id,
            "action_type": self.action_type,
            "details": self.details,
            "prev_hash": self.prev_hash,
            "entry_hash": self.entry_hash,
            "timestamp": self.timestamp,
        }


class WorkflowAuditTrail:
    """Append-only audit trail guaranteeing compliance and non-repudiation."""

    def __init__(self, genesis_hash: str = "0" * 64):
        self._entries: List[WorkflowAuditEntry] = []
        self._latest_hash = genesis_hash

    def record(
        self,
        entry_id: str,
        workflow_name: str,
        operator_id: str,
        action_type: str,
        details: Dict[str, Any],
    ) -> WorkflowAuditEntry:
        entry = WorkflowAuditEntry(
            entry_id=entry_id,
            workflow_name=workflow_name,
            operator_id=operator_id,
            action_type=action_type,
            details=details,
            prev_hash=self._latest_hash,
        )
        self._entries.append(entry)
        self._latest_hash = entry.entry_hash
        return entry

    def verify_chain(self) -> bool:
        expected = "0" * 64
        for e in self._entries:
            if e.prev_hash != expected:
                return False
            canonical = json.dumps(
                {
                    "entry_id": e.entry_id,
                    "workflow_name": e.workflow_name,
                    "operator_id": e.operator_id,
                    "action_type": e.action_type,
                    "details": e.details,
                    "prev_hash": e.prev_hash,
                    "timestamp": e.timestamp,
                },
                sort_keys=True,
            )
            if hashlib.sha256(canonical.encode("utf-8")).hexdigest() != e.entry_hash:
                return False
            expected = e.entry_hash
        return True

    def get_entries(self) -> List[Dict[str, Any]]:
        return [e.to_dict() for e in self._entries]


__all__ = ["WorkflowAuditEntry", "WorkflowAuditTrail"]
