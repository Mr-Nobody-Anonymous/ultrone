# Copyright (c) Ultrone Contributors. All rights reserved.
"""Release Manager — evaluates validated improvements and proposes releases,
managing versioning and integration recommendations.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict

from comms.protocol import MessageType
from knowledge_engine.base import KnowledgeSource
from .base_agent import ResearchAgent, ResearchAgentRole

logger = logging.getLogger("Ultrone.ResearchDivision.Release")


class ReleaseManager(ResearchAgent):
    """Manages release proposals for validated improvements."""

    def __init__(self, **kwargs):
        super().__init__(
            agent_id=kwargs.pop("agent_id", "release-manager-001"),
            role=ResearchAgentRole.RELEASER,
            **kwargs,
        )
        self.message_handlers[MessageType.RESEARCH_RELEASE_PROPOSAL] = self._on_release_request

    async def run(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Evaluate experiments and propose releases for adopted improvements."""
        experiments = self.research_db.list_experiments()
        proposals = []
        for experiment in experiments:
            if experiment.status == "completed" and experiment.recommendation == "adopt":
                proposal = self._create_release_proposal(experiment)
                proposals.append(proposal)

        self._log_action("release_cycle", {"proposals": len(proposals)}, None)
        return {"proposals": len(proposals), "results": proposals}

    def _on_release_request(self, message: Any) -> Any:
        experiment_id = message.content.get("experiment_id")
        experiment = self.research_db.get_experiment(experiment_id) if experiment_id else None
        if experiment:
            return self._create_release_proposal(experiment)
        return None

    def _create_release_proposal(self, experiment: Any) -> Dict[str, Any]:
        """Create a release proposal for an adopted experiment."""
        proposal = {
            "experiment_id": experiment.experiment_id,
            "title": f"Release: {experiment.hypothesis[:60]}...",
            "version": f"0.{int(time.time()) % 100}.0",
            "changes": [
                f"Integrate validated improvement from experiment {experiment.experiment_id}",
                f"Update documentation for {experiment.dataset}",
            ],
            "metrics": experiment.evaluation_metrics,
            "recommendation": "release",
            "rollback_strategy": "git revert to previous release tag",
        }

        self.knowledge.store_auto_categorized(
            content=f"Release proposal created for experiment '{experiment.experiment_id}': {proposal}",
            source=KnowledgeSource.ANALYSIS,
            tags=["release", "proposal"],
            entities=[experiment.experiment_id],
            confidence_score=0.85,
            layer="project",
            metadata={"experiment_id": experiment.experiment_id, "proposal": proposal},
        )

        self._log_action("release_proposed", {"experiment_id": experiment.experiment_id}, proposal)
        return proposal
