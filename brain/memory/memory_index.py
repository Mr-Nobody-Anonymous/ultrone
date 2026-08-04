# Copyright (c) Ultrone Contributors. All rights reserved.
"""Memory Index — inverted index for fast keyword-based retrieval over memory.

Maps terms to memory keys and supports relevance-ranked search.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .base import MemoryItem

logger = logging.getLogger("Ultrone.Brain.Memory.Index")


@dataclass
class IndexConfig:
    """Configuration for the memory index."""
    case_sensitive: bool = False
    min_token_length: int = 2


class MemoryIndex:
    """Inverted index over memory item contents."""

    def __init__(self, config: Optional[IndexConfig] = None):
        self.config = config or IndexConfig()
        self._index: Dict[str, set] = {}
        self._item_terms: Dict[str, Dict[str, int]] = {}

    def add(self, item: MemoryItem) -> None:
        """Index a memory item."""
        terms = self._tokenize(self._extract_text(item.content))
        counts: Dict[str, int] = {}
        for term in terms:
            counts[term] = counts.get(term, 0) + 1
            self._index.setdefault(term, set()).add(item.key)
        self._item_terms[item.key] = counts

    def remove(self, key: str) -> None:
        """Remove a key from the index."""
        for term_set in self._index.values():
            term_set.discard(key)
        self._item_terms.pop(key, None)

    def search(self, query: str, top_n: int = 10) -> List[str]:
        """Return keys ranked by term overlap with the query."""
        query_terms = self._tokenize(query)
        if not query_terms:
            return []
        scores: Dict[str, int] = {}
        for term in query_terms:
            for key in self._index.get(term, set()):
                scores[key] = scores.get(key, 0) + 1
        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        return [k for k, _ in ranked[:top_n]]

    def _tokenize(self, text: str) -> List[str]:
        words = re.findall(r"\w+", text)
        if not self.config.case_sensitive:
            words = [w.lower() for w in words]
        return [w for w in words if len(w) >= self.config.min_token_length]

    @staticmethod
    def _extract_text(content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, dict):
            return " ".join(str(v) for v in content.values())
        if isinstance(content, (list, tuple)):
            return " ".join(str(x) for x in content)
        return str(content)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "type": "MemoryIndex",
            "unique_terms": len(self._index),
            "indexed_items": len(self._item_terms),
        }

