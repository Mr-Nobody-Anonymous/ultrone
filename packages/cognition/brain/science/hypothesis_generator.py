# Copyright (c) Ultrone Contributors. All rights reserved.
"""Scientist Hypothesis Generator — proposes novel research hypotheses."""
from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Ultrone.Science.Hypothesis")


@dataclass
class ResearchHypothesis:
    """A proposed research hypothesis."""
    hypothesis_id: str = field(default_factory=lambda: f"RH-{uuid.uuid4().hex[:10]}")
    title: str = ""
    claim: str = ""
    rationale: str = ""
    novelty: float = 0.5
    estimated_impact: float = 0.5
    feasibility: float = 0.5
    related_work: List[str] = field(default_factory=list)
    methods: List[str] = field(default_factory=list)
    status: str = "proposed"
    created_at: float = field(default_factory=time.time)

    def score(self) -> float:
        """Overall research quality score."""
        return (self.novelty * 0.4 + self.estimated_impact * 0.3 + self.feasibility * 0.3)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hypothesis_id": self.hypothesis_id,
            "title": self.title,
            "claim": self.claim,
            "rationale": self.rationale,
            "novelty": self.novelty,
            "estimated_impact": self.estimated_impact,
            "feasibility": self.feasibility,
            "related_work": self.related_work,
            "methods": self.methods,
            "status": self.status,
            "created_at": self.created_at,
            "score": self.score(),
        }


class ScientistHypothesisGenerator:
    """Generates and ranks research hypotheses."""

    def __init__(self):
        self._hypotheses: List[ResearchHypothesis] = []

    def generate(self, topic: str, inspiration: Optional[str] = None) -> ResearchHypothesis:
        """Generate a hypothesis for a topic."""
        hypothesis = ResearchHypothesis(
            title=f"Improving {topic} efficacy through adaptive methods",
            claim=f"Adaptive {topic} methods outperform static baselines",
            rationale=f"Literature suggests {topic} benefits from dynamic adaptation. "
                      f"Related work: {inspiration or 'general ML principles'}.",
            novelty=0.7,
            estimated_impact=0.6,
            feasibility=0.8,
            related_work=[inspiration] if inspiration else [],
            methods=["baseline", "adaptive variant"],
        )
        self._hypotheses.append(hypothesis)
        logger.info("Generated hypothesis: %s", hypothesis.title)
        return hypothesis

    def generate_batch(self, topics: List[str]) -> List[ResearchHypothesis]:
        """Generate a batch of hypotheses."""
        return [self.generate(topic) for topic in topics]

    def rank(self, hypotheses: Optional[List[ResearchHypothesis]] = None) -> List[ResearchHypothesis]:
        """Rank hypotheses by research quality score (descending)."""
        pool = hypotheses or self._hypotheses
        return sorted(pool, key=lambda h: h.score(), reverse=True)

    def get_hypotheses(self) -> List[ResearchHypothesis]:
        """Return all generated hypotheses."""
        return list(self._hypotheses)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "type": "ScientistHypothesisGenerator",
            "hypotheses_generated": len(self._hypotheses),
        }

