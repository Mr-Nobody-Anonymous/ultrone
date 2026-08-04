# Copyright (c) Ultrone Contributors. All rights reserved.
"""Active perception for curiosity-driven sensing.

Implements:

* curiosity-driven exploration
* saliency map computation
* observation scheduling
* sensor tasking based on information gain
* entropy reduction targets
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

from .information_gain import InformationGainEstimator
from .types import TrackedEntity, utc_now

__all__ = [
    "PerceptionAction",
    "ActivePerception",
    "ActivePerceptionConfig",
]


@dataclass
class PerceptionAction:
    """A recommended sensing action."""

    sensor_id: str
    entity_id: str
    action_type: str  # "observe", "track", "explore"
    priority: float
    expected_gain: float = 0.0
    reason: str = ""
    scheduled_at: datetime = field(default_factory=utc_now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ActivePerceptionConfig:
    """Configuration for active perception."""

    def __init__(
        self,
        *,
        curiosity_weight: float = 0.3,
        information_gain_weight: float = 0.4,
        uncertainty_weight: float = 0.3,
        exploration_bonus: float = 0.1,
        min_gain_threshold: float = 0.01,
    ) -> None:
        self.curiosity_weight = curiosity_weight
        self.information_gain_weight = information_gain_weight
        self.uncertainty_weight = uncertainty_weight
        self.exploration_bonus = exploration_bonus
        self.min_gain_threshold = min_gain_threshold


class ActivePerception:
    """Recommends sensing actions to maximize information gain."""

    def __init__(
        self,
        *,
        config: Optional[ActivePerceptionConfig] = None,
        information_gain_estimator: Optional[InformationGainEstimator] = None,
    ) -> None:
        self._config = config or ActivePerceptionConfig()
        self._ig_estimator = information_gain_estimator or InformationGainEstimator()
        self._actions: List[PerceptionAction] = []
        self._explored: Dict[str, int] = {}
        self._sensor_noises: Dict[str, float] = {}

    def register_sensor_noise(self, sensor_id: str, noise: float) -> None:
        """Register the measurement noise of a sensor."""
        self._sensor_noises[sensor_id] = noise

    def recommend_actions(
        self,
        entities: Sequence[TrackedEntity],
        *,
        sensor_ids: Optional[List[str]] = None,
    ) -> List[PerceptionAction]:
        """Recommend sensing actions for a set of entities."""
        sensors = sensor_ids or list(self._sensor_noises.keys())
        if not sensors:
            sensors = ["default_sensor"]
            self._sensor_noises["default_sensor"] = 0.1

        actions: List[PerceptionAction] = []
        for entity in entities:
            key = str(entity.entity_id)
            belief = entity.belief

            if belief is None:
                continue

            # Compute information gain for each sensor.
            gains = self._ig_estimator.rank_sensors(
                belief,
                {s: self._sensor_noises.get(s, 0.1) for s in sensors},
                entity_id=key,
            )

            for gain in gains:
                if gain.expected_gain < self._config.min_gain_threshold:
                    continue

                # Curiosity bonus for unexplored entities.
                exploration_count = self._explored.get(key, 0)
                curiosity = np.exp(-exploration_count) * self._config.exploration_bonus

                # Uncertainty component.
                uncertainty = belief.uncertainty()
                uncertainty_score = 1.0 / (1.0 + uncertainty) if np.isfinite(uncertainty) else 1.0

                priority = (
                    self._config.information_gain_weight * gain.expected_gain
                    + self._config.uncertainty_weight * uncertainty_score
                    + self._config.curiosity_weight * curiosity
                )

                action = PerceptionAction(
                    sensor_id=gain.sensor_id,
                    entity_id=key,
                    action_type="observe",
                    priority=float(np.clip(priority, 0.0, 1.0)),
                    expected_gain=gain.expected_gain,
                    reason=f"IG={gain.expected_gain:.3f} unc={uncertainty_score:.2f}",
                )
                actions.append(action)
                self._explored[key] = exploration_count + 1

        actions.sort(key=lambda a: a.priority, reverse=True)
        self._actions.extend(actions)
        return actions

    def saliency_map(
        self, entities: Sequence[TrackedEntity]
    ) -> Dict[str, float]:
        """Compute a saliency map over entities."""
        saliency: Dict[str, float] = {}
        for entity in entities:
            key = str(entity.entity_id)
            uncertainty = entity.uncertainty
            uncertainty_score = 1.0 / (1.0 + uncertainty) if np.isfinite(uncertainty) else 1.0
            saliency[key] = uncertainty_score * entity.confidence
        return saliency

    def schedule_observations(
        self,
        entities: Sequence[TrackedEntity],
        *,
        max_actions: int = 10,
    ) -> List[PerceptionAction]:
        """Schedule the top observation actions."""
        actions = self.recommend_actions(entities)
        return actions[:max_actions]

    def actions(self, limit: Optional[int] = None) -> List[PerceptionAction]:
        actions = self._actions
        if limit is not None:
            actions = actions[-limit:]
        return list(actions)

    def clear(self) -> None:
        self._actions.clear()
        self._explored.clear()