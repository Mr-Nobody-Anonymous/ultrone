# Copyright (c) Ultrone Contributors. All rights reserved.
"""Research Scout — continuously discovers new research from multiple sources.

Monitors arXiv, Semantic Scholar, Hugging Face, Papers With Code, OpenReview,
GitHub repositories, AI conferences, and benchmark leaderboards. Publishes
discovery events and stores paper records.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from comms.protocol import MessageType, Priority
from knowledge_engine.base import KnowledgeSource, KnowledgeCategory, ConfidenceLevel
from research_db.schema import PaperRecord
from .base_agent import ResearchAgent, ResearchAgentRole

logger = logging.getLogger("Ultrone.ResearchDivision.Scout")


class ResearchScout(ResearchAgent):
    """Discovers new research papers across multiple monitoring sources."""

    SOURCES = [
        "arxiv",
        "semantic_scholar",
        "huggingface",
        "papers_with_code",
        "openreview",
        "github",
        "conferences",
        "leaderboards",
    ]

    def __init__(self, **kwargs):
        super().__init__(
            agent_id=kwargs.pop("agent_id", "research-scout-001"),
            role=ResearchAgentRole.SCOUT,
            **kwargs,
        )
        self._discovered_count = 0

    async def run(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Execute one research discovery cycle.

        Scans configured sources for new papers and publishes discovery events.
        """
        sources = kwargs.get("sources") or self.SOURCES
        max_papers = kwargs.get("max_papers", 20)

        discovered: List[PaperRecord] = []
        for source in sources:
            if source not in self.SOURCES:
                logger.warning("Unknown research source: %s", source)
                continue
            try:
                papers = self._scan_source(source, max_papers)
                discovered.extend(papers)
            except Exception as e:
                self._log_action("scan_error", {"source": source, "error": str(e)}, None)

        # Store and publish discoveries
        stored_ids = []
        for paper in discovered[:max_papers]:
            stored = self.research_db.save_paper(paper)
            stored_ids.append(stored.paper_id)

            # Create knowledge entry
            entry = self.knowledge.store_auto_categorized(
                content=f"Paper discovered: {paper.title}",
                source=KnowledgeSource.PAPER,
                tags=["paper", paper.venue] + paper.algorithms,
                entities=paper.authors,
                confidence_score=paper.confidence_score,
                layer="research",
                metadata={
                    "paper_id": paper.paper_id,
                    "title": paper.title,
                    "source": paper.metadata.get("source", "unknown"),
                },
            )
            self._discovered_count += 1

            # Publish discovery event
            await self.publish(
                MessageType.RESEARCH_PAPER_DISCOVERED,
                {
                    "paper_id": paper.paper_id,
                    "title": paper.title,
                    "source": paper.metadata.get("source", "unknown"),
                    "paper": paper.to_dict(),
                },
                priority=Priority.PRIORITY,
            )

        self._log_action("discovery_cycle", {
            "sources_scanned": sources,
            "papers_discovered": len(discovered),
            "papers_stored": len(stored_ids),
        }, {"paper_ids": stored_ids})

        return {
            "discovered": len(discovered),
            "stored": len(stored_ids),
            "paper_ids": stored_ids,
        }

    def _scan_source(self, source: str, max_papers: int) -> List[PaperRecord]:
        """Scan a single source for papers.

        This is a deterministic simulation of source scanning. In production,
        this would call the actual APIs (arXiv API, Semantic Scholar API, etc.).
        """
        papers = []
        # Simulated scan - generate sample papers with metadata
        sample = {
            "arxiv": {
                "title": "Sample arxiv paper on mixture of experts",
                "venue": "arXiv",
                "arxiv_id": "2401.00001",
            },
            "semantic_scholar": {
                "title": "Sample Semantic Scholar paper on RAG",
                "venue": "Semantic Scholar",
            },
            "huggingface": {
                "title": "Sample Hugging Face model card",
                "venue": "Hugging Face",
            },
            "papers_with_code": {
                "title": "Sample Papers With Code entry",
                "venue": "Papers With Code",
            },
            "openreview": {
                "title": "Sample OpenReview submission",
                "venue": "OpenReview",
            },
            "github": {
                "title": "Sample GitHub repository",
                "venue": "GitHub",
            },
            "conferences": {
                "title": "Sample conference paper",
                "venue": "NeurIPS",
            },
            "leaderboards": {
                "title": "Sample leaderboard entry",
                "venue": "Benchmark Leaderboard",
            },
        }
        info = sample.get(source)
        if info:
            paper = PaperRecord(
                title=info["title"],
                venue=info["venue"],
                arxiv_id=info.get("arxiv_id", ""),
                metadata={"source": source},
                confidence_score=0.6,
            )
            papers.append(paper)

        # Check for user-specified sample papers via config
        for p in self.config.get("sample_papers", []):
            if p.get("source") == source:
                papers.append(PaperRecord(**{k: v for k, v in p.items() if k != "source"}))

        return papers[:max_papers]

    def get_discovered_count(self) -> int:
        return self._discovered_count