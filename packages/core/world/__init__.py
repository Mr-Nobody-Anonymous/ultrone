"""
ULTRONE World Module.

Canonical re-export of the world model. Everything should talk
to one world model:

    WORLD MODEL
        │
    ┌───┼───┐
    ↓   ↓   ↓
  Entities Events State
    │   │   │
    perception  simulation  external data
        │
      cognition

This module re-exports from packages.core.world_model for
backward compatibility while providing the canonical import path.
"""
try:
    from packages.core.world_model import *  # noqa: F401, F403
except ImportError:
    pass  # world_model may not be fully initialized yet

from packages.core.entities import Entity, EntityStatus, Position, Velocity
from packages.core.events import Event, EventType, EventBus, get_event_bus

__all__ = [
    "Entity",
    "EntityStatus",
    "Position",
    "Velocity",
    "Event",
    "EventType",
    "EventBus",
    "get_event_bus",
]

