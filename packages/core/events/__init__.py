"""
ULTRONE Canonical Event System.

All components communicate through a unified event bus.
Every event has:
- Type (what happened)
- Timestamp (when)
- Source (who/what generated it)
- Entity reference (optional)
- Payload (event-specific data)
- Confidence (how certain)
- Provenance (decision chain)

The UI receives these events via WebSocket stream rather than
constantly polling REST endpoints.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class EventType(str, Enum):
    """Standard ULTRONE event types."""
    # Entity lifecycle
    ENTITY_CREATED = "ENTITY_CREATED"
    ENTITY_UPDATED = "ENTITY_UPDATED"
    ENTITY_DESTROYED = "ENTITY_DESTROYED"

    # Observations
    OBSERVATION_ADDED = "OBSERVATION_ADDED"
    SENSOR_READING = "SENSOR_READING"

    # Decisions
    DECISION_MADE = "DECISION_MADE"
    PLAN_GENERATED = "PLAN_GENERATED"
    ACTION_EXECUTED = "ACTION_EXECUTED"

    # Simulation
    SIMULATION_TICK = "SIMULATION_TICK"
    SIMULATION_STARTED = "SIMULATION_STARTED"
    SIMULATION_STOPPED = "SIMULATION_STOPPED"

    # Cognitive
    REASONING_COMPLETE = "REASONING_COMPLETE"
    ANOMALY_DETECTED = "ANOMALY_DETECTED"
    CONFIDENCE_CHANGED = "CONFIDENCE_CHANGED"

    # Human-in-the-loop
    HUMAN_APPROVAL = "HUMAN_APPROVAL"
    HUMAN_REJECTION = "HUMAN_REJECTION"
    HUMAN_OVERRIDE = "HUMAN_OVERRIDE"

    # System
    SYSTEM_HEALTH = "SYSTEM_HEALTH"
    SYSTEM_ERROR = "SYSTEM_ERROR"


@dataclass
class Event:
    """
    Canonical ULTRONE Event.

    Every important output in the system generates an Event that flows
    through the event bus, enabling:
    - Real-time UI updates via WebSocket
    - Audit trail / provenance tracking
    - Cross-component communication
    - Replay and debugging

    Example:
        >>> event = Event(
        ...     type=EventType.ENTITY_UPDATED,
        ...     entity_id="entity_001",
        ...     changes={"status": "active", "confidence": 0.91},
        ...     confidence=0.91,
        ...     source="perception_pipeline",
        ... )
    """
    event_id: str = field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:12]}")
    type: EventType = EventType.ENTITY_UPDATED
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    source: str = ""
    entity_id: Optional[str] = None
    changes: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    provenance: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for WebSocket/JSON transport."""
        return {
            "event_id": self.event_id,
            "type": self.type.value,
            "timestamp": self.timestamp,
            "source": self.source,
            "entity_id": self.entity_id,
            "changes": self.changes,
            "confidence": self.confidence,
            "provenance": self.provenance,
            "metadata": self.metadata,
        }


class EventBus:
    """
    Simple in-process event bus.

    For distributed deployments, this should be backed by
    Redis Pub/Sub, NATS, or a proper message queue.
    """

    def __init__(self) -> None:
        self._handlers: Dict[EventType, List[Callable[[Event], None]]] = {}
        self._global_handlers: List[Callable[[Event], None]] = []
        self._history: List[Event] = []
        self._max_history: int = 10_000

    def subscribe(self, event_type: EventType, handler: Callable[[Event], None]) -> None:
        """Subscribe to a specific event type."""
        self._handlers.setdefault(event_type, []).append(handler)

    def subscribe_all(self, handler: Callable[[Event], None]) -> None:
        """Subscribe to all events."""
        self._global_handlers.append(handler)

    def publish(self, event: Event) -> None:
        """Publish an event to all subscribers."""
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        for handler in self._handlers.get(event.type, []):
            handler(event)
        for handler in self._global_handlers:
            handler(event)

    def get_history(self, event_type: Optional[EventType] = None, limit: int = 100) -> List[Event]:
        """Get recent event history, optionally filtered by type."""
        events = self._history
        if event_type:
            events = [e for e in events if e.type == event_type]
        return events[-limit:]


# Global event bus singleton
_default_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get or create the global event bus."""
    global _default_bus
    if _default_bus is None:
        _default_bus = EventBus()
    return _default_bus


__all__ = [
    "Event",
    "EventType",
    "EventBus",
    "get_event_bus",
]

