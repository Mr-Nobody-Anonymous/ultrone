# Copyright (c) Ultrone Contributors. All rights reserved.
"""Peer Reviewer — critiques publications for quality and rigor."""
from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Ultrone.Science.PeerReviewer")


class PeerReviewer:
    """Reviews publications and returns scorecards."""

    def __init__(self):
        self._reviews: List[Dict[str, Any]] = []

    def review(self, publication: Any) -> Dict[str, Any]:
        """Review a publication (object with ``title`` and ``sections``).

        Returns:
            Dict with overall score, per-aspect scores, and comments.
        """
        title = getattr(publication, "title", "Untitled")
        sections = getattr(publication, "sections", {})

        # Evaluate each aspect with a simple heuristic
        soundness = self._score_soundness(sections)
        significance = self._score_significance(sections)
        novelty = self._score_novelty(sections)
        clarity = self._score_clarity(sections)

        overall = (soundness * 0.3 + significance * 0.3 + novelty * 0.2 + clarity * 0.2)

        review = {
            "review_id": f"RV-{uuid.uuid4().hex[:10]}",
            "title": title,
            "scores": {
                "soundness": soundness,
                "significance": significance,
                "novelty": novelty,
                "clarity": clarity,
            },
            "overall_score": overall,
            "recommendation": self._recommendation(overall),
            "comments": [
                "Clarity could be improved with more concrete comparisons.",
                "Consider adding ablations to strengthen the evidence.",
            ],
            "timestamp": time.time(),
        }
        self._reviews.append(review)
        logger.info("Reviewed publication '%s': %.2f", title, overall)
        return review

    def _score_soundness(self, sections: Dict[str, str]) -> float:
        """Score based on presence of methods/results sections."""
        score = 0.3
        if "methods" in sections and sections.get("methods"):
            score += 0.3
        if "results" in sections and sections.get("results"):
            score += 0.4
        return min(score, 1.0)

    def _score_significance(self, sections: Dict[str, str]) -> float:
        """Score based on having discussion/conclusion."""
        score = 0.3
        if "discussion" in sections and sections.get("discussion"):
            score += 0.4
        if "conclusion" in sections and sections.get("conclusion"):
            score += 0.3
        return min(score, 1.0)

    def _score_novelty(self, sections: Dict[str, str]) -> float:
        """Score based on abstract/introduction mentions of novelty."""
        intro = sections.get("introduction", "").lower()
        abstract = sections.get("abstract", "").lower()
        combined = intro + abstract
        novelty_hints = ["novel", "new", "approach", "method", "improve"]
        score = 0.2 + sum(0.1 for hint in novelty_hints if hint in combined)
        return min(score, 1.0)

    def _score_clarity(self, sections: Dict[str, str]) -> float:
        """Score based on average section length as a clarity proxy."""
        if not sections:
            return 0.2
        avg_len = sum(len(v) for v in sections.values()) / len(sections)
        if avg_len > 200:
            return 0.9
        if avg_len > 100:
            return 0.6
        return 0.3

    def _recommendation(self, score: float) -> str:
        """Map a score to an editorial recommendation."""
        if score >= 0.7:
            return "accept"
        if score >= 0.4:
            return "minor_revision"
        if score >= 0.2:
            return "major_revision"
        return "reject"

    def get_reviews(self) -> List[Dict[str, Any]]:
        """Return all reviews."""
        return list(self._reviews)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "type": "PeerReviewer",
            "reviews_completed": len(self._reviews),
        }
