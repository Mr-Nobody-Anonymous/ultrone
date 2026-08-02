# Copyright (c) Ultrone Contributors. All rights reserved.
"""Literature Search — searches for relevant literature and implementations
to support improvement hypotheses.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from knowledge_engine.memory_manager import KnowledgeMemoryManager
from research_db.store import ResearchDatabase

logger = logging.getLogger("Ultrone.SelfImprovement.Literature")


class LiteratureSearch:
    """Searches for relevant literature and implementations."""

    def __init__(
        self,
        knowledge: Optional[KnowledgeMemoryManager] = None,
        research_db: Optional[ResearchDatabase] = None,
    ):
        self.knowledge = knowledge or KnowledgeMemoryManager()
        self.research_db = research_db or ResearchDatabase()

    def search_papers(self, query: str, limit: int = 10) -> List[Any]:
        """Search for papers matching a query."""
        papers = self.research_db.list_papers()
        q = query.lower()
        results = []
        for paper in papers:
            text = f"{paper.title} {paper.summary} {' '.join(paper.algorithms)}".lower()
            if q in text or any(term in text for term in q.split()):
                results.append(paper)
        return results[:limit]

    def search_knowledge(self, query: str, limit: int = 10) -> List[Any]:
        """Search knowledge engine for relevant entries."""
        return self.knowledge.recall(query, limit=limit)

    def search_implementations(self, query: str, limit: int = 10) -> List[Any]:
        """Search for implementation plans matching a query."""
        plans = self.research_db.list_implementation_plans()
        q = query.lower()
        results = []
        for plan in plans:
            text = f"{plan.title} {plan.description}".lower()
            if q in text or any(term in text for term in q.split()):
                results.append(plan)
        return results[:limit]

    def find_related_research(self, hypothesis: Dict[str, Any], limit: int = 5) -> Dict[str, Any]:
        """Find related research for a hypothesis."""
        title = hypothesis.get("title", "")
        description = hypothesis.get("description", "")
        query = f"{title} {description}"

        return {
            "papers": self.search_papers(query, limit=limit),
            "knowledge": self.search_knowledge(query, limit=limit),
            "implementations": self.search_implementations(query, limit=limit),
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "type": "LiteratureSearch",
            "knowledge_entries": len(self.knowledge._all_entries),
            "papers": len(self.research_db.list_papers()),
            "plans": len(self.research_db.list_implementation_plans()),
        }