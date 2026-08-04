# Copyright (c) Ultrone Contributors. All rights reserved.
"""Explainability for situational awareness.

Generates human-readable explanations for belief updates, predictions, and
assessments. Every explanation includes:

* evidence chain
* contributing observations
* confidence and uncertainty
* information gain
* reasoning graph
* probability explanation
* alternative hypotheses
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .types import (
    BeliefUpdate,
    EvidenceChain,
    EvidenceLink,
    TrackedEntity,
    utc_now,
)

__all__ = [
    "Explanation",
    "ExplainabilityEngine",
    "ExplainabilityConfig",
]


@dataclass
class Explanation:
    """A complete explanation for a belief update or assessment."""

    target_id: str
    summary: str
    evidence_chain: EvidenceChain
    confidence: float = 0.0
    uncertainty: float = 0.0
    information_gain: float = 0.0
    probability_explanation: str = ""
    alternative_hypotheses: List[str] = field(default_factory=list)
    generated_at: datetime = field(default_factory=utc_now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ExplainabilityConfig:
    """Configuration for the explainability engine."""

    def __init__(
        self,
        *,
        max_evidence_links: int = 20,
        include_probability_math: bool = True,
        include_alternative_hypotheses: bool = True,
    ) -> None:
        self.max_evidence_links = max_evidence_links
        self.include_probability_math = include_probability_math
        self.include_alternative_hypotheses = include_alternative_hypotheses


class ExplainabilityEngine:
    """Generates explanations for belief updates and assessments."""

    def __init__(self, *, config: Optional[ExplainabilityConfig] = None) -> None:
        self._config = config or ExplainabilityConfig()
        self._explanations: List[Explanation] = []

    def explain_belief_update(
        self,
        update: BeliefUpdate,
        *,
        entity: Optional[TrackedEntity] = None,
    ) -> Explanation:
        """Generate an explanation for a belief update."""
        links: List[EvidenceLink] = []
        for obs_id in update.contributing_observation_ids:
            links.append(
                EvidenceLink(
                    source="observation",
                    description=f"Observation {obs_id} contributed to the update",
                    confidence=0.8,
                    observation_id=obs_id,
                )
            )

        if update.previous_belief is not None and update.updated_belief is not None:
            links.append(
                EvidenceLink(
                    source="bayesian_update",
                    description=f"Belief updated via {update.method}",
                    confidence=0.9,
                )
            )

        # Probability explanation.
        probability_explanation = ""
        if self._config.include_probability_math and update.updated_belief is not None:
            probability_explanation = (
                f"Posterior belief has entropy {update.updated_belief.entropy():.3f} "
                f"and uncertainty {update.updated_belief.uncertainty():.3f}"
            )

        # Alternative hypotheses.
        alternatives: List[str] = []
        if self._config.include_alternative_hypotheses and update.updated_belief is not None:
            if update.updated_belief.categorical_probs:
                sorted_probs = sorted(
                    update.updated_belief.categorical_probs.items(),
                    key=lambda kv: kv[1],
                    reverse=True,
                )
                alternatives = [
                    f"{label} ({prob:.2f})"
                    for label, prob in sorted_probs[1:4]
                ]

        chain = EvidenceChain(
            conclusion=f"Belief updated for entity {update.entity_id}",
            links=links[: self._config.max_evidence_links],
            overall_confidence=0.8,
            alternative_hypotheses=alternatives,
        )

        explanation = Explanation(
            target_id=str(update.entity_id),
            summary=f"Belief updated via {update.method} with information gain {update.information_gain:.3f}",
            evidence_chain=chain,
            confidence=0.8,
            uncertainty=update.updated_belief.uncertainty() if update.updated_belief else 0.0,
            information_gain=update.information_gain,
            probability_explanation=probability_explanation,
            alternative_hypotheses=alternatives,
        )
        self._explanations.append(explanation)
        return explanation

    def explain_entity(
        self,
        entity: TrackedEntity,
        *,
        conclusion: str = "Entity state assessment",
    ) -> Explanation:
        """Generate an explanation for an entity's current state."""
        links: List[EvidenceLink] = [
            EvidenceLink(
                source="entity_state",
                description=f"Entity type: {entity.entity_type.value}, category: {entity.category.value}",
                confidence=entity.confidence,
            ),
            EvidenceLink(
                source="belief",
                description=f"Belief uncertainty: {entity.uncertainty:.3f}",
                confidence=0.7,
            ),
        ]

        for obs_id in entity.observation_ids[-5:]:
            links.append(
                EvidenceLink(
                    source="observation",
                    description=f"Observation {obs_id}",
                    confidence=0.6,
                    observation_id=obs_id,
                )
            )

        chain = EvidenceChain(
            conclusion=conclusion,
            links=links[: self._config.max_evidence_links],
            overall_confidence=entity.confidence,
        )

        explanation = Explanation(
            target_id=str(entity.entity_id),
            summary=f"Entity {entity.entity_id} assessed with confidence {entity.confidence:.2f}",
            evidence_chain=chain,
            confidence=entity.confidence,
            uncertainty=entity.uncertainty,
            information_gain=0.0,
        )
        self._explanations.append(explanation)
        return explanation

    def explanations(self, limit: Optional[int] = None) -> List[Explanation]:
        explanations = self._explanations
        if limit is not None:
            explanations = explanations[-limit:]
        return list(explanations)

    def clear(self) -> None:
        self._explanations.clear()