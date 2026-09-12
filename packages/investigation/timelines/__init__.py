"""ULTRONE Investigation - Chronology, timeline reconstruction, and event correlation."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TimelineEvent:
    """An event positioned along an investigative timeline."""
    event_id: str
    timestamp: float
    title: str
    event_type: str
    entity_ids: List[str] = field(default_factory=list)
    location: Optional[Dict[str, float]] = None  # lat, lon, alt
    details: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "title": self.title,
            "event_type": self.event_type,
            "entity_ids": self.entity_ids,
            "location": self.location,
            "details": self.details,
            "confidence": self.confidence,
        }


class EventCorrelator:
    """Correlates disparate sensor detections and events into unified timelines."""

    def __init__(self, time_window_seconds: float = 300.0, spatial_threshold_km: float = 10.0):
        self.time_window = time_window_seconds
        self.spatial_threshold = spatial_threshold_km
        self._events: List[TimelineEvent] = []

    def add_event(self, event: TimelineEvent) -> None:
        self._events.append(event)
        self._events.sort(key=lambda e: e.timestamp)

    def correlate_for_entity(self, entity_id: str) -> List[TimelineEvent]:
        return [e for e in self._events if entity_id in e.entity_ids]

    def get_chronology(self, start_time: float = 0.0, end_time: float = float("inf")) -> List[TimelineEvent]:
        return [e for e in self._events if start_time <= e.timestamp <= end_time]


__all__ = ["TimelineEvent", "EventCorrelator"]
