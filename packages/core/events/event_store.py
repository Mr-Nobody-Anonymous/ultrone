# Copyright (c) Ultrone Contributors. All rights reserved.
"""Event Store for querying historical events."""
from __future__ import annotations

from typing import List, Optional
from packages.core.events.event import Event, EventType


class EventStore:
    """In-memory event store with query filtering."""

    def __init__(self, max_events: int = 10000) -> None:
        self._events: List[Event] = []
        self._max_events = max_events

    def append(self, event: Event) -> None:
        """Store an event."""
        self._events.append(event)
        if len(self._events) > self._max_events:
            self._events.pop(0)

    def query(
        self,
        entity_id: Optional[str] = None,
        event_type: Optional[EventType] = None,
        source: Optional[str] = None,
        limit: int = 100,
    ) -> List[Event]:
        """Query stored events by entity, type, or source."""
        results = self._events
        if entity_id:
            results = [e for e in results if e.entity_id == entity_id]
        if event_type:
            results = [e for e in results if e.type == event_type]
        if source:
            results = [e for e in results if e.source == source]
        return results[-limit:]

    def count(self) -> int:
        return len(self._events)

    def clear(self) -> None:
        self._events.clear()


_default_store: Optional[EventStore] = None


def get_event_store() -> EventStore:
    global _default_store
    if _default_store is None:
        _default_store = EventStore()
    return _default_store
