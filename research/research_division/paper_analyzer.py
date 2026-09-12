# Copyright (c) Ultrone Contributors. All rights reserved.
"""Paper Analyzer — summarizes, compares, and extracts insights from papers.

Analyzes discovered papers to extract summaries, algorithms, equations,
architectures, datasets, limitations, implementation ideas, and more.
Publishes analysis events and stores structured knowledge.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List

from comms.protocol import MessageType, Priority
from knowledge_engine.base import KnowledgeSource
from research_db.schema import PaperRecord
from .base_agent import ResearchAgent, ResearchAgentRole

logger = logging.getLogger("Ultrone.ResearchDivision.Analyzer")


class PaperAnalyzer(ResearchAgent):
    """Analyzes research papers to extract structured knowledge."""

    def __init__(self, **kwargs):
        super().__init__(
            agent_id=kwargs.pop("agent_id", "paper-analyzer-001"),
            role=ResearchAgentRole.ANALYZER,
            **kwargs,
        )
        # Register message handler for discovered papers
        self.message_handlers[MessageType.RESEARCH_PAPER_DISCOVERED] = self._on_paper_discovered

    async def run(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Analyze papers from the research database.

        If paper_ids is provided, analyze those papers. Otherwise analyze
        papers with empty summary (not yet analyzed).
        """
        paper_ids = kwargs.get("paper_ids")
        if paper_ids:
            papers = [self.research_db.get_paper(pid) for pid in paper_ids]
            papers = [p for p in papers if p is not None]
        else:
            papers = self.research_db.list_papers()
            papers = [p for p in papers if not p.summary]

        analyzed = []
        for paper in papers:
            result = self._analyze_paper(paper)
            analyzed.append(result)

        self._log_action(
            "analyze_cycle",
            {
                "papers_analyzed": len(analyzed),
            },
            {"paper_ids": [p.get("paper_id") for p in analyzed]},
        )

        return {
            "analyzed": len(analyzed),
            "results": analyzed,
        }

    def _on_paper_discovered(self, message: Any) -> Any:
        """Handle a paper discovered message."""
        content = message.content
        paper_id = content.get("paper_id")
        if not paper_id:
            return None
        paper = self.research_db.get_paper(paper_id)
        if paper is None:
            return None
        analysis = self._analyze_paper(paper)
        self._log_action("paper_discovered_analysis", {"paper_id": paper_id}, analysis)
        return analysis

    def _analyze_paper(self, paper: PaperRecord) -> Dict[str, Any]:
        """Analyze a single paper and extract structured knowledge."""
        # Simulated analysis - extract structured info from paper data
        title = paper.title or "Untitled"
        abstract = paper.abstract or ""

        # Extract algorithms (simulated keyword extraction)
        algorithms = self._extract_algorithms(title, abstract)

        # Extract architectures
        architectures = self._extract_architectures(title, abstract)

        # Extract datasets
        datasets = self._extract_datasets(title, abstract)

        # Extract limitations (simulated)
        limitations = self._extract_limitations(title, abstract)

        # Generate summary
        summary = (
            f"Analysis of '{title}': explores {', '.join(algorithms) if algorithms else 'novel approaches'}. "
            f"Uses {', '.join(datasets) if datasets else 'various datasets'} for evaluation."
        )

        # Update paper record
        paper.summary = summary
        paper.algorithms = list(dict.fromkeys(paper.algorithms + algorithms))
        paper.architectures = list(dict.fromkeys(paper.architectures + architectures))
        paper.datasets = list(dict.fromkeys(paper.datasets + datasets))
        paper.limitations = list(dict.fromkeys(paper.limitations + limitations))
        paper.confidence_score = min(0.9, paper.confidence_score + 0.1)
        paper.updated_at = time.time()
        self.research_db.save_paper(paper)

        # Store knowledge entries
        for algo in algorithms:
            self.knowledge.store_auto_categorized(
                content=f"Paper '{title}' presents algorithm: {algo}",
                source=KnowledgeSource.PAPER,
                tags=["algorithm", "paper"] + paper.authors[:2],
                entities=[algo] + paper.authors[:2],
                confidence_score=paper.confidence_score,
                layer="algorithm",
                metadata={"paper_id": paper.paper_id, "title": title},
            )

        # Publish analysis event
        import asyncio

        try:
            asyncio.get_event_loop().run_until_complete(
                self.publish(
                    MessageType.RESEARCH_PAPER_ANALYZED,
                    {
                        "paper_id": paper.paper_id,
                        "title": paper.title,
                        "summary": summary,
                        "algorithms": algorithms,
                        "architectures": architectures,
                    },
                    priority=Priority.ROUTINE,
                )
            )
        except RuntimeError:
            # Event loop already running - schedule
            try:
                loop = asyncio.get_running_loop()

                loop.create_task(self._async_publish_analyzed(paper, summary, algorithms, architectures))
            except RuntimeError:
                pass

        result = {
            "paper_id": paper.paper_id,
            "title": paper.title,
            "summary": summary,
            "algorithms": algorithms,
            "architectures": architectures,
        }
        self._log_action("paper_analyzed", {"paper_id": paper.paper_id}, result)
        return result

    async def _async_publish_analyzed(
        self, paper: PaperRecord, summary: str, algorithms: List[str], architectures: List[str]
    ) -> None:
        """Async helper for publishing analysis event."""
        await self.publish(
            MessageType.RESEARCH_PAPER_ANALYZED,
            {
                "paper_id": paper.paper_id,
                "title": paper.title,
                "summary": summary,
                "algorithms": algorithms,
                "architectures": architectures,
            },
        )

    @staticmethod
    def _extract_algorithms(title: str, abstract: str) -> List[str]:
        """Extract algorithm names from text (keyword-based)."""
        text = f"{title} {abstract}".lower()
        known = [
            "transformer",
            "diffusion",
            "reinforcement learning",
            "attention",
            "mixture of experts",
            "rag",
            "graph neural network",
            "gan",
            "vae",
            "normalizing flow",
            "kalman filter",
            "particle filter",
            "monte carlo tree search",
            "evolutionary",
            "bayesian",
        ]
        found = []
        for algo in known:
            if algo in text:
                found.append(algo.title())
        return found

    @staticmethod
    def _extract_architectures(title: str, abstract: str) -> List[str]:
        """Extract architecture names from text."""
        text = f"{title} {abstract}".lower()
        known = ["encoder-decoder", "transformer", "cnn", "rnn", "lstm", "graph attention", "resnet", "u-net"]
        return [a.upper() for a in known if a in text]

    @staticmethod
    def _extract_datasets(title: str, abstract: str) -> List[str]:
        """Extract dataset names from text."""
        text = f"{title} {abstract}".lower()
        known = ["imagenet", "cifar", "mnist", "glue", "squad", "commoncrawl", "wikipedia", "atari"]
        return [d for d in known if d in text]

    @staticmethod
    def _extract_limitations(title: str, abstract: str) -> List[str]:
        """Extract limitations from text."""
        text = f"{title} {abstract}".lower()
        limitations = []
        if "limited" in text or "limitation" in text:
            limitations.append("Limited generalization to other domains")
        if "computational" in text or "expensive" in text:
            limitations.append("High computational cost")
        if "small" in text or "small-scale" in text:
            limitations.append("Evaluated on small-scale benchmarks only")
        return limitations
