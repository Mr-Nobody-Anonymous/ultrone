"""Immutable Event Sourcing schemas for ULTRONE deterministic provenance."""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class EventType(str, Enum):
    """Exhaustive catalog of immutable operational events."""
    ObservationReceived = "ObservationReceived"
    SensorFusionCompleted = "SensorFusionCompleted"
    WorldEstimateUpdated = "WorldEstimateUpdated"
    PlanGenerated = "PlanGenerated"
    PlanRanked = "PlanRanked"
    ActionProposed = "ActionProposed"
    PolicyChecked = "PolicyChecked"
    ActionApproved = "ActionApproved"
    ActionRejected = "ActionRejected"
    DeviceCommandIssued = "DeviceCommandIssued"
    DeviceAcknowledged = "DeviceAcknowledged"
    DeviceStateChanged = "DeviceStateChanged"
    OutcomeObserved = "OutcomeObserved"
    ModelUpdated = "ModelUpdated"
    BenchmarkCompleted = "BenchmarkCompleted"
    PromotionApproved = "PromotionApproved"
    PromotionRejected = "PromotionRejected"
    FaultInjected = "FaultInjected"


@dataclass(frozen=True)
class ImmutableEvent:
    """Cryptographically chained immutable event record."""
    event_id: str
    event_type: EventType
    trace_id: str
    logical_tick: int
    timestamp: float
    payload: Dict[str, Any]
    payload_hash: str
    previous_event_hash: Optional[str] = None

    @staticmethod
    def create(
        event_type: EventType,
        trace_id: str,
        logical_tick: int,
        payload: Dict[str, Any],
        previous_event_hash: Optional[str] = None,
    ) -> ImmutableEvent:
        payload_serialized = json.dumps(payload, sort_keys=True)
        p_hash = hashlib.sha256(payload_serialized.encode("utf-8")).hexdigest()
        event_id = f"evt-{uuid.uuid4().hex[:12]}"
        now = time.time()
        return ImmutableEvent(
            event_id=event_id,
            event_type=event_type,
            trace_id=trace_id,
            logical_tick=logical_tick,
            timestamp=now,
            payload=payload,
            payload_hash=p_hash,
            previous_event_hash=previous_event_hash,
        )

    def compute_event_hash(self) -> str:
        """Compute chained hash of this event including predecessor hash."""
        token = f"{self.event_id}:{self.event_type.value}:{self.trace_id}:{self.logical_tick}:{self.payload_hash}:{self.previous_event_hash}"
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "trace_id": self.trace_id,
            "logical_tick": self.logical_tick,
            "timestamp": self.timestamp,
            "payload": self.payload,
            "payload_hash": self.payload_hash,
            "previous_event_hash": self.previous_event_hash,
            "event_hash": self.compute_event_hash(),
        }
