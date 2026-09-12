# Copyright (c) Ultrone Contributors. All rights reserved.
"""Documentation Writer — generates comprehensive documentation for
research findings, generated modules, experiments, and releases.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from comms.protocol import MessageType
from knowledge_engine.base import KnowledgeSource
from .base_agent import ResearchAgent, ResearchAgentRole

logger = logging.getLogger("Ultrone.ResearchDivision.Writer")


class DocumentationWriter(ResearchAgent):
    """Generates documentation for research outputs."""

    def __init__(self, **kwargs):
        super().__init__(
            agent_id=kwargs.pop("agent_id", "documentation-writer-001"),
            role=ResearchAgentRole.WRITER,
            **kwargs,
        )
        self.message_handlers[MessageType.RESEARCH_DOCUMENTATION] = self._on_documentation_request

    async def run(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Generate documentation for all research records."""
        docs = []

        # Document papers
        for paper in self.research_db.list_papers():
            doc = self._document_paper(paper)
            docs.append(doc)

        # Document experiments
        for experiment in self.research_db.list_experiments():
            doc = self._document_experiment(experiment)
            docs.append(doc)

        # Document implementation plans
        for plan in self.research_db.list_implementation_plans():
            doc = self._document_plan(plan)
            docs.append(doc)

        self._log_action("documentation_cycle", {"docs_generated": len(docs)}, None)
        return {"docs_generated": len(docs), "results": docs}

    def _on_documentation_request(self, message: Any) -> Any:
        record_type = message.content.get("record_type")
        record_id = message.content.get("record_id")
        if record_type == "paper":
            paper = self.research_db.get_paper(record_id)
            return self._document_paper(paper) if paper else None
        elif record_type == "experiment":
            experiment = self.research_db.get_experiment(record_id)
            return self._document_experiment(experiment) if experiment else None
        return None

    def _document_paper(self, paper: Any) -> Dict[str, Any]:
        """Generate documentation for a paper."""
        doc = {
            "type": "paper",
            "record_id": paper.paper_id,
            "title": paper.title,
            "authors": paper.authors,
            "venue": paper.venue,
            "summary": paper.summary,
            "algorithms": paper.algorithms,
            "datasets": paper.datasets,
            "limitations": paper.limitations,
            "future_work": paper.future_work,
            "confidence": paper.confidence_score,
        }
        self._store_doc(doc, paper.paper_id, "paper")
        return doc

    def _document_experiment(self, experiment: Any) -> Dict[str, Any]:
        """Generate documentation for an experiment."""
        doc = {
            "type": "experiment",
            "record_id": experiment.experiment_id,
            "hypothesis": experiment.hypothesis,
            "status": experiment.status,
            "metrics": experiment.evaluation_metrics,
            "conclusion": experiment.conclusion,
            "recommendation": experiment.recommendation,
        }
        self._store_doc(doc, experiment.experiment_id, "experiment")
        return doc

    def _document_plan(self, plan: Any) -> Dict[str, Any]:
        """Generate documentation for an implementation plan."""
        doc = {
            "type": "implementation_plan",
            "record_id": plan.plan_id,
            "title": plan.title,
            "description": plan.description,
            "steps": plan.steps,
            "estimated_effort": plan.estimated_effort,
            "risks": plan.risks,
        }
        self._store_doc(doc, plan.plan_id, "implementation_plan")
        return doc

    def _store_doc(self, doc: Dict[str, Any], record_id: str, doc_type: str) -> None:
        """Store documentation in knowledge."""
        self.knowledge.store_auto_categorized(
            content=f"Documentation for {doc_type} '{record_id}': {doc}",
            source=KnowledgeSource.ANALYSIS,
            tags=["documentation", doc_type],
            entities=[record_id],
            confidence_score=0.8,
            layer="project",
            metadata={"record_id": record_id, "doc_type": doc_type, "doc": doc},
        )
