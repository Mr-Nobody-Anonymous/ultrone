# Copyright (c) Ultrone Contributors. All rights reserved.
"""Episodic knowledge memory — time-stamped, event-based knowledge records."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from .base import (
    ConfidenceLevel,
    KnowledgeEntry,
    KnowledgeMemoryBase,
    KnowledgeSource,
)


class EpisodicKnowledgeMemory(KnowledgeMemoryBase):
    """Stores episodic knowledge: time-bound events, experiments, and outcomes.

    Each entry is automatically tagged with a timestamp so that recall can be
    time-filtered. Useful for remembering what happened during a specific run,
    a benchmark, or a research cycle.
    """

    def __init__(self, capacity: int = 50_000, name: str = "episodic_knowledge"):
        super().__init__(capacity=capacity, name=name)

    def record_event(
        self,
        event_type: str,
        description: str,
        outcome: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        confidence_score: float = 0.7,
    ) -> KnowledgeEntry:
        """Record a time-stamped event."""
        entry = KnowledgeEntry(
            content=description,
            category=self._category_for_event(event_type),
            source=KnowledgeSource.EXPERIMENT,
            confidence=ConfidenceLevel.HIGH if confidence_score >= 0.7 else ConfidenceLevel.MEDIUM,
            confidence_score=confidence_score,
            tags=["episodic", event_type] + (["outcome:" + outcome] if outcome else []),
            metadata=metadata or {},
        )
        return self.store(entry)

    def recall_since(self, since_ts: float, limit: int = 50) -> List[KnowledgeEntry]:
        """Recall entries created after a timestamp."""
        results = [
            e for e in self._entries.values() if e.created_at >= since_ts
        ]
        results.sort(key=lambda e: e.created_at, reverse=True)
        return results[:limit]

    def recall_by_event_type(self, event_type: str) -> List[KnowledgeEntry]:
        """Recall entries matching an event type tag."""
        return self.filter_by_tags([event_type])

    @staticmethod
    def _category_for_event(event_type: str):
        from .base import KnowledgeCategory
        et = event_type.lower()
        if "benchmark" in et or "result" in et:
            return KnowledgeCategory.RESULT
        if "experiment" in et:
            return KnowledgeCategory.METHOD
        if "hypothesis" in et:
            return KnowledgeCategory.THEORY
        return KnowledgeCategory.INSIGHT
