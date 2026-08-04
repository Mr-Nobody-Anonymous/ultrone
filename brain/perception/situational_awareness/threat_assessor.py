# Copyright (c) Ultrone Contributors. All rights reserved.
"""Threat assessment for tracked entities.

Computes threat scores based on:

* entity disposition and category
* proximity to protected assets
* velocity / approach rate
* entity type and capability
* confidence weighting
* temporal escalation
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

from .types import (
    Disposition,
    EntityCategory,
    EntityID,
    ThreatLevel,
    TrackedEntity,
    Vector3,
    utc_now,
)

__all__ = [
    "ThreatAssessment",
    "ThreatAssessor",
    "ThreatAssessorConfig",
]


@dataclass
class ThreatAssessment:
    """A threat assessment for a single entity."""

    entity_id: EntityID
    threat_score: float = 0.0
    threat_level: ThreatLevel = ThreatLevel.NONE
    contributing_factors: Dict[str, float] = field(default_factory=dict)
    confidence: float = 0.0
    assessed_at: datetime = field(default_factory=utc_now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ThreatAssessorConfig:
    """Configuration for the threat assessor."""

    def __init__(
        self,
        *,
        proximity_weight: float = 0.4,
        velocity_weight: float = 0.3,
        disposition_weight: float = 0.2,
        type_weight: float = 0.1,
        proximity_scale: float = 100.0,
        velocity_scale: float = 50.0,
    ) -> None:
        self.proximity_weight = proximity_weight
        self.velocity_weight = velocity_weight
        self.disposition_weight = disposition_weight
        self.type_weight = type_weight
        self.proximity_scale = proximity_scale
        self.velocity_scale = velocity_scale


class ThreatAssessor:
    """Assesses threat levels for tracked entities."""

    _DISPOSITION_SCORES = {
        Disposition.ADVERSARIAL: 1.0,
        Disposition.UNKNOWN: 0.5,
        Disposition.UNRESPONSIVE: 0.4,
        Disposition.NEUTRAL: 0.1,
        Disposition.COOPERATIVE: 0.0,
    }

    _CATEGORY_SCORES = {
        EntityCategory.FRIEND: 0.0,
        EntityCategory.NEUTRAL: 0.1,
        EntityCategory.UNKNOWN: 0.5,
        EntityCategory.ENVIRONMENT: 0.0,
        EntityCategory.INFRASTRUCTURE: 0.0,
        EntityCategory.WEATHER: 0.0,
        EntityCategory.TERRAIN: 0.0,
        EntityCategory.RESOURCE: 0.0,
        EntityCategory.COMMUNICATION: 0.0,
    }

    def __init__(self, *, config: Optional[ThreatAssessorConfig] = None) -> None:
        self._config = config or ThreatAssessorConfig()
        self._protected_assets: List[Vector3] = []

    def add_protected_asset(self, position: Vector3) -> None:
        """Register a protected asset position."""
        self._protected_assets.append(position)

    def set_protected_assets(self, positions: Sequence[Vector3]) -> None:
        self._protected_assets = list(positions)

    def assess(
        self, entity: TrackedEntity, *, now: Optional[datetime] = None
    ) -> ThreatAssessment:
        """Compute a threat assessment for an entity."""
        factors: Dict[str, float] = {}

        # 1. Proximity to nearest protected asset.
        if self._protected_assets:
            distances = [
                entity.state.position.distance_to(asset)
                for asset in self._protected_assets
            ]
            nearest = min(distances)
            proximity_score = np.exp(-nearest / self._config.proximity_scale)
            factors["proximity"] = float(proximity_score)
        else:
            factors["proximity"] = 0.0

        # 2. Velocity / approach rate.
        speed = float(np.linalg.norm(entity.state.velocity.as_array()))
        velocity_score = min(1.0, speed / self._config.velocity_scale)
        factors["velocity"] = velocity_score

        # 3. Disposition.
        disposition_score = self._DISPOSITION_SCORES.get(entity.disposition, 0.5)
        factors["disposition"] = disposition_score

        # 4. Entity type / category.
        category_score = self._CATEGORY_SCORES.get(entity.category, 0.5)
        factors["category"] = category_score

        # Weighted combination.
        threat_score = (
            self._config.proximity_weight * factors["proximity"]
            + self._config.velocity_weight * factors["velocity"]
            + self._config.disposition_weight * factors["disposition"]
            + self._config.type_weight * factors["category"]
        )

        # Confidence weighting.
        threat_score *= entity.confidence

        # Map to threat level.
        threat_level = self._score_to_level(threat_score)

        return ThreatAssessment(
            entity_id=entity.entity_id,
            threat_score=float(np.clip(threat_score, 0.0, 1.0)),
            threat_level=threat_level,
            contributing_factors=factors,
            confidence=entity.confidence,
            assessed_at=now or utc_now(),
        )

    def assess_batch(
        self, entities: Sequence[TrackedEntity]
    ) -> List[ThreatAssessment]:
        return [self.assess(e) for e in entities]

    def highest_threat(
        self, entities: Sequence[TrackedEntity]
    ) -> Optional[ThreatAssessment]:
        assessments = self.assess_batch(entities)
        if not assessments:
            return None
        return max(assessments, key=lambda a: a.threat_score)

    @staticmethod
    def _score_to_level(score: float) -> ThreatLevel:
        if score >= 0.8:
            return ThreatLevel.CRITICAL
        if score >= 0.6:
            return ThreatLevel.HIGH
        if score >= 0.4:
            return ThreatLevel.MEDIUM
        if score >= 0.2:
            return ThreatLevel.LOW
        return ThreatLevel.NONE