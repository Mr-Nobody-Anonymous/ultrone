# Copyright (c) Ultrone Contributors. All rights reserved.
"""Observation history for temporal analysis.

Maintains a bounded, queryable history of observations for each entity and
sensor. Supports:

* per-entity observation history
* per-sensor observation history
* time-window queries
* observation statistics
"""

from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime
from typing import Deque, Dict, List, Optional

from .types import EntityID, Observation

__all__ = [
    "ObservationHistory",
    "ObservationHistoryConfig",
]


class ObservationHistoryConfig:
    """Configuration for the observation history."""

    def __init__(
        self,
        *,
        max_observations_per_entity: int = 1000,
        max_observations_per_sensor: int = 1000,
        max_total_observations: int = 100_000,
    ) -> None:
        self.max_observations_per_entity = max_observations_per_entity
        self.max_observations_per_sensor = max_observations_per_sensor
        self.max_total_observations = max_total_observations


class ObservationHistory:
    """Bounded observation history with per-entity and per-sensor indexing."""

    def __init__(self, *, config: Optional[ObservationHistoryConfig] = None) -> None:
        self._config = config or ObservationHistoryConfig()
        self._by_entity: Dict[str, Deque[Observation]] = defaultdict(
            lambda: deque(maxlen=self._config.max_observations_per_entity)
        )
        self._by_sensor: Dict[str, Deque[Observation]] = defaultdict(
            lambda: deque(maxlen=self._config.max_observations_per_sensor)
        )
        self._all: Deque[Observation] = deque(maxlen=self._config.max_total_observations)

    def add(self, observation: Observation) -> None:
        """Record an observation in the history."""
        self._all.append(observation)
        if observation.entity_id is not None:
            self._by_entity[str(observation.entity_id)].append(observation)
        self._by_sensor[observation.sensor_id].append(observation)

    def for_entity(self, entity_id: EntityID) -> List[Observation]:
        """Get all observations for an entity (most recent last)."""
        return list(self._by_entity.get(str(entity_id), []))

    def for_sensor(self, sensor_id: str) -> List[Observation]:
        """Get all observations from a sensor (most recent last)."""
        return list(self._by_sensor.get(sensor_id, []))

    def since(self, timestamp: datetime) -> List[Observation]:
        """Get all observations since a given timestamp."""
        return [obs for obs in self._all if obs.timestamp >= timestamp]

    def in_window(
        self, start: datetime, end: datetime
    ) -> List[Observation]:
        """Get observations within a time window."""
        return [
            obs for obs in self._all if start <= obs.timestamp <= end
        ]

    def last_n(self, n: int) -> List[Observation]:
        """Get the last n observations."""
        return list(self._all)[-n:]

    def entity_observation_count(self, entity_id: EntityID) -> int:
        return len(self._by_entity.get(str(entity_id), []))

    def sensor_observation_count(self, sensor_id: str) -> int:
        return len(self._by_sensor.get(sensor_id, []))

    def total_count(self) -> int:
        return len(self._all)

    def entity_ids(self) -> List[str]:
        return list(self._by_entity.keys())

    def sensor_ids(self) -> List[str]:
        return list(self._by_sensor.keys())

    def clear(self) -> None:
        self._by_entity.clear()
        self._by_sensor.clear()
        self._all.clear()