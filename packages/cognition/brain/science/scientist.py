# Copyright (c) Ultrone Contributors. All rights reserved.
"""AI Scientist — orchestrates the autonomous research lifecycle.

Pipeline: Hypothesis → Novelty → Design → Experiment → Publish → Review.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from .hypothesis_generator import ScientistHypothesisGenerator, ResearchHypothesis
from .novelty_detector import NoveltyDetector
from .experiment_designer import ExperimentDesigner
from .publication_writer import PublicationWriter
from .peer_reviewer import PeerReviewer
from .citation_network import CitationNetwork

logger = logging.getLogger("Ultrone.Science.Scientist")


class Scientist:
    """End-to-end autonomous research scientist."""

    def __init__(self):
        self.hypotheses = ScientistHypothesisGenerator()
        self.novelty = NoveltyDetector()
        self.designer = ExperimentDesigner()
        self.writer = PublicationWriter()
        self.reviewer = PeerReviewer()
        self.citations = CitationNetwork()
        self._sessions: List[Dict[str, Any]] = []

    def run_research_cycle(
        self,
        topic: str,
        keywords: Optional[List[str]] = None,
        related_work: Optional[List[str]] = None,
        results: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute one full research cycle for a topic."""
        session_id = f"SC-{uuid.uuid4().hex[:10]}"
        started = time.time()

        # 1. Hypothesis
        hypothesis = self.hypotheses.generate(topic)
        # 2. Novelty
        novelty_report = self.novelty.assess(
            hypothesis.title,
            keywords=keywords or [topic],
            related_work=related_work or [],
        )
        # 3. Design
        design = self.designer.design(
            hypothesis_id=hypothesis.hypothesis_id,
            title=hypothesis.title,
            independent_variables=keywords,
        )
        # 4. Publish (draft)
        publication = self.writer.draft(
            title=hypothesis.title,
            abstract=hypothesis.claim,
            results=results or {"accuracy": 0.85},
            methods=["baseline", "adaptive"],
        )
        # 5. Review
        review = self.reviewer.review(publication)

        session = {
            "session_id": session_id,
            "topic": topic,
            "hypothesis": hypothesis.to_dict(),
            "novelty_report": novelty_report,
            "design": design.to_dict(),
            "publication": publication.to_dict(),
            "review": review,
            "elapsed_seconds": time.time() - started,
        }
        self._sessions.append(session)
        logger.info("Research cycle complete for '%s' (score=%.2f)", topic, review["overall_score"])
        return session

    def get_sessions(self) -> List[Dict[str, Any]]:
        """Return all research sessions."""
        return list(self._sessions)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "type": "Scientist",
            "research_cycles": len(self._sessions),
            "hypotheses": self.hypotheses.get_stats(),
            "novelty": self.novelty.get_stats(),
            "designer": self.designer.get_stats(),
            "writer": self.writer.get_stats(),
            "reviewer": self.reviewer.get_stats(),
        }
