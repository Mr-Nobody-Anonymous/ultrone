# Copyright (c) Ultrone Contributors. All rights reserved.
"""Canonical Event definitions."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


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
    """Canonical ULTRONE Event."""
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
            "type": self.type.value if hasattr(self.type, "value") else str(self.type),
            "timestamp": self.timestamp,
            "source": self.source,
            "entity_id": self.entity_id,
            "changes": self.changes,
            "confidence": self.confidence,
            "provenance": self.provenance,
            "metadata": self.metadata,
        }
