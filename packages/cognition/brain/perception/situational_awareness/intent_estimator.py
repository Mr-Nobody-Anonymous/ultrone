# Copyright (c) Ultrone Contributors. All rights reserved.
"""Intent estimation for tracked entities.

Estimates the likely intent of entities based on:

* behavioral patterns (velocity, heading, acceleration)
* disposition and category priors
* contextual cues (proximity to assets, terrain)
* temporal behavior consistency
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

from .types import (
    Disposition,
    EntityID,
    TrackedEntity,
    Vector3,
    utc_now,
)

__all__ = [
    "IntentEstimate",
    "IntentEstimator",
    "IntentEstimatorConfig",
]


@dataclass
class IntentEstimate:
    """An estimate of an entity's intent."""

    entity_id: EntityID
    intent: str
    probability: float
    alternative_intents: Dict[str, float] = field(default_factory=dict)
    confidence: float = 0.0
    estimated_at: datetime = field(default_factory=utc_now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class IntentEstimatorConfig:
    """Configuration for the intent estimator."""

    def __init__(
        self,
        *,
        intents: Optional[List[str]] = None,
        approach_speed_threshold: float = 5.0,
        retreat_speed_threshold: float = 5.0,
        min_confidence: float = 0.1,
    ) -> None:
        self.intents = intents or [
            "approach",
            "retreat",
            "patrol",
            "stationary",
            "transit",
            "unknown",
        ]
        self.approach_speed_threshold = approach_speed_threshold
        self.retreat_speed_threshold = retreat_speed_threshold
        self.min_confidence = min_confidence


class IntentEstimator:
    """Estimates entity intent from behavioral and contextual cues."""

    def __init__(self, *, config: Optional[IntentEstimatorConfig] = None) -> None:
        self._config = config or IntentEstimatorConfig()
        self._estimates: List[IntentEstimate] = []
        self._protected_assets: List[Vector3] = []

    def add_protected_asset(self, position: Vector3) -> None:
        self._protected_assets.append(position)

    def estimate(
        self, entity: TrackedEntity, *, now: Optional[datetime] = None
    ) -> IntentEstimate:
        """Estimate the intent of an entity."""
        speed = float(np.linalg.norm(entity.state.velocity.as_array()))
        heading = entity.state.velocity.as_array()
        if np.linalg.norm(heading) > 1e-6:
            heading = heading / np.linalg.norm(heading)
        else:
            heading = np.zeros(3)

        # Compute intent probabilities.
        probs: Dict[str, float] = {intent: 0.0 for intent in self._config.intents}

        # Stationary.
        if speed < 0.5:
            probs["stationary"] = 0.8
            probs["patrol"] = 0.1
            probs["unknown"] = 0.1
        else:
            # Approach / retreat relative to nearest protected asset.
            if self._protected_assets:
                distances = [
                    entity.state.position.distance_to(asset)
                    for asset in self._protected_assets
                ]
                nearest_asset = self._protected_assets[int(np.argmin(distances))]
                to_asset = nearest_asset.as_array() - entity.state.position.as_array()
                if np.linalg.norm(to_asset) > 1e-6:
                    to_asset = to_asset / np.linalg.norm(to_asset)
                    approach = float(np.dot(heading, to_asset))
                    if approach > 0.3 and speed > self._config.approach_speed_threshold:
                        probs["approach"] = 0.7
                        probs["transit"] = 0.2
                        probs["unknown"] = 0.1
                    elif approach < -0.3 and speed > self._config.retreat_speed_threshold:
                        probs["retreat"] = 0.7
                        probs["transit"] = 0.2
                        probs["unknown"] = 0.1
                    else:
                        probs["patrol"] = 0.5
                        probs["transit"] = 0.3
                        probs["unknown"] = 0.2
                else:
                    probs["patrol"] = 0.5
                    probs["transit"] = 0.3
                    probs["unknown"] = 0.2
            else:
                probs["patrol"] = 0.5
                probs["transit"] = 0.3
                probs["unknown"] = 0.2

        # Adjust by disposition.
        if entity.disposition == Disposition.ADVERSARIAL:
            probs["approach"] = min(1.0, probs["approach"] * 1.5)
            probs["retreat"] = probs["retreat"] * 0.5
        elif entity.disposition == Disposition.COOPERATIVE:
            probs["approach"] = probs["approach"] * 0.5
            probs["retreat"] = probs["retreat"] * 0.5
            probs["transit"] = min(1.0, probs["transit"] * 1.2)

        # Normalize.
        total = sum(probs.values())
        if total > 0:
            probs = {k: v / total for k, v in probs.items()}

        best_intent = max(probs, key=probs.get)
        best_prob = probs[best_intent]

        estimate = IntentEstimate(
            entity_id=entity.entity_id,
            intent=best_intent,
            probability=best_prob,
            alternative_intents=probs,
            confidence=entity.confidence,
            estimated_at=now or utc_now(),
        )
        self._estimates.append(estimate)
        return estimate

    def estimate_batch(
        self, entities: Sequence[TrackedEntity]
    ) -> List[IntentEstimate]:
        return [self.estimate(e) for e in entities]

    def estimates(self, limit: Optional[int] = None) -> List[IntentEstimate]:
        estimates = self._estimates
        if limit is not None:
            estimates = estimates[-limit:]
        return list(estimates)

    def clear(self) -> None:
        self._estimates.clear()