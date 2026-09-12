# Copyright (c) Ultrone Contributors. All rights reserved.
"""Authoritative unified World State container."""
from __future__ import annotations

import time
from typing import Dict, List, Optional
from packages.core.entities import Entity
from packages.core.events import Event, EventType, get_event_bus


class WorldState:
    """Authoritative operational state container."""

    def __init__(self) -> None:
        self._entities: Dict[str, Entity] = {}
        self._updated_at: float = time.time()
        self._event_bus = get_event_bus()

    def upsert_entity(self, entity: Entity, publish_event: bool = True) -> Entity:
        """Add or update an entity in the world model."""
        is_new = entity.entity_id not in self._entities
        self._entities[entity.entity_id] = entity
        self._updated_at = time.time()

        if publish_event:
            evt_type = EventType.ENTITY_CREATED if is_new else EventType.ENTITY_UPDATED
            self._event_bus.publish(Event(
                type=evt_type,
                entity_id=entity.entity_id,
                source="world_model",
                changes=entity.to_dict(),
                confidence=entity.confidence,
            ))
        return entity

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get an entity by ID."""
        return self._entities.get(entity_id)

    def remove_entity(self, entity_id: str, publish_event: bool = True) -> Optional[Entity]:
        """Remove an entity from the world model."""
        entity = self._entities.pop(entity_id, None)
        if entity and publish_event:
            self._event_bus.publish(Event(
                type=EventType.ENTITY_DESTROYED,
                entity_id=entity_id,
                source="world_model",
            ))
        return entity

    def all_entities(self) -> List[Entity]:
        """Get all entities currently tracked."""
        return list(self._entities.values())

    def count(self) -> int:
        """Count tracked entities."""
        return len(self._entities)


_default_world_state: Optional[WorldState] = None


def get_world_state() -> WorldState:
    global _default_world_state
    if _default_world_state is None:
        _default_world_state = WorldState()
    return _default_world_state
