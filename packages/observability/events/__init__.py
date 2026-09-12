"""
ULTRONE Event Bus — Observability Layer.

Re-exports the canonical event bus from packages.core.events
and adds observability-specific event handling (logging,
metrics emission, tracing integration).
"""
try:
    from packages.core.events import Event, EventType, EventBus, get_event_bus

    __all__ = ["Event", "EventType", "EventBus", "get_event_bus"]
except ImportError:
    __all__ = []
