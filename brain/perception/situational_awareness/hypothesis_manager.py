# Copyright (c) Ultrone Contributors. All rights reserved.
"""Hypothesis management for reasoning and explainability.

Maintains competing hypotheses about entity identity, intent, and world
state. Supports:

* hypothesis proposal and lifecycle
* evidence accumulation
* probability updates
* hypothesis ranking and elimination
* alternative hypothesis tracking
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np

from .events import EventBus, HypothesisUpdated
from .types import EntityID, HypothesisStatus, utc_now

__all__ = [
    "Hypothesis",
    "HypothesisManager",
    "HypothesisManagerConfig",
]


@dataclass
class Hypothesis:
    """A competing hypothesis about the world."""

    hypothesis_id: str
    description: str
    probability: float = 0.0
    status: HypothesisStatus = HypothesisStatus.PROPOSED
    entity_id: Optional[EntityID] = None
    evidence: List[str] = field(default_factory=list)
    supporting_observations: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_evidence(self, evidence: str, observation_id: Optional[str] = None) -> None:
        self.evidence.append(evidence)
        if observation_id is not None:
            self.supporting_observations.append(observation_id)
        self.updated_at = utc_now()


class HypothesisManagerConfig:
    """Configuration for the hypothesis manager."""

    def __init__(
        self,
        *,
        max_hypotheses: int = 1000,
        elimination_threshold: float = 0.01,
        acceptance_threshold: float = 0.8,
    ) -> None:
        self.max_hypotheses = max_hypotheses
        self.elimination_threshold = elimination_threshold
        self.acceptance_threshold = acceptance_threshold


class HypothesisManager:
    """Manages competing hypotheses with evidence accumulation."""

    def __init__(
        self,
        *,
        config: Optional[HypothesisManagerConfig] = None,
        event_bus: Optional[EventBus] = None,
    ) -> None:
        self._config = config or HypothesisManagerConfig()
        self._event_bus = event_bus
        self._hypotheses: Dict[str, Hypothesis] = {}

    def propose(
        self,
        description: str,
        *,
        entity_id: Optional[EntityID] = None,
        initial_probability: float = 0.0,
        hypothesis_id: Optional[str] = None,
    ) -> Hypothesis:
        """Propose a new hypothesis."""
        hypothesis_id = hypothesis_id or f"hyp_{len(self._hypotheses)}"
        hypothesis = Hypothesis(
            hypothesis_id=hypothesis_id,
            description=description,
            probability=initial_probability,
            status=HypothesisStatus.PROPOSED,
            entity_id=entity_id,
        )
        self._hypotheses[hypothesis_id] = hypothesis
        return hypothesis

    def add_evidence(
        self,
        hypothesis_id: str,
        evidence: str,
        *,
        observation_id: Optional[str] = None,
        likelihood: Optional[float] = None,
    ) -> Optional[Hypothesis]:
        """Add evidence to a hypothesis and update its probability."""
        hypothesis = self._hypotheses.get(hypothesis_id)
        if hypothesis is None:
            return None

        hypothesis.add_evidence(evidence, observation_id)
        hypothesis.status = HypothesisStatus.ACTIVE

        if likelihood is not None:
            # Bayesian update: P(H|E) ∝ P(E|H) * P(H)
            hypothesis.probability = hypothesis.probability * likelihood
            self._normalize_entity_hypotheses(hypothesis.entity_id)

        self._update_status(hypothesis)
        self._emit_update(hypothesis)
        return hypothesis

    def set_probability(self, hypothesis_id: str, probability: float) -> Optional[Hypothesis]:
        """Directly set a hypothesis probability."""
        hypothesis = self._hypotheses.get(hypothesis_id)
        if hypothesis is None:
            return None
        hypothesis.probability = float(np.clip(probability, 0.0, 1.0))
        self._update_status(hypothesis)
        self._emit_update(hypothesis)
        return hypothesis

    def _normalize_entity_hypotheses(self, entity_id: Optional[EntityID]) -> None:
        """Normalize probabilities across hypotheses for the same entity."""
        if entity_id is None:
            return
        related = [
            h for h in self._hypotheses.values()
            if h.entity_id == entity_id and h.status != HypothesisStatus.ELIMINATED
        ]
        total = sum(h.probability for h in related)
        if total > 0:
            for h in related:
                h.probability = h.probability / total

    def _update_status(self, hypothesis: Hypothesis) -> None:
        if hypothesis.probability >= self._config.acceptance_threshold:
            hypothesis.status = HypothesisStatus.ACCEPTED
        elif hypothesis.probability <= self._config.elimination_threshold:
            hypothesis.status = HypothesisStatus.ELIMINATED
        elif hypothesis.probability > self._config.elimination_threshold:
            hypothesis.status = HypothesisStatus.SUPPORTED

    def _emit_update(self, hypothesis: Hypothesis) -> None:
        if self._event_bus is not None:
            self._event_bus.publish_sync(
                HypothesisUpdated(
                    hypothesis_id=hypothesis.hypothesis_id,
                    status=hypothesis.status.value,
                    probability=hypothesis.probability,
                )
            )

    def get(self, hypothesis_id: str) -> Optional[Hypothesis]:
        return self._hypotheses.get(hypothesis_id)

    def for_entity(self, entity_id: EntityID) -> List[Hypothesis]:
        return [
            h for h in self._hypotheses.values()
            if h.entity_id == entity_id
        ]

    def active(self) -> List[Hypothesis]:
        return [
            h for h in self._hypotheses.values()
            if h.status in (HypothesisStatus.ACTIVE, HypothesisStatus.SUPPORTED)
        ]

    def accepted(self) -> List[Hypothesis]:
        return [
            h for h in self._hypotheses.values()
            if h.status == HypothesisStatus.ACCEPTED
        ]

    def eliminated(self) -> List[Hypothesis]:
        return [
            h for h in self._hypotheses.values()
            if h.status == HypothesisStatus.ELIMINATED
        ]

    def ranked(self) -> List[Hypothesis]:
        """Return hypotheses ranked by probability (descending)."""
        return sorted(
            self._hypotheses.values(),
            key=lambda h: h.probability,
            reverse=True,
        )

    def top(self, n: int = 3) -> List[Hypothesis]:
        return self.ranked()[:n]

    def hypothesis_count(self) -> int:
        return len(self._hypotheses)

    def clear(self) -> None:
        self._hypotheses.clear()