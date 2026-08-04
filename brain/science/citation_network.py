# Copyright (c) Ultrone Contributors. All rights reserved.
"""Citation Network — builds and analyzes citation graphs between papers."""
from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Ultrone.Science.CitationNetwork")


class CitationNetwork:
    """Manages a citation graph and computes influence metrics."""

    def __init__(self):
        self._nodes: Dict[str, Dict[str, Any]] = {}
        self._edges: List[Dict[str, str]] = []

    def add_paper(self, paper_id: str, title: str, year: int = 0) -> None:
        """Add a paper to the network."""
        self._nodes[paper_id] = {
            "paper_id": paper_id,
            "title": title,
            "year": year,
            "citations": [],
            "references": [],
        }
        logger.info("Added paper %s to citation network", paper_id)

    def add_citation(self, citing: str, cited: str) -> None:
        """Add a citation edge: ``citing`` cites ``cited``."""
        if citing not in self._nodes or cited not in self._nodes:
            raise ValueError("Both papers must be added first")
        self._edges.append({"citing": citing, "cited": cited})
        self._nodes[citing]["references"].append(cited)
        self._nodes[cited]["citations"].append(citing)

    def citation_count(self, paper_id: str) -> int:
        """Number of citations a paper received."""
        return len(self._nodes.get(paper_id, {}).get("citations", []))

    def h_index(self, paper_id: str) -> int:
        """Approximate influential research count (max h where h papers have h+ citations)."""
        counts = sorted(
            (self.citation_count(n) for n in self._nodes),
            reverse=True,
        )
        h = 0
        for i, c in enumerate(counts, start=1):
            if c >= i:
                h = i
            else:
                break
        return h

    def get_cited_by(self, paper_id: str) -> List[str]:
        """Papers citing a paper."""
        return list(self._nodes.get(paper_id, {}).get("citations", []))

    def get_references(self, paper_id: str) -> List[str]:
        """Papers a paper cites."""
        return list(self._nodes.get(paper_id, {}).get("references", []))

    def get_stats(self) -> Dict[str, Any]:
        return {
            "type": "CitationNetwork",
            "papers": len(self._nodes),
            "citation_edges": len(self._edges),
            "total_citations": sum(self.citation_count(n) for n in self._nodes),
        }
