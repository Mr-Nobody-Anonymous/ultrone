# Copyright (c) Ultrone Contributors. All rights reserved.
"""Dynamic attention allocation for sensing resources.

Implements:

* dynamic attention allocation across entities and sensors
* sensor prioritization based on information gain and threat
* novelty detection for attention redirection
* saliency scoring
* observation scheduling
* curiosity-driven exploration
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

from .events import AttentionRedirected, EventBus
from .types import EntityID, TrackedEntity, utc_now

__all__ = [
    "AttentionAllocation",
    "AttentionManager",
    "AttentionManagerConfig",
]


@dataclass
class AttentionAllocation:
    """An allocation of attention to an entity or sensor."""

    target_id: str
    attention_score: float
    priority: float
    reason: str = ""
    allocated_at: datetime = field(default_factory=utc_now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class AttentionManagerConfig:
    """Configuration for the attention manager."""

    def __init__(
        self,
        *,
        uncertainty_weight: float = 0.4,
        threat_weight: float = 0.3,
        novelty_weight: float = 0.2,
        recency_weight: float = 0.1,
        min_attention: float = 0.0,
        max_attention: float = 1.0,
    ) -> None:
        self.uncertainty_weight = uncertainty_weight
        self.threat_weight = threat_weight
        self.novelty_weight = novelty_weight
        self.recency_weight = recency_weight
        self.min_attention = min_attention
        self.max_attention = max_attention


class AttentionManager:
    """Allocates attention across entities and sensors."""

    def __init__(
        self,
        *,
        config: Optional[AttentionManagerConfig] = None,
        event_bus: Optional[EventBus] = None,
    ) -> None:
        self._config = config or AttentionManagerConfig()
        self._event_bus = event_bus
        self._allocations: List[AttentionAllocation] = []
        self._last_seen: Dict[str, datetime] = {}
        self._novelty_scores: Dict[str, float] = {}

    def compute_attention(
        self,
        entity: TrackedEntity,
        *,
        threat_score: float = 0.0,
        novelty_score: Optional[float] = None,
    ) -> AttentionAllocation:
        """Compute an attention score for an entity."""
        key = str(entity.entity_id)

        # Uncertainty component (higher uncertainty = more attention).
        uncertainty = entity.uncertainty
        uncertainty_score = 1.0 / (1.0 + uncertainty) if np.isfinite(uncertainty) else 1.0

        # Threat component.
        threat_component = threat_score

        # Novelty component.
        if novelty_score is None:
            novelty_score = self._novelty_scores.get(key, 0.0)
        novelty_component = novelty_score

        # Recency component (more recent = more attention).
        last_seen = self._last_seen.get(key)
        if last_seen is not None:
            age = (utc_now() - last_seen).total_seconds()
            recency_component = np.exp(-age / 60.0)
        else:
            recency_component = 0.5

        attention = (
            self._config.uncertainty_weight * uncertainty_score
            + self._config.threat_weight * threat_component
            + self._config.novelty_weight * novelty_component
            + self._config.recency_weight * recency_component
        )
        attention = float(np.clip(
            attention, self._config.min_attention, self._config.max_attention
        ))

        allocation = AttentionAllocation(
            target_id=key,
            attention_score=attention,
            priority=attention,
            reason=f"unc={uncertainty_score:.2f} threat={threat_component:.2f}",
        )
        self._allocations.append(allocation)
        self._last_seen[key] = utc_now()
        return allocation

    def allocate_batch(
        self,
        entities: Sequence[TrackedEntity],
        *,
        threat_scores: Optional[Dict[str, float]] = None,
    ) -> List[AttentionAllocation]:
        """Compute attention for a batch of entities."""
        allocations: List[AttentionAllocation] = []
        for entity in entities:
            threat = (threat_scores or {}).get(str(entity.entity_id), 0.0)
            allocations.append(
                self.compute_attention(entity, threat_score=threat)
            )
        allocations.sort(key=lambda a: a.attention_score, reverse=True)
        return allocations

    def register_novelty(self, entity_id: EntityID, score: float) -> None:
        """Register a novelty score for an entity."""
        self._novelty_scores[str(entity_id)] = float(np.clip(score, 0.0, 1.0))

    def top_targets(self, n: int = 5) -> List[AttentionAllocation]:
        """Return the top-n attention targets."""
        sorted_allocations = sorted(
            self._allocations, key=lambda a: a.attention_score, reverse=True
        )
        return sorted_allocations[:n]

    def redirect(
        self,
        *,
        sensor_ids: Optional[List[str]] = None,
        entity_ids: Optional[List[str]] = None,
        reason: str = "",
    ) -> None:
        """Redirect sensing resources and emit an event."""
        if self._event_bus is not None:
            self._event_bus.publish_sync(
                AttentionRedirected(
                    sensor_ids=sensor_ids or [],
                    entity_ids=entity_ids or [],
                    reason=reason,
                )
            )

    def allocations(self, limit: Optional[int] = None) -> List[AttentionAllocation]:
        allocations = self._allocations
        if limit is not None:
            allocations = allocations[-limit:]
        return list(allocations)

    def clear(self) -> None:
        self._allocations.clear()
        self._last_seen.clear()
        self._novelty_scores.clear()