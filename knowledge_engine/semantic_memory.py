# Copyright (c) Ultrone Contributors. All rights reserved.
"""Semantic knowledge memory - general concepts, facts, and relationships."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .base import (
    KnowledgeCategory,
    KnowledgeEntry,
    KnowledgeMemoryBase,
    KnowledgeSource,
)


class SemanticKnowledgeMemory(KnowledgeMemoryBase):
    """Stores semantic/general knowledge (concepts, facts, relationships)."""

    def __init__(self, capacity: int = 50000, name: str = "semantic_knowledge"):
        super().__init__(capacity=capacity, name=name)

    def store_concept(
        self,
        concept: str,
        definition: str,
        tags: Optional[List[str]] = None,
        confidence_score: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> KnowledgeEntry:
        """Store a concept definition."""
        entry = KnowledgeEntry(
            content=definition,
            category=self._category_from_content(definition),
            source=KnowledgeSource.SYNTHESIS,
            confidence_score=confidence_score,
            tags=tags or [],
            entities=[concept],
            metadata=metadata or {},
        )
        return self.store(entry)

    def find_concept(self, concept: str) -> List[KnowledgeEntry]:
        """Find entries related to a concept (case-insensitive)."""
        c = concept.lower()
        return [
            e for e in self._entries.values()
            if any(c == ent.lower() for ent in e.entities)
            or c in e.content.lower()
        ]

    @staticmethod
    def _category_from_content(content: str) -> KnowledgeCategory:
        lower = content.lower()
        if any(w in lower for w in ("algorithm", "method", "approach", "technique")):
            return KnowledgeCategory.METHOD
        if any(w in lower for w in ("result", "improvement", "outperform", "accuracy")):
            return KnowledgeCategory.RESULT
        if any(w in lower for w in ("hyperparameter", "learning rate", "batch size")):
            return KnowledgeCategory.HYPERPARAMETER
        return KnowledgeCategory.THEORY
