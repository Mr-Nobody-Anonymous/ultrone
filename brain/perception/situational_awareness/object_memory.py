# Copyright (c) Ultrone Contributors. All rights reserved.
"""Object memory for persistent entity knowledge.

Maintains long-term knowledge about observed objects, including:

* persistent object records with attributes
* episodic observation history
* semantic memory (class labels, inferred properties)
* associative memory (related objects)
* memory decay and consolidation
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from .types import EntityID, Observation, TrackedEntity, utc_now

__all__ = [
    "ObjectMemoryRecord",
    "ObjectMemory",
    "ObjectMemoryConfig",
]


@dataclass
class ObjectMemoryRecord:
    """Persistent record of knowledge about an object."""

    entity_id: EntityID
    first_seen: datetime = field(default_factory=utc_now)
    last_seen: datetime = field(default_factory=utc_now)
    observation_count: int = 0
    attributes: Dict[str, Any] = field(default_factory=dict)
    semantic_labels: Dict[str, str] = field(default_factory=dict)
    inferred_properties: Dict[str, Any] = field(default_factory=dict)
    associated_entity_ids: Set[str] = field(default_factory=set)
    episodic_summary: List[str] = field(default_factory=list)
    memory_strength: float = 1.0

    def touch(self, observation: Optional[Observation] = None) -> None:
        self.last_seen = utc_now()
        self.observation_count += 1
        if observation is not None:
            self.episodic_summary.append(
                f"{observation.timestamp.isoformat()}: {observation.sensor_id} "
                f"conf={observation.confidence:.2f}"
            )
            if len(self.episodic_summary) > 100:
                self.episodic_summary = self.episodic_summary[-100:]

    def decay(self, half_life_seconds: float) -> None:
        """Exponentially decay memory strength based on time since last seen."""
        age = (utc_now() - self.last_seen).total_seconds()
        self.memory_strength = 0.5 ** (age / half_life_seconds)


class ObjectMemoryConfig:
    """Configuration for object memory."""

    def __init__(
        self,
        *,
        max_records: int = 50_000,
        decay_half_life_seconds: float = 3600.0,
        prune_threshold: float = 0.01,
        prune_enabled: bool = True,
    ) -> None:
        self.max_records = max_records
        self.decay_half_life_seconds = decay_half_life_seconds
        self.prune_threshold = prune_threshold
        self.prune_enabled = prune_enabled


class ObjectMemory:
    """Long-term object memory with decay, consolidation, and association."""

    def __init__(self, *, config: Optional[ObjectMemoryConfig] = None) -> None:
        self._config = config or ObjectMemoryConfig()
        self._records: Dict[str, ObjectMemoryRecord] = {}

    def observe(
        self, entity: TrackedEntity, observation: Optional[Observation] = None
    ) -> ObjectMemoryRecord:
        """Update memory for an entity based on a new observation."""
        key = str(entity.entity_id)
        record = self._records.get(key)
        if record is None:
            record = ObjectMemoryRecord(entity_id=entity.entity_id)
            self._records[key] = record

        record.touch(observation)
        record.attributes.update(entity.state.attributes)
        record.semantic_labels.update(entity.labels)
        record.inferred_properties.update(entity.inferred_properties)

        # Associate with nearby entities (co-occurrence).
        for other_key, other in self._records.items():
            if other_key == key:
                continue
            if str(other.entity_id) in record.associated_entity_ids:
                continue
            record.associated_entity_ids.add(str(other.entity_id))
            other.associated_entity_ids.add(key)

        return record

    def get(self, entity_id: EntityID) -> Optional[ObjectMemoryRecord]:
        return self._records.get(str(entity_id))

    def get_required(self, entity_id: EntityID) -> ObjectMemoryRecord:
        record = self.get(entity_id)
        if record is None:
            raise KeyError(f"No memory record for entity {entity_id}")
        return record

    def recall(self, entity_id: EntityID) -> Optional[ObjectMemoryRecord]:
        """Recall a memory record, applying decay."""
        record = self.get(entity_id)
        if record is not None:
            record.decay(self._config.decay_half_life_seconds)
        return record

    def associate(self, entity_id_a: EntityID, entity_id_b: EntityID) -> None:
        """Explicitly associate two entities in memory."""
        record_a = self.get_required(entity_id_a)
        record_b = self.get_required(entity_id_b)
        record_a.associated_entity_ids.add(str(entity_id_b))
        record_b.associated_entity_ids.add(str(entity_id_a))

    def associated_with(self, entity_id: EntityID) -> List[ObjectMemoryRecord]:
        """Return memory records associated with the given entity."""
        record = self.get(entity_id)
        if record is None:
            return []
        return [
            self._records[aid]
            for aid in record.associated_entity_ids
            if aid in self._records
        ]

    def consolidate(self) -> int:
        """Consolidate memory by pruning weak records. Returns count pruned."""
        if not self._config.prune_enabled:
            return 0
        pruned: List[str] = []
        for key, record in self._records.items():
            record.decay(self._config.decay_half_life_seconds)
            if record.memory_strength < self._config.prune_threshold:
                pruned.append(key)
        for key in pruned:
            self._records.pop(key, None)
        return len(pruned)

    def all(self) -> List[ObjectMemoryRecord]:
        return list(self._records.values())

    def count(self) -> int:
        return len(self._records)

    def clear(self) -> None:
        self._records.clear()