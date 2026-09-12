# Copyright (c) Ultrone Contributors. All rights reserved.
"""Research memory - knowledge from papers, literature, and research findings."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .base import (
    KnowledgeCategory,
    KnowledgeEntry,
    KnowledgeMemoryBase,
    KnowledgeSource,
)


class ResearchMemory(KnowledgeMemoryBase):
    """Stores research-oriented knowledge: papers, findings, and literature."""

    def __init__(self, capacity: int = 100000, name: str = "research_knowledge"):
        super().__init__(capacity=capacity, name=name)

    def store_paper(
        self,
        title: str,
        authors: List[str],
        abstract: str,
        venue: str = "",
        year: int = 0,
        arxiv_id: Optional[str] = None,
        doi: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> KnowledgeEntry:
        """Store a research paper."""
        entry = KnowledgeEntry(
            content=abstract,
            category=KnowledgeCategory.RESULT,
            source=KnowledgeSource.PAPER,
            confidence_score=0.7,
            tags=["paper"] + (tags or []),
            entities=[title],
            metadata={
                **(metadata or {}),
                "title": title,
                "authors": authors,
                "venue": venue,
                "year": year,
                "arxiv_id": arxiv_id,
                "doi": doi,
            },
        )
        return self.store(entry)

    def find_paper(self, title: str) -> Optional[KnowledgeEntry]:
        t = title.lower()
        for e in self._entries.values():
            meta = e.metadata or {}
            if t in (meta.get("title", "").lower() or e.content.lower()):
                return e
        return None

    def list_papers(
        self,
        venue: Optional[str] = None,
        year: Optional[int] = None,
    ) -> List[KnowledgeEntry]:
        results = []
        for e in self._entries.values():
            meta = e.metadata or {}
            if venue and meta.get("venue") != venue:
                continue
            if year and meta.get("year") != year:
                continue
            results.append(e)
        return results
