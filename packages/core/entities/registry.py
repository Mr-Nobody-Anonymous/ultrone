# Copyright (c) Ultrone Contributors. All rights reserved.
"""Entity Registry for canonical entity lifecycle management."""
from __future__ import annotations

from typing import Dict, List, Optional
from packages.core.entities import Entity, EntityStatus


class EntityRegistry:
    """Thread-safe in-memory entity registry."""

    def __init__(self) -> None:
        self._entities: Dict[str, Entity] = {}

    def register(self, entity: Entity) -> Entity:
        """Register or update an entity."""
        self._entities[entity.entity_id] = entity
        return entity

    def get(self, entity_id: str) -> Optional[Entity]:
        """Retrieve entity by ID."""
        return self._entities.get(entity_id)

    def list_all(self) -> List[Entity]:
        """Return all tracked entities."""
        return list(self._entities.values())

    def filter_by_type(self, entity_type: str) -> List[Entity]:
        """Filter entities by type."""
        return [e for e in self._entities.values() if e.type == entity_type]

    def filter_by_status(self, status: EntityStatus) -> List[Entity]:
        """Filter entities by status."""
        return [e for e in self._entities.values() if e.status == status]

    def remove(self, entity_id: str) -> Optional[Entity]:
        """Remove entity from registry."""
        return self._entities.pop(entity_id, None)

    def count(self) -> int:
        """Total number of tracked entities."""
        return len(self._entities)


# Global registry singleton
_default_registry: Optional[EntityRegistry] = None


def get_entity_registry() -> EntityRegistry:
    """Get or initialize default global entity registry."""
    global _default_registry
    if _default_registry is None:
        _default_registry = EntityRegistry()
    return _default_registry
