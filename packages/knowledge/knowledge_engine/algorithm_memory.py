# Copyright (c) Ultrone Contributors. All rights reserved.
"""Algorithm memory - knowledge about algorithms, architectures, and implementations."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .base import (
    KnowledgeCategory,
    KnowledgeEntry,
    KnowledgeMemoryBase,
    KnowledgeSource,
)


class AlgorithmMemory(KnowledgeMemoryBase):
    """Stores algorithm-specific knowledge: specs, hyperparameters, and implementations."""

    def __init__(self, capacity: int = 50000, name: str = "algorithm_knowledge"):
        super().__init__(capacity=capacity, name=name)

    def store_algorithm(
        self,
        name: str,
        description: str,
        complexity: Optional[str] = None,
        dependencies: Optional[List[str]] = None,
        hyperparameters: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> KnowledgeEntry:
        """Store algorithm knowledge."""
        entry = KnowledgeEntry(
            content=description,
            category=KnowledgeCategory.ALGORITHM,
            source=KnowledgeSource.CODE,
            confidence_score=0.8,
            tags=["algorithm", name] + (tags or []),
            entities=[name],
            metadata={
                **(metadata or {}),
                "name": name,
                "complexity": complexity,
                "dependencies": dependencies or [],
                "hyperparameters": hyperparameters or {},
            },
        )
        return self.store(entry)

    def find_algorithm(self, name: str) -> Optional[KnowledgeEntry]:
        n = name.lower()
        for e in self._entries.values():
            if any(n == ent.lower() for ent in e.entities):
                return e
            if n in e.content.lower():
                return e
        return None

    def get_hyperparameters(self, name: str) -> Dict[str, Any]:
        """Return stored hyperparameters for an algorithm."""
        entry = self.find_algorithm(name)
        if entry:
            return dict((entry.metadata or {}).get("hyperparameters", {}))
        return {}
