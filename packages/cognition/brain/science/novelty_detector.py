# Copyright (c) Ultrone Contributors. All rights reserved.
"""Novelty Detector — assesses the novelty of research ideas against
existing literature and knowledge graphs."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Ultrone.Science.Novelty")


class NoveltyDetector:
    """Estimates how novel a research idea is relative to prior work."""

    def __init__(self):
        self._assessments: List[Dict[str, Any]] = []

    def assess(
        self,
        idea: str,
        keywords: Optional[List[str]] = None,
        related_work: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Assess the novelty of an idea.

        Args:
            idea: Description of the research idea.
            keywords: Key terms describing the idea.
            related_work: Existing works that overlap with the idea.

        Returns:
            Dict with a novelty score (0-1) and an assessment breakdown.
        """
        keywords = keywords or []
        related_work = related_work or []
        overlap = len(keywords) if keywords else 0

        # Novelty proxy: how little overlap exists between the idea's keywords
        # and known related work. More overlap → lower novelty.
        known_terms = self._collect_terms(related_work)
        matches = sum(1 for kw in keywords if kw.lower() in known_terms)
        if keywords:
            overlap_ratio = matches / len(keywords)
        else:
            overlap_ratio = 0.0

        novelty = 1.0 - overlap_ratio
        # Clamp to sensible range
        novelty = max(0.0, min(1.0, novelty))

        assessment = {
            "idea": idea,
            "keywords": keywords,
            "related_work_count": len(related_work),
            "overlap_ratio": overlap_ratio,
            "novelty_score": novelty,
            "verdict": "high" if novelty > 0.7 else ("medium" if novelty > 0.4 else "low"),
        }
        self._assessments.append(assessment)
        logger.info("Assessed novelty of '%s': %.2f", idea, novelty)
        return assessment

    def _collect_terms(self, related_work: List[str]) -> set:
        """Collect known terms from related work titles/descriptions."""
        terms = set()
        for work in related_work:
            for token in work.lower().replace("_", " ").split():
                terms.add(token)
        return terms

    def compare(self, ideas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Rank multiple ideas by novelty (descending)."""
        return sorted(ideas, key=lambda i: i.get("novelty_score", 0.0), reverse=True)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "type": "NoveltyDetector",
            "assessments_performed": len(self._assessments),
        }
