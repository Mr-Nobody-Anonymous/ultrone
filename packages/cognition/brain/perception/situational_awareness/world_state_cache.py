# Copyright (c) Ultrone Contributors. All rights reserved.
"""World state cache for fast access to frequently queried state.

Provides a bounded, time-aware cache of world state snapshots and entity
lookups to avoid repeated recomputation.
"""

from __future__ import annotations

from collections import OrderedDict
from datetime import datetime
from typing import List, Optional, Tuple

from .types import EntityID, TrackedEntity, WorldSnapshot, utc_now

__all__ = [
    "WorldStateCache",
    "WorldStateCacheConfig",
]


class WorldStateCacheConfig:
    """Configuration for the world state cache."""

    def __init__(
        self,
        *,
        max_entries: int = 1000,
        ttl_seconds: float = 5.0,
        max_snapshots: int = 100,
    ) -> None:
        self.max_entries = max_entries
        self.ttl_seconds = ttl_seconds
        self.max_snapshots = max_snapshots


class WorldStateCache:
    """Bounded, time-aware cache for world state."""

    def __init__(self, *, config: Optional[WorldStateCacheConfig] = None) -> None:
        self._config = config or WorldStateCacheConfig()
        self._entity_cache: OrderedDict[str, Tuple[datetime, TrackedEntity]] = OrderedDict()
        self._snapshots: List[WorldSnapshot] = []

    def put_entity(self, entity: TrackedEntity) -> None:
        """Cache an entity with a timestamp."""
        key = str(entity.entity_id)
        self._entity_cache[key] = (utc_now(), entity)
        self._entity_cache.move_to_end(key)
        while len(self._entity_cache) > self._config.max_entries:
            self._entity_cache.popitem(last=False)

    def get_entity(self, entity_id: EntityID) -> Optional[TrackedEntity]:
        """Get a cached entity if not expired."""
        key = str(entity_id)
        entry = self._entity_cache.get(key)
        if entry is None:
            return None
        timestamp, entity = entry
        if (utc_now() - timestamp).total_seconds() > self._config.ttl_seconds:
            self._entity_cache.pop(key, None)
            return None
        return entity

    def put_snapshot(self, snapshot: WorldSnapshot) -> None:
        """Cache a world snapshot."""
        self._snapshots.append(snapshot)
        if len(self._snapshots) > self._config.max_snapshots:
            self._snapshots = self._snapshots[-self._config.max_snapshots :]

    def latest_snapshot(self) -> Optional[WorldSnapshot]:
        return self._snapshots[-1] if self._snapshots else None

    def snapshots(self, limit: Optional[int] = None) -> List[WorldSnapshot]:
        snapshots = self._snapshots
        if limit is not None:
            snapshots = snapshots[-limit:]
        return list(snapshots)

    def invalidate(self, entity_id: EntityID) -> None:
        self._entity_cache.pop(str(entity_id), None)

    def clear(self) -> None:
        self._entity_cache.clear()
        self._snapshots.clear()

    @property
    def entity_cache_size(self) -> int:
        return len(self._entity_cache)

    @property
    def snapshot_count(self) -> int:
        return len(self._snapshots)