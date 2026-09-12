"""
ULTRONE Distributed Tracing (OpenTelemetry).

Every decision is traceable:
  Observation → Source → Transformation → Model →
  Reasoning → Decision → Confidence → Human approval → Outcome

This module provides OpenTelemetry integration for distributed
tracing across ULTRONE services.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Span:
    """A trace span representing a unit of work."""
    span_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    trace_id: str = ""
    parent_id: Optional[str] = None
    operation: str = ""
    service: str = "ultrone"
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "ok"

    def end(self) -> None:
        self.end_time = time.time()

    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        self.events.append({
            "name": name,
            "timestamp": time.time(),
            "attributes": attributes or {},
        })


class Tracer:
    """Simple tracer — replace with OpenTelemetry SDK in production."""

    def __init__(self, service_name: str = "ultrone") -> None:
        self.service_name = service_name
        self._spans: List[Span] = []

    def start_span(self, operation: str, parent_id: Optional[str] = None) -> Span:
        span = Span(
            trace_id=uuid.uuid4().hex[:32],
            parent_id=parent_id,
            operation=operation,
            service=self.service_name,
        )
        self._spans.append(span)
        return span


__all__ = ["Span", "Tracer"]
