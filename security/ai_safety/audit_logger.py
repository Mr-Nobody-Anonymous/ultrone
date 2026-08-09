# Copyright (c) Ultrone Contributors. All rights reserved.
"""Audit logging for AI safety and compliance.

Every agent action, tool call, model invocation, and safety check is logged
with full provenance for forensic analysis and compliance.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Ultrone.Security.AISafety.Audit")


class EventType(Enum):
    """Types of auditable events."""
    MODEL_INVOKE = "model_invoke"
    TOOL_CALL = "tool_call"
    ACTION_LOG = "action_log"
    SAFETY_CHECK = "safety_check"
    DATA_ACCESS = "data_access"
    MODEL_DEPLOY = "model_deploy"
    MODEL_MODIFY = "model_modify"
    WEIGHT_UPDATE = "weight_update"
    EXPERIMENT = "experiment"
    FEEDBACK = "feedback"
    RESEARCH = "research"
    DENY = "deny"


@dataclass
class AuditEvent:
    """A single audit-log entry."""
    event_id: str
    event_type: EventType
    actor: str
    action: str
    timestamp: float
    severity: str = "info"
    details: Dict[str, Any] = field(default_factory=dict)
    request_id: Optional[str] = None
    model_version: Optional[str] = None
    tools_used: List[str] = field(default_factory=list)
    retrieval_sources: List[str] = field(default_factory=list)
    input_hash: Optional[str] = None
    output_hash: Optional[str] = None
    duration_ms: Optional[float] = None
    approved: Optional[bool] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "actor": self.actor,
            "action": self.action,
            "timestamp": self.timestamp,
            "severity": self.severity,
            "details": self.details,
            "request_id": self.request_id,
            "model_version": self.model_version,
            "tools_used": self.tools_used,
            "retrieval_sources": self.retrieval_sources,
            "input_hash": self.input_hash,
            "output_hash": self.output_hash,
            "duration_ms": self.duration_ms,
            "approved": self.approved,
        }


class AuditLogger:
    """Writes structured audit logs to disk and stdout.

    Each event is written as a JSON line (JSONL) for easy parsing,
    and also logged via the standard logging framework.
    """

    def __init__(self, log_file: str = "./audit/audit.log"):
        self.log_file = log_file
        os.makedirs(os.path.dirname(log_file) or ".", exist_ok=True)
        self._events: List[AuditEvent] = []
        self._start_time = time.time()

    def log(
        self,
        event_type: EventType,
        actor: str,
        action: str,
        details: Optional[Dict[str, Any]] = None,
        severity: str = "info",
        request_id: Optional[str] = None,
        model_version: Optional[str] = None,
        tools_used: Optional[List[str]] = None,
        retrieval_sources: Optional[List[str]] = None,
        input_text: Optional[str] = None,
        output_text: Optional[str] = None,
        duration_ms: Optional[float] = None,
        approved: Optional[bool] = None,
    ) -> AuditEvent:
        """Log an audit event."""
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            actor=actor,
            action=action,
            timestamp=time.time(),
            severity=severity,
            details=details or {},
            request_id=request_id,
            model_version=model_version,
            tools_used=tools_used or [],
            retrieval_sources=retrieval_sources or [],
            input_hash=hashlib.sha256(input_text.encode()).hexdigest()[:16] if input_text else None,
            output_hash=hashlib.sha256(output_text.encode()).hexdigest()[:16] if output_text else None,
            duration_ms=duration_ms,
            approved=approved,
        )
        self._events.append(event)

        # Write JSONL
        try:
            with open(self.log_file, "a") as f:
                f.write(json.dumps(event.to_dict(), default=str) + "\n")
        except OSError as e:
            logger.warning("Failed to write audit log: %s", e)

        logger.info(
            "AUDIT [%s] %s: %s (actor=%s, approved=%s)",
            event_type.value, action, details or {}, actor, approved,
        )
        return event

    def deny(
        self,
        actor: str,
        action: str,
        reason: str,
        request_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        """Log a denied action (security event)."""
        return self.log(
            EventType.DENY,
            actor,
            action,
            details={**(details or {}), "reason": reason},
            severity="critical",
            request_id=request_id,
            approved=False,
        )

    def get_events(
        self,
        event_type: Optional[EventType] = None,
        actor: Optional[str] = None,
        since: Optional[float] = None,
    ) -> List[AuditEvent]:
        """Query audit events with optional filters."""
        events = self._events
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        if actor:
            events = [e for e in events if e.actor == actor]
        if since:
            events = [e for e in events if e.timestamp >= since]
        return events

    def get_stats(self) -> Dict[str, Any]:
        from collections import Counter
        type_counts = Counter(e.event_type.value for e in self._events)
        deny_count = sum(1 for e in self._events if e.event_type == EventType.DENY)
        return {
            "uptime_seconds": time.time() - self._start_time,
            "total_events": len(self._events),
            "events_by_type": dict(type_counts),
            "denied_count": deny_count,
            "log_file": self.log_file,
        }

    def export_jsonl(self, path: str) -> str:
        """Export all events to a JSONL file."""
        with open(path, "w") as f:
            for event in self._events:
                f.write(json.dumps(event.to_dict(), default=str) + "\n")
        return path
