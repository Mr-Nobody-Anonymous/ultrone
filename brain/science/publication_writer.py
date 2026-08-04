# Copyright (c) Ultrone Contributors. All rights reserved.
"""Publication Writer — drafts research papers from experiment results."""
from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Ultrone.Science.PublicationWriter")


@dataclass
class Publication:
    """A drafted research publication."""
    publication_id: str = field(default_factory=lambda: f"PUB-{uuid.uuid4().hex[:10]}")
    title: str = ""
    abstract: str = ""
    sections: Dict[str, str] = field(default_factory=dict)
    authors: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "publication_id": self.publication_id,
            "title": self.title,
            "abstract": self.abstract,
            "sections": self.sections,
            "authors": self.authors,
            "references": self.references,
            "created_at": self.created_at,
        }


class PublicationWriter:
    """Generates structured publication drafts."""

    def __init__(self):
        self._publications: List[Publication] = []

    def draft(
        self,
        title: str,
        abstract: str,
        results: Optional[Dict[str, Any]] = None,
        methods: Optional[List[str]] = None,
        references: Optional[List[str]] = None,
        authors: Optional[List[str]] = None,
    ) -> Publication:
        """Draft a publication from structured inputs."""
        sections = {
            "introduction": f"Introduction for: {title}",
            "methods": self._format_methods(methods),
            "results": self._format_results(results or {}),
            "discussion": f"Discussion of findings for: {title}",
            "conclusion": f"We presented {title}. Future work is discussed.",
        }
        pub = Publication(
            title=title,
            abstract=abstract,
            sections=sections,
            authors=authors or ["ULTRONE AI Scientist"],
            references=references or [],
        )
        self._publications.append(pub)
        logger.info("Drafted publication: %s", title)
        return pub

    def _format_methods(self, methods: Optional[List[str]]) -> str:
        if not methods:
            return "Standard experimental methodology was used."
        return "\n".join(f"- {m}" for m in methods)

    def _format_results(self, results: Dict[str, Any]) -> str:
        if not results:
            return "Results are summarized in the accompanying tables."
        lines = [f"- {k}: {v}" for k, v in results.items()]
        return "\n".join(lines)

    def get_publications(self) -> List[Publication]:
        """Return all drafted publications."""
        return list(self._publications)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "type": "PublicationWriter",
            "publications_drafted": len(self._publications),
        }
