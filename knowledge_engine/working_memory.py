# Copyright (c) Ultrone Contributors. All rights reserved.
"""Working knowledge memory — short-term, high-access context with TTL."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from .base import (
    KnowledgeEntry,
    KnowledgeMemoryBase,
)


class WorkingKnowledgeMemory(KnowledgeMemoryBase):
    """Short-term working memory with time-to-live (TTL) eviction.

    Entries expire after ``ttl_seconds`` and are automatically evicted on
    access/stats calls. Used for active research context, in-progress
    reasoning, and transient scratch knowledge.
    """

    def __init__(
        self,
        capacity: int = 5_000,
        name: str = "working_knowledge",
        ttl_seconds: float = 1800.0,
    ):
        super().__init__(capacity=capacity, name=name)
        self.ttl_seconds = ttl_seconds
        self._last_access: Dict[str, float] = {}

    def store(self, entry: KnowledgeEntry) -> KnowledgeEntry:
        result = super().store(entry)
        self._last_access[entry.entry_id] = time.time()
        return result

    def get(self, entry_id: str) -> Optional[KnowledgeEntry]:
        self._evict_expired()
        entry = super().get(entry_id)
        if entry:
            self._last_access[entry_id] = time.time()
        return entry

    def recall(self, entry_id: str) -> Optional[KnowledgeEntry]:
        return self.get(entry_id)

    def search(self, query: str, limit: int = 20) -> List[KnowledgeEntry]:
        self._evict_expired()
        results = super().search(query, limit=limit)
        for e in results:
            self._last_access[e.entry_id] = time.time()
        return results

    def touch(self, entry_id: str) -> None:
        """Refresh the TTL for an entry."""
        if entry_id in self._entries:
            self._last_access[entry_id] = time.time()

    def _evict_expired(self) -> None:
        now = time.time()
        expired = [eid for eid, ts in self._last_access.items() if now - ts > self.ttl_seconds]
        for eid in expired:
            self._entries.pop(eid, None)
            self._last_access.pop(eid, None)

    def get_stats(self) -> Dict[str, Any]:
        self._evict_expired()
        stats = super().get_stats()
        stats["ttl_seconds"] = self.ttl_seconds
        return stats
