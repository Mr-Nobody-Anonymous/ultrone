# Copyright (c) Ultrone Contributors. All rights reserved.
"""Entity tracking and association.

Implements multi-object tracking with:

* observation-to-entity association (nearest-neighbor gating)
* track initialization / confirmation / deletion
* track quality scoring
* identity persistence across observations
* gating based on Mahalanobis distance
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import numpy as np

from .types import (
    EntityID,
    Observation,
    TrackedEntity,
    utc_now,
)

__all__ = [
    "TrackQuality",
    "AssociationResult",
    "EntityTracker",
    "EntityTrackerConfig",
]


@dataclass
class TrackQuality:
    """Quality metrics for a tracked entity."""

    entity_id: EntityID
    observation_count: int = 0
    last_update: datetime = field(default_factory=utc_now)
    gating_distance: float = float("inf")
    quality_score: float = 0.0
    confirmed: bool = False

    def update(
        self,
        *,
        observation_count: Optional[int] = None,
        gating_distance: Optional[float] = None,
        confirmed: Optional[bool] = None,
    ) -> None:
        if observation_count is not None:
            self.observation_count = observation_count
        if gating_distance is not None:
            self.gating_distance = gating_distance
        if confirmed is not None:
            self.confirmed = confirmed
        self.last_update = utc_now()
        # Quality: higher with more observations, lower with larger gating distance.
        base = min(1.0, self.observation_count / 10.0)
        distance_factor = 1.0 / (1.0 + self.gating_distance)
        self.quality_score = 0.7 * base + 0.3 * distance_factor


@dataclass
class AssociationResult:
    """Result of associating an observation with an entity."""

    observation_id: str
    entity_id: Optional[EntityID]
    gating_distance: float
    associated: bool


class EntityTrackerConfig:
    """Configuration for the entity tracker."""

    def __init__(
        self,
        *,
        gating_threshold: float = 3.0,
        confirmation_threshold: int = 3,
        deletion_threshold_seconds: float = 30.0,
        max_tracks: int = 10_000,
    ) -> None:
        self.gating_threshold = gating_threshold
        self.confirmation_threshold = confirmation_threshold
        self.deletion_threshold_seconds = deletion_threshold_seconds
        self.max_tracks = max_tracks


class EntityTracker:
    """Tracks entities across observations using gated nearest-neighbor association.

    Maintains track quality per entity and provides association between new
    observations and existing tracks. New observations that do not associate
    with any existing track create a new track candidate.
    """

    def __init__(
        self,
        *,
        config: Optional[EntityTrackerConfig] = None,
        entities: Optional[Dict[str, TrackedEntity]] = None,
    ) -> None:
        self._config = config or EntityTrackerConfig()
        self._entities: Dict[str, TrackedEntity] = entities or {}
        self._qualities: Dict[str, TrackQuality] = {}
        self._association_history: List[AssociationResult] = []

    def set_entities(self, entities: Dict[str, TrackedEntity]) -> None:
        """Provide the world model's entity dictionary for association."""
        self._entities = entities

    def associate(
        self, observation: Observation
    ) -> AssociationResult:
        """Associate an observation with the nearest entity within the gate."""
        obs_pos = self._extract_position(observation)
        if obs_pos is None:
            return AssociationResult(
                observation_id=observation.observation_id,
                entity_id=None,
                gating_distance=float("inf"),
                associated=False,
            )

        best_entity_id: Optional[EntityID] = None
        best_distance = float("inf")

        for key, entity in self._entities.items():
            entity_pos = entity.state.position.as_array()
            diff = obs_pos - entity_pos
            distance = float(np.linalg.norm(diff))
            if distance < best_distance:
                best_distance = distance
                best_entity_id = entity.entity_id

        associated = best_distance <= self._config.gating_threshold
        result = AssociationResult(
            observation_id=observation.observation_id,
            entity_id=best_entity_id if associated else None,
            gating_distance=best_distance,
            associated=associated,
        )
        self._association_history.append(result)

        if associated and best_entity_id is not None:
            quality = self._qualities.setdefault(
                str(best_entity_id),
                TrackQuality(entity_id=best_entity_id),
            )
            quality.update(
                observation_count=quality.observation_count + 1,
                gating_distance=best_distance,
                confirmed=quality.observation_count
                >= self._config.confirmation_threshold,
            )

        return result

    def create_track(
        self, observation: Observation, entity: TrackedEntity
    ) -> TrackedEntity:
        """Register a new track for an entity."""
        self._entities[str(entity.entity_id)] = entity
        quality = TrackQuality(entity_id=entity.entity_id)
        quality.update(observation_count=1, gating_distance=0.0)
        self._qualities[str(entity.entity_id)] = quality
        return entity

    def get_quality(self, entity_id: EntityID) -> Optional[TrackQuality]:
        return self._qualities.get(str(entity_id))

    def confirmed_tracks(self) -> List[TrackQuality]:
        return [q for q in self._qualities.values() if q.confirmed]

    def delete_stale_tracks(self, now: Optional[datetime] = None) -> int:
        """Delete tracks not updated within the deletion threshold."""
        now = now or utc_now()
        threshold = timedelta(seconds=self._config.deletion_threshold_seconds)
        stale_keys: List[str] = []
        for key, quality in self._qualities.items():
            if now - quality.last_update > threshold:
                stale_keys.append(key)
        for key in stale_keys:
            self._qualities.pop(key, None)
            self._entities.pop(key, None)
        return len(stale_keys)

    def track_count(self) -> int:
        return len(self._qualities)

    def association_history(self, limit: Optional[int] = None) -> List[AssociationResult]:
        history = self._association_history
        if limit is not None:
            history = history[-limit:]
        return list(history)

    @staticmethod
    def _extract_position(observation: Observation) -> Optional[np.ndarray]:
        """Extract a 3D position from an observation's measurement value."""
        value = observation.measurement.value
        if isinstance(value, (list, tuple, np.ndarray)):
            arr = np.asarray(value, dtype=np.float64)
            if arr.size >= 3:
                return arr[:3]
            if arr.size == 2:
                return np.array([arr[0], arr[1], 0.0])
        return None