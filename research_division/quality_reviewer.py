# Copyright (c) Ultrone Contributors. All rights reserved.
"""Quality Reviewer — reviews research findings, code, and experiments for
quality, correctness, and reproducibility.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from comms.protocol import MessageType, Priority
from knowledge_engine.base import KnowledgeSource, KnowledgeCategory, ConfidenceLevel
from .base_agent import ResearchAgent, ResearchAgentRole

logger = logging.getLogger("Ultrone.ResearchDivision.Reviewer")


class QualityReviewer(ResearchAgent):
    """Reviews research outputs for quality and correctness."""

    def __init__(self, **kwargs):
        super().__init__(
            agent_id=kwargs.pop("agent_id", "quality-reviewer-001"),
            role=ResearchAgentRole.REVIEWER,
            **kwargs,
        )
        self.message_handlers[MessageType.RESEARCH_QUALITY_REVIEW] = self._on_review_request

    async def run(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Review all completed experiments and generated code."""
        experiments = self.research_db.list_experiments()
        reviews = []
        for experiment in experiments:
            if experiment.status == "completed":
                review = self._review_experiment(experiment)
                reviews.append(review)

        self._log_action("review_cycle", {"reviews": len(reviews)}, None)
        return {"reviews": len(reviews), "results": reviews}

    def _on_review_request(self, message: Any) -> Any:
        """Handle review request events."""
        experiment_id = message.content.get("experiment_id")
        experiment = self.research_db.get_experiment(experiment_id) if experiment_id else None
        if experiment:
            return self._review_experiment(experiment)
        return None

    def _review_experiment(self, experiment: Any) -> Dict[str, Any]:
        """Review a completed experiment for quality."""
        issues = []
        score = 0.8

        # Check for required fields
        if not experiment.hypothesis:
            issues.append("Missing hypothesis")
            score -= 0.1
        if not experiment.dataset:
            issues.append("Missing dataset specification")
            score -= 0.1
        if not experiment.evaluation_metrics:
            issues.append("Missing evaluation metrics")
            score -= 0.1
        if not experiment.conclusion:
            issues.append("Missing conclusion")
            score -= 0.1
        if not experiment.recommendation:
            issues.append("Missing recommendation")
            score -= 0.05

        # Check reproducibility
        if not experiment.training_config:
            issues.append("Missing training configuration (reproducibility risk)")
            score -= 0.1

        review = {
            "experiment_id": experiment.experiment_id,
            "quality_score": max(0.0, score),
            "issues": issues,
            "passed": score >= 0.6,
        }

        # Store review in knowledge
        self.knowledge.store_auto_categorized(
            content=f"Quality review for experiment '{experiment.experiment_id}': score={score:.2f}, "
                    f"issues={issues}",
            source=KnowledgeSource.ANALYSIS,
            tags=["quality_review", "review"],
            entities=[experiment.experiment_id],
            confidence_score=score,
            layer="experiment",
            metadata={"experiment_id": experiment.experiment_id, "review": review},
        )

        self._log_action("experiment_reviewed", {"experiment_id": experiment.experiment_id}, review)
        return review