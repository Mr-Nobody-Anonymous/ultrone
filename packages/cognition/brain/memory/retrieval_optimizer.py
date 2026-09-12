# Copyright (c) Ultrone Contributors. All rights reserved.
"""Retrieval Optimizer — combines index search, importance ranking, and
caching to return the most relevant memory items efficiently.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .base import MemoryItem
from .importance import ImportanceScorer
from .memory_index import MemoryIndex

logger = logging.getLogger("Ultrone.Brain.Memory.Retrieval")


@dataclass
class RetrievalConfig:
    """Configuration for retrieval optimization."""
    cache_size: int = 100
    default_top_n: int = 10


class RetrievalOptimizer:
    """Optimizes memory retrieval with indexing, ranking, and caching."""

    def __init__(
        self,
        index: Optional[MemoryIndex] = None,
        scorer: Optional[ImportanceScorer] = None,
        config: Optional[RetrievalConfig] = None,
    ):
        self.index = index or MemoryIndex()
        self.scorer = scorer or ImportanceScorer()
        self.config = config or RetrievalConfig()
        self._cache: Dict[str, List[str]] = {}
        self._cache_order: List[str] = []

    def index_item(self, item: MemoryItem) -> None:
        """Index an item and record its access."""
        self.index.add(item)
        self.scorer.record_access(item.key)

    def retrieve(self, items: List[MemoryItem], query: str, top_n: Optional[int] = None) -> List[MemoryItem]:
        """Retrieve the most relevant items for a query."""
        top_n = top_n or self.config.default_top_n
        # Cache hit
        if query in self._cache:
            self._touch_cache(query)
            keys = self._cache[query][:top_n]
            by_key = {it.key: it for it in items}
            return [by_key[k] for k in keys if k in by_key]

        # Index search
        keys = self.index.search(query, top_n=top_n * 3)
        matched = [it for it in items if it.key in keys]
        if not matched:
            # Fall back to full scan ranked by importance
            matched = sorted(items, key=lambda it: self.scorer.score(it), reverse=True)
        ranked = self.scorer.rank(matched, top_n=top_n)

        self._cache[query] = [it.key for it in ranked]
        self._touch_cache(query)
        self._evict_cache()
        return ranked

    def _touch_cache(self, query: str) -> None:
        if query in self._cache_order:
            self._cache_order.remove(query)
        self._cache_order.append(query)

    def _evict_cache(self) -> None:
        while len(self._cache_order) > self.config.cache_size:
            oldest = self._cache_order.pop(0)
            self._cache.pop(oldest, None)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "type": "RetrievalOptimizer",
            "cache_entries": len(self._cache),
            "index": self.index.get_stats(),
            "scorer": self.scorer.get_stats(),
        }

