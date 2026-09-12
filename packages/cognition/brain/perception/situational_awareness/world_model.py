# Copyright (c) Ultrone Contributors. All rights reserved.
"""Continuous digital twin maintained by the awareness engine.

The world model holds entities, spatial/semantic/temporal/causal/knowledge
graphs, observation history, and predicted futures. It provides an immutable
:class:`WorldSnapshot` for consumers and emits :class:`WorldStateChanged`
events after every committed tick.

This module intentionally depends only on ``types``, ``events``, and
``telemetry`` so it can be imported by every subsystem without circular
imports.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence, Set

from .events import EntityUpdated, EventBus, WorldStateChanged
from .telemetry import PerformanceTelemetry
from .types import (
    BeliefDistribution,
    EntityID,
    EntityFilter,
    EntityState,
    Observation,
    PredictedState,
    Relationship,
    RelationshipType,
    TrackedEntity,
    Vector3,
    WorldSnapshot,
    utc_now,
)

__all__ = [
    "WorldModel",
    "WorldModelConfig",
    "EntityNotFoundError",
]


class EntityNotFoundError(KeyError):
    """Raised when an entity is accessed by an unknown ID."""


class WorldModelConfig:
    """Configuration for the world model."""

    def __init__(
        self,
        *,
        max_entities: int = 100_000,
        max_history_per_entity: int = 500,
        stale_entity_threshold_seconds: float = 300.0,
        prune_stale_entities: bool = True,
        track_history: bool = True,
    ) -> None:
        self.max_entities = max_entities
        self.max_history_per_entity = max_history_per_entity
        self.stale_entity_threshold_seconds = stale_entity_threshold_seconds
        self.prune_stale_entities = prune_stale_entities
        self.track_history = track_history


class WorldModel:
    """Thread-safe digital twin of the observed world.

    Provides:

    * entity CRUD with typed IDs
    * belief, confidence, and uncertainty tracking
    * history recording with bounded size
    * relationship management (shared spatial graph)
    * immutable snapshotting for consumers
    * filter-based queries
    * stale entity pruning
    """

    def __init__(
        self,
        *,
        config: Optional[WorldModelConfig] = None,
        event_bus: Optional[EventBus] = None,
        telemetry: Optional[PerformanceTelemetry] = None,
    ) -> None:
        self._config = config or WorldModelConfig()
        self._event_bus = event_bus
        self._telemetry = telemetry

        self._entities: Dict[str, TrackedEntity] = {}
        self._relationships: Dict[str, Relationship] = {}
        self._observations: Dict[str, Observation] = {}
        self._sequence: int = 0
        self._changed_entity_ids: Set[str] = set()

    # ------------------------------------------------------------------
    # Entity management
    # ------------------------------------------------------------------

    def upsert_entity(self, entity: TrackedEntity) -> TrackedEntity:
        """Insert a new entity or replace an existing one."""
        key = str(entity.entity_id)
        entity.updated_at = utc_now()
        self._entities[key] = entity

        if self._config.track_history:
            entity.history.append(entity.state)
            if len(entity.history) > self._config.max_history_per_entity:
                entity.history = entity.history[
                    -self._config.max_history_per_entity :
                ]

        self._changed_entity_ids.add(key)
        if self._event_bus is not None:
            self._event_bus.publish_sync(
                EntityUpdated(
                    entity_id=key,
                    confidence=entity.confidence,
                    uncertainty=entity.uncertainty,
                    changed_fields=["*"],
                )
            )
        return entity

    def create_entity(
        self,
        *,
        entity_type: Any,
        category: Any,
        position: Optional[Vector3] = None,
        state: Optional[EntityState] = None,
        confidence: float = 0.5,
        belief: Optional[BeliefDistribution] = None,
        disposition: Any = None,
    ) -> TrackedEntity:
        """Convenience constructor that creates a fresh tracked entity."""
        from .types import Disposition

        entity_state = state or EntityState(position=position or Vector3())
        entity = TrackedEntity(
            entity_type=entity_type,
            category=category,
            state=entity_state,
            confidence=confidence,
            belief=belief
            or BeliefDistribution.deterministic(entity_state.state_vector().tolist()),
            disposition=disposition or Disposition.UNKNOWN,
        )
        return self.upsert_entity(entity)

    def get_entity(self, entity_id: EntityID) -> Optional[TrackedEntity]:
        return self._entities.get(str(entity_id))

    def get_entity_required(self, entity_id: EntityID) -> TrackedEntity:
        entity = self.get_entity(entity_id)
        if entity is None:
            raise EntityNotFoundError(f"Unknown entity: {entity_id}")
        return entity

    def update_entity(
        self,
        entity_id: EntityID,
        *,
        state: Optional[EntityState] = None,
        confidence: Optional[float] = None,
        uncertainty: Optional[float] = None,
        belief: Optional[BeliefDistribution] = None,
        inferred_properties: Optional[Dict[str, Any]] = None,
        labels: Optional[Dict[str, str]] = None,
        **attribute_updates: Any,
    ) -> TrackedEntity:
        """In-place update of an entity's state and metadata."""
        entity = self.get_entity_required(entity_id)
        changed: List[str] = []

        if state is not None:
            if self._config.track_history:
                entity.history.append(entity.state)
                if len(entity.history) > self._config.max_history_per_entity:
                    entity.history = entity.history[
                        -self._config.max_history_per_entity :
                    ]
            entity.state = state
            entity.updated_at = utc_now()
            changed.append("state")

        if confidence is not None:
            entity.confidence = max(0.0, min(1.0, confidence))
            changed.append("confidence")

        if uncertainty is not None:
            entity.uncertainty = uncertainty
            changed.append("uncertainty")

        if belief is not None:
            entity.belief = belief
            changed.append("belief")

        if inferred_properties:
            entity.inferred_properties.update(inferred_properties)
            changed.append("inferred_properties")

        if labels:
            entity.labels.update(labels)
            changed.append("labels")

        if attribute_updates:
            entity.state.attributes.update(attribute_updates)
            changed.append("attributes")

        self._changed_entity_ids.add(str(entity_id))

        if self._event_bus is not None:
            self._event_bus.publish_sync(
                EntityUpdated(
                    entity_id=str(entity_id),
                    confidence=entity.confidence,
                    uncertainty=entity.uncertainty,
                    changed_fields=changed,
                )
            )
        return entity

    def delete_entity(self, entity_id: EntityID) -> bool:
        key = str(entity_id)
        removed = self._entities.pop(key, None) is not None
        if removed:
            # Remove relationships touching this entity.
            to_remove = [
                rid
                for rid, rel in self._relationships.items()
                if rel.source_id == entity_id or rel.target_id == entity_id
            ]
            for rid in to_remove:
                self._relationships.pop(rid, None)
            self._changed_entity_ids.add(key)
        return removed

    def entity_count(self) -> int:
        return len(self._entities)

    # ------------------------------------------------------------------
    # Relationship management
    # ------------------------------------------------------------------

    def add_relationship(
        self,
        source_id: EntityID,
        target_id: EntityID,
        relationship_type: RelationshipType,
        *,
        confidence: float = 0.5,
        attributes: Optional[Dict[str, Any]] = None,
        relationship_id: Optional[str] = None,
    ) -> Relationship:
        self.get_entity_required(source_id)
        self.get_entity_required(target_id)

        relationship_id = relationship_id or f"{source_id}-{target_id}-{relationship_type.value}"
        relationship = Relationship(
            relationship_id=relationship_id,
            source_id=source_id,
            target_id=target_id,
            relationship_type=relationship_type,
            confidence=confidence,
            attributes=attributes or {},
        )
        self._relationships[relationship_id] = relationship

        # Bidirectional graph bookkeeping on entities.
        source = self._entities[str(source_id)]
        target = self._entities[str(target_id)]
        if relationship_id not in source.relationship_ids:
            source.relationship_ids.append(relationship_id)
        if relationship_id not in target.relationship_ids:
            target.relationship_ids.append(relationship_id)

        return relationship

    def update_relationship(
        self,
        relationship_id: str,
        *,
        confidence: Optional[float] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Optional[Relationship]:
        rel = self._relationships.get(relationship_id)
        if rel is None:
            return None
        if confidence is not None:
            rel.confidence = max(0.0, min(1.0, confidence))
        if attributes:
            rel.attributes.update(attributes)
        rel.last_updated = utc_now()
        return rel

    def remove_relationship(self, relationship_id: str) -> bool:
        rel = self._relationships.pop(relationship_id, None)
        if rel is None:
            return False
        source = self._entities.get(str(rel.source_id))
        target = self._entities.get(str(rel.target_id))
        if source is not None and relationship_id in source.relationship_ids:
            source.relationship_ids.remove(relationship_id)
        if target is not None and relationship_id in target.relationship_ids:
            target.relationship_ids.remove(relationship_id)
        return True

    def relationships_for(self, entity_id: EntityID) -> List[Relationship]:
        return [
            rel
            for rel in self._relationships.values()
            if rel.source_id == entity_id or rel.target_id == entity_id
        ]

    def relationship_count(self) -> int:
        return len(self._relationships)

    # ------------------------------------------------------------------
    # Observations
    # ------------------------------------------------------------------

    def record_observation(self, observation: Observation) -> None:
        self._observations[observation.observation_id] = observation
        if observation.entity_id is not None:
            entity = self._entities.get(str(observation.entity_id))
            if entity is not None:
                entity.observation_ids.append(observation.observation_id)
                entity.observation_count += 1
                entity.last_observed_at = observation.timestamp

    def observations_for(self, entity_id: EntityID) -> List[Observation]:
        eid = str(entity_id)
        return [
            obs
            for obs in self._observations.values()
            if obs.entity_id is not None and str(obs.entity_id) == eid
        ]

    def observation_count(self) -> int:
        return len(self._observations)

    # ------------------------------------------------------------------
    # Prediction storage
    # ------------------------------------------------------------------

    def store_predictions(
        self, entity_id: EntityID, predictions: Sequence[PredictedState]
    ) -> None:
        entity = self.get_entity_required(entity_id)
        entity.predicted_states = list(predictions)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def query(self, entity_filter: Optional[EntityFilter] = None) -> List[TrackedEntity]:
        entities = list(self._entities.values())
        if entity_filter is None:
            return entities

        result: List[TrackedEntity] = []
        for entity in entities:
            if (
                entity_filter.categories is not None
                and entity.category not in entity_filter.categories
            ):
                continue
            if (
                entity_filter.entity_types is not None
                and entity.entity_type not in entity_filter.entity_types
            ):
                continue
            if (
                entity_filter.dispositions is not None
                and entity.disposition not in entity_filter.dispositions
            ):
                continue
            if (
                entity_filter.min_confidence is not None
                and entity.confidence < entity_filter.min_confidence
            ):
                continue
            if (
                entity_filter.max_uncertainty is not None
                and entity.uncertainty > entity_filter.max_uncertainty
            ):
                continue
            if (
                entity_filter.within_radius_of is not None
                and entity_filter.radius is not None
            ):
                if (
                    entity.state.position.distance_to(entity_filter.within_radius_of)
                    > entity_filter.radius
                ):
                    continue
            if (
                entity_filter.updated_after is not None
                and entity.updated_at < entity_filter.updated_after
            ):
                continue
            result.append(entity)
        return result

    def entities_in_radius(self, center: Vector3, radius: float) -> List[TrackedEntity]:
        return [
            e
            for e in self._entities.values()
            if e.state.position.distance_to(center) <= radius
        ]

    def nearest_entity(
        self, center: Vector3, *, category: Any = None
    ) -> Optional[TrackedEntity]:
        best: Optional[TrackedEntity] = None
        best_dist = float("inf")
        for entity in self._entities.values():
            if category is not None and entity.category != category:
                continue
            dist = entity.state.position.distance_to(center)
            if dist < best_dist:
                best_dist = dist
                best = entity
        return best

    # ------------------------------------------------------------------
    # Snapshot / lifecycle
    # ------------------------------------------------------------------

    def snapshot(self) -> WorldSnapshot:
        """Capture an immutable snapshot of the world state."""
        return WorldSnapshot(
            captured_at=utc_now(),
            entities=list(self._entities.values()),
            relationships=list(self._relationships.values()),
            observations=list(self._observations.values()),
            sequence=self._sequence,
        )

    def commit_tick(self) -> WorldSnapshot:
        """Commit a temporal tick and emit the world-state-changed event."""
        self._sequence += 1
        snapshot = self.snapshot()
        changed = list(self._changed_entity_ids)
        self._changed_entity_ids.clear()

        if self._event_bus is not None:
            self._event_bus.publish_sync(
                WorldStateChanged(
                    sequence=self._sequence,
                    entity_count=len(self._entities),
                    relationship_count=len(self._relationships),
                    changed_entity_ids=changed,
                )
            )
        return snapshot

    def prune_stale(self, now: Optional[datetime] = None) -> int:
        """Remove entities not observed within the stale threshold."""
        if not self._config.prune_stale_entities:
            return 0
        now = now or utc_now()
        threshold = timedelta(seconds=self._config.stale_entity_threshold_seconds)
        stale_keys: List[str] = []
        for key, entity in self._entities.items():
            last_seen = entity.last_observed_at or entity.updated_at
            if now - last_seen > threshold:
                stale_keys.append(key)
        for key in stale_keys:
            self._entities.pop(key, None)
        return len(stale_keys)

    def clear(self) -> None:
        self._entities.clear()
        self._relationships.clear()
        self._observations.clear()
        self._changed_entity_ids.clear()

    @property
    def sequence(self) -> int:
        return self._sequence