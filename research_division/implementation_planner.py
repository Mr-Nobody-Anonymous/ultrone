# Copyright (c) Ultrone Contributors. All rights reserved.
"""Implementation Planner — generates detailed implementation plans for
research findings, experiment proposals, and integration roadmaps.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from comms.protocol import MessageType
from knowledge_engine.base import KnowledgeSource
from research_db.schema import ImplementationPlan, PaperRecord
from .base_agent import ResearchAgent, ResearchAgentRole

logger = logging.getLogger("Ultrone.ResearchDivision.Planner")


class ImplementationPlanner(ResearchAgent):
    """Creates implementation plans and experiment proposals."""

    def __init__(self, **kwargs):
        super().__init__(
            agent_id=kwargs.pop("agent_id", "implementation-planner-001"),
            role=ResearchAgentRole.PLANNER,
            **kwargs,
        )
        self.message_handlers[MessageType.RESEARCH_ALGORITHM_EXTRACTED] = self._on_algorithm_extracted

    async def run(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Generate implementation plans for papers."""
        paper_ids = kwargs.get("paper_ids")
        if paper_ids:
            papers = [self.research_db.get_paper(pid) for pid in paper_ids]
            papers = [p for p in papers if p is not None]
        else:
            papers = self.research_db.list_papers()

        plans = []
        for paper in papers:
            if not paper.algorithms:
                continue
            plan = self._create_plan(paper)
            plans.append(plan)

        self._log_action("plan_cycle", {"plans_created": len(plans)}, None)
        return {"plans_created": len(plans), "plan_ids": [p.plan_id for p in plans]}

    def _on_algorithm_extracted(self, message: Any) -> Any:
        paper_id = message.content.get("paper_id")
        paper = self.research_db.get_paper(paper_id) if paper_id else None
        if paper and paper.algorithms:
            return self._create_plan(paper)
        return None

    def _create_plan(self, paper: PaperRecord) -> ImplementationPlan:
        """Create an implementation plan from a paper's algorithms."""
        algorithms = ", ".join(paper.algorithms) if paper.algorithms else "novel approach"
        steps = []

        for i, algo in enumerate(paper.algorithms or ["Core approach"]):
            steps.append(
                {
                    "step": i + 1,
                    "action": f"Implement {algo}",
                    "description": f"Create module implementing {algo} from paper '{paper.title}'",
                    "estimated_hours": 8,
                    "dependencies": paper.algorithms[:i] if i > 0 else [],
                }
            )

        steps.append(
            {
                "step": len(steps) + 1,
                "action": "Integrate and test",
                "description": "Integrate modules, write unit tests, run benchmark suite",
                "estimated_hours": 4,
                "dependencies": [],
            }
        )

        plan = ImplementationPlan(
            title=f"Implement {algorithms} from '{paper.title}'",
            description=f"Implementation plan for algorithms extracted from paper: {paper.title}. "
            f"Includes {len(paper.algorithms)} algorithm implementations.",
            source_paper_ids=[paper.paper_id],
            steps=steps,
            estimated_effort=f"{sum(s.get('estimated_hours', 4) for s in steps)} hours",
            dependencies=[],
            risks=["Performance regression risk", "Integration complexity", "Numerical instability"],
            expected_improvements=[f"Incorporate {algo}" for algo in paper.algorithms],
        )
        self.research_db.save_implementation_plan(plan)

        # Store in knowledge
        self.knowledge.store_auto_categorized(
            content=f"Implementation plan '{plan.title}' created from paper '{paper.title}'",
            source=KnowledgeSource.ANALYSIS,
            tags=["implementation_plan", "plan"],
            entities=[a for a in paper.algorithms],
            confidence_score=paper.confidence_score,
            layer="project",
            metadata={"plan_id": plan.plan_id, "paper_id": paper.paper_id},
        )

        self._log_action("plan_created", {"plan_id": plan.plan_id, "paper_id": paper.paper_id}, None)
        return plan

    def create_experiment_proposal(
        self,
        hypothesis: str,
        motivation: str,
        implementation: str,
        dataset: str,
        success_criteria: str,
    ) -> Any:
        """Create an experiment proposal record."""
        from research_db.schema import ExperimentRecord

        experiment = ExperimentRecord(
            hypothesis=hypothesis,
            research_motivation=motivation,
            implementation=implementation,
            dataset=dataset,
            success_criteria=success_criteria,
            status="proposed",
        )
        stored = self.research_db.save_experiment(experiment)
        self._log_action("experiment_proposal", {"experiment_id": stored.experiment_id}, None)
        return stored
