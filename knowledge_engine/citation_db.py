# Copyright (c) Ultrone Contributors. All rights reserved.
"""Citation database for the ULTRONE autonomous research platform.

Stores structured citations with metadata, reciprocal references,
and lookup by paper ID, author, venue, and year.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("Ultrone.KnowledgeEngine.CitationDB")


@dataclass
class Citation:
    """A single structured citation record."""
    citation_id: str = field(default_factory=lambda: f"CT-{uuid.uuid4().hex[:12]}")
    title: str = ""
    authors: List[str] = field(default_factory=list)
    venue: str = ""
    year: Optional[int] = None
    doi: str = ""
    arxiv_id: str = ""
    url: str = ""
    references: List[str] = field(default_factory=list)  # citation_ids
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "citation_id": self.citation_id,
            "title": self.title,
            "authors": self.authors,
            "venue": self.venue,
            "year": self.year,
            "doi": self.doi,
            "arxiv_id": self.arxiv_id,
            "url": self.url,
            "references": self.references,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Citation":
        return cls(
            citation_id=data.get("citation_id", f"CT-{uuid.uuid4().hex[:12]}"),
            title=data.get("title", ""),
            authors=data.get("authors", []),
            venue=data.get("venue", ""),
            year=data.get("year"),
            doi=data.get("doi", ""),
            arxiv_id=data.get("arxiv_id", ""),
            url=data.get("url", ""),
            references=data.get("references", []),
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at", time.time()),
        )


class CitationDatabase:
    """Versioned citation store with reciprocal reference tracking."""

    def __init__(self, name: str = "ultrone_citations"):
        self.name = name
        self._citations: Dict[str, Citation] = {}
        self._by_title: Dict[str, str] = {}  # normalized title -> citation_id
        self._by_arxiv: Dict[str, str] = {}
        self._by_doi: Dict[str, str] = {}

    def add_citation(self, citation: Citation) -> Citation:
        """Add or update a citation."""
        existing = self._by_title.get(self._normalize(citation.title))
        if existing:
            old = self._citations[existing]
            citation.citation_id = old.citation_id
        self._citations[citation.citation_id] = citation
        self._by_title[self._normalize(citation.title)] = citation.citation_id
        if citation.arxiv_id:
            self._by_arxiv[citation.arxiv_id] = citation.citation_id
        if citation.doi:
            self._by_doi[citation.doi.lower()] = citation.citation_id
        return citation

    @staticmethod
    def _normalize(title: str) -> str:
        return title.strip().lower()

    def get(self, citation_id: str) -> Optional[Citation]:
        return self._citations.get(citation_id)

    def lookup_by_title(self, title: str) -> Optional[Citation]:
        cid = self._by_title.get(self._normalize(title))
        return self._citations.get(cid) if cid else None

    def lookup_by_arxiv(self, arxiv_id: str) -> Optional[Citation]:
        cid = self._by_arxiv.get(arxiv_id)
        return self._citations.get(cid) if cid else None

    def lookup_by_doi(self, doi: str) -> Optional[Citation]:
        cid = self._by_doi.get(doi.lower())
        return self._citations.get(cid) if cid else None

    def find_by_author(self, author: str) -> List[Citation]:
        return [
            c for c in self._citations.values()
            if any(a.lower() == author.lower() for a in c.authors)
        ]

    def find_by_venue(self, venue: str) -> List[Citation]:
        v = venue.lower()
        return [c for c in self._citations.values() if c.venue.lower() == v]

    def find_by_year(self, year: int) -> List[Citation]:
        return [c for c in self._citations.values() if c.year == year]

    def references_of(self, citation_id: str) -> List[Citation]:
        """Return citations referenced by the given citation."""
        cit = self._citations.get(citation_id)
        if not cit:
            return []
        return [self._citations.get(r) for r in cit.references if r in self._citations]

    def cited_by(self, citation_id: str) -> List[Citation]:
        """Return citations that reference the given citation (reverse lookup)."""
        return [
            c for c in self._citations.values()
            if citation_id in c.references
        ]

    def citation_count(self, citation_id: str) -> int:
        return len(self.cited_by(citation_id))

    def count(self) -> int:
        return len(self._citations)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "type": "CitationDatabase",
            "name": self.name,
            "citations": len(self._citations),
            "total_references": sum(len(c.references) for c in self._citations.values()),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "citations": [c.to_dict() for c in self._citations.values()],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CitationDatabase":
        db = cls(name=data.get("name", "ultrone_citations"))
        for cd in data.get("citations", []):
            db.add_citation(Citation.from_dict(cd))
        return db