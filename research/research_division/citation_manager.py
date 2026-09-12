# Copyright (c) Ultrone Contributors. All rights reserved.
"""Citation Manager — manages citations, tracks references, and maintains
the citation database for all research records.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from comms.protocol import MessageType
from knowledge_engine.citation_db import Citation
from .base_agent import ResearchAgent, ResearchAgentRole

logger = logging.getLogger("Ultrone.ResearchDivision.CitationManager")


class CitationManager(ResearchAgent):
    """Manages citations and reference tracking."""

    def __init__(self, **kwargs):
        super().__init__(
            agent_id=kwargs.pop("agent_id", "citation-manager-001"),
            role=ResearchAgentRole.CITATION_MANAGER,
            **kwargs,
        )
        self.message_handlers[MessageType.RESEARCH_CITATION_ADDED] = self._on_citation_added

    async def run(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Index citations from all papers in the research database."""
        papers = self.research_db.list_papers()
        citations_added = 0
        for paper in papers:
            citation = self._create_citation_from_paper(paper)
            if citation:
                self.knowledge.register_citation(citation)
                citations_added += 1

        self._log_action("citation_index", {"citations_added": citations_added}, None)
        return {"citations_added": citations_added}

    def _on_citation_added(self, message: Any) -> Any:
        """Handle citation added events."""
        citation_data = message.content.get("citation")
        if citation_data:
            citation = Citation.from_dict(citation_data)
            self.knowledge.register_citation(citation)
            return {"citation_id": citation.citation_id}
        return None

    def _create_citation_from_paper(self, paper: Any) -> Optional[Citation]:
        """Create a citation record from a paper."""
        if not paper.title:
            return None
        citation = Citation(
            title=paper.title,
            authors=paper.authors,
            venue=paper.venue,
            year=(
                int(paper.publication_date[:4]) if paper.publication_date and len(paper.publication_date) >= 4 else None
            ),
            doi=paper.doi,
            arxiv_id=paper.arxiv_id,
            url=paper.url,
            metadata={"paper_id": paper.paper_id},
        )
        return citation

    def add_citation(
        self,
        title: str,
        authors: List[str],
        venue: str = "",
        year: Optional[int] = None,
        doi: str = "",
        arxiv_id: str = "",
    ) -> str:
        """Add a citation manually. Returns citation_id."""
        citation = Citation(
            title=title,
            authors=authors,
            venue=venue,
            year=year,
            doi=doi,
            arxiv_id=arxiv_id,
        )
        stored = self.knowledge.register_citation(citation)
        self._log_action("citation_added", {"citation_id": stored}, None)
        return stored
