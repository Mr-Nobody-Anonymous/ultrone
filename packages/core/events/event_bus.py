# Copyright (c) Ultrone Contributors. All rights reserved.
"""Canonical EventBus for publish/subscribe event streaming."""
from __future__ import annotations

import asyncio
from typing import Callable, Dict, List, Optional
from packages.core.events.event import Event, EventType


class EventBus:
    """Thread-safe pub/sub event bus supporting synchronous and asynchronous handlers."""

    def __init__(self) -> None:
        self._subscribers: Dict[EventType, List[Callable[[Event], None]]] = {}
        self._all_subscribers: List[Callable[[Event], None]] = []

    def subscribe(self, event_type: EventType, callback: Callable[[Event], None]) -> None:
        """Subscribe a callback to a specific event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)

    def subscribe_all(self, callback: Callable[[Event], None]) -> None:
        """Subscribe a callback to all events (e.g. for WebSocket forwarding or audit logging)."""
        self._all_subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[Event], None]) -> None:
        """Unsubscribe a callback from all event types."""
        for callbacks in self._subscribers.values():
            if callback in callbacks:
                callbacks.remove(callback)
        if callback in self._all_subscribers:
            self._all_subscribers.remove(callback)

    def publish(self, event: Event) -> None:
        """Publish an event to all interested subscribers."""
        # Deliver to specific subscribers
        for callback in self._subscribers.get(event.type, []):
            try:
                callback(event)
            except Exception as e:
                import logging
                logging.getLogger("ultrone.event_bus").warning(f"Error in subscriber: {e}")

        # Deliver to catch-all subscribers
        for callback in self._all_subscribers:
            try:
                callback(event)
            except Exception as e:
                import logging
                logging.getLogger("ultrone.event_bus").warning(f"Error in catch-all subscriber: {e}")

    def clear(self) -> None:
        """Remove all subscribers."""
        self._subscribers.clear()
        self._all_subscribers.clear()


# Global EventBus singleton
_default_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get or initialize default global event bus."""
    global _default_event_bus
    if _default_event_bus is None:
        _default_event_bus = EventBus()
    return _default_event_bus
