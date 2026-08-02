# Copyright (c) Ultrone Contributors. All rights reserved.
"""Base data structures for the knowledge engine."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class KnowledgeSource(Enum):
    """Provenance of a knowledge entry."""
    PAPER = "paper"
    EXPERIMENT = "experiment"
    BENCHMARK = "benchmark"
    CODE = "code"
    DOCUMENTATION = "documentation"
    HYPOTHESIS = "hypothesis"
    ANALYSIS = "analysis"
    HUMAN = "human"
    SYNTHESIS = "synthesis"
    OTHER = "other"


class KnowledgeCategory(Enum):
    """Category of knowledge."""
    ALGORITHM = "algorithm"
    ARCHITECTURE = "architecture"
    THEORY = "theory"
    METHOD = "method"
    RESULT = "result"
    DATASET = "dataset"
    METRIC = "metric"
    HYPERPARAMETER = "hyperparameter"
    INSIGHT = "insight"
    LIMITATION = "limitation"
    BEST_PRACTICE = "best_practice"
    UNKNOWN = "unknown"


class ConfidenceLevel(Enum):
    """Confidence level of a knowledge entry."""
    VERIFIED = "verified"          # Confirmed by experiment/benchmark
    HIGH = "high"                  # Strong evidence
    MEDIUM = "medium"              # Some evidence
    LOW = "low"                    # Weak/uncertain evidence
    HYPOTHETICAL = "hypothetical"  # Not yet validated
    UNKNOWN = "unknown"


@dataclass
class KnowledgeEntry:
    """A single, versioned, source-attributed knowledge entry.

    Attributes
    ----------
    entry_id : str
        Unique identifier for the entry.
    content : str
        The knowledge content (text/description).
    category : KnowledgeCategory
        Category of knowledge.
    source : KnowledgeSource
        Where this knowledge came from.
    confidence : ConfidenceLevel
        Confidence level.
    confidence_score : float
        Numeric confidence in [0, 1].
    tags : List[str]
        Tags for categorization.
    entities : List[str]
        Linked entity names.
    related_entry_ids : List[str]
        IDs of related knowledge entries.
    metadata : Dict[str, Any]
        Arbitrary metadata.
    version : int
        Version counter (incremented on update).
    created_at : float
        Unix timestamp of creation.
    updated_at : float
        Unix timestamp of last update.
    """

    content: str
    category: KnowledgeCategory = KnowledgeCategory.UNKNOWN
    source: KnowledgeSource = KnowledgeSource.OTHER
    confidence: ConfidenceLevel = ConfidenceLevel.UNKNOWN
    confidence_score: float = 0.5
    entry_id: str = field(default_factory=lambda: f"K-{uuid.uuid4().hex[:12]}")
    tags: List[str] = field(default_factory=list)
    entities: List[str] = field(default_factory=list)
    related_entry_ids: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    version: int = 1
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "content": self.content,
            "category": self.category.value,
            "source": self.source.value,
            "confidence": self.confidence.value,
            "confidence_score": self.confidence_score,
            "tags": self.tags,
            "entities": self.entities,
            "related_entry_ids": self.related_entry_ids,
            "metadata": self.metadata,
            "version": self.version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KnowledgeEntry":
        return cls(
            content=data.get("content", ""),
            category=KnowledgeCategory(data.get("category", "unknown")),
            source=KnowledgeSource(data.get("source", "other")),
            confidence=ConfidenceLevel(data.get("confidence", "unknown")),
            confidence_score=data.get("confidence_score", 0.5),
            entry_id=data.get("entry_id", f"K-{uuid.uuid4().hex[:12]}"),
            tags=data.get("tags", []),
            entities=data.get("entities", []),
            related_entry_ids=data.get("related_entry_ids", []),
            metadata=data.get("metadata", {}),
            version=data.get("version", 1),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
        )


class KnowledgeMemoryBase:
    """Base interface for all knowledge memory layers."""

    def __init__(self, capacity: int = 10_000, name: str = "knowledge_memory"):
        self.capacity = capacity
        self.name = name
        self._entries: Dict[str, KnowledgeEntry] = {}
        self._created_count: int = 0

    def store(self, entry: KnowledgeEntry) -> KnowledgeEntry:
        """Store a knowledge entry (insert or update)."""
        if entry.entry_id in self._entries:
            # Update existing: bump version, preserve creation time.
            existing = self._entries[entry.entry_id]
            entry.version = existing.version + 1
            entry.created_at = existing.created_at
            entry.updated_at = time.time()
            self._entries[entry.entry_id] = entry
        else:
            self._created_count += 1
            self._entries[entry.entry_id] = entry
        self._enforce_capacity()
        return entry

    def get(self, entry_id: str) -> Optional[KnowledgeEntry]:
        return self._entries.get(entry_id)

    def recall(self, entry_id: str) -> Optional[KnowledgeEntry]:
        return self.get(entry_id)

    def delete(self, entry_id: str) -> bool:
        if entry_id in self._entries:
            del self._entries[entry_id]
            return True
        return False

    def search(self, query: str, limit: int = 20) -> List[KnowledgeEntry]:
        """Simple substring search over content and tags."""
        q = query.lower()
        results = []
        for e in self._entries.values():
            if q in e.content.lower() or any(q in t.lower() for t in e.tags):
                results.append(e)
        results.sort(key=lambda e: e.confidence_score, reverse=True)
        return results[:limit]

    def filter_by_category(self, category: KnowledgeCategory) -> List[KnowledgeEntry]:
        return [e for e in self._entries.values() if e.category == category]

    def filter_by_source(self, source: KnowledgeSource) -> List[KnowledgeEntry]:
        return [e for e in self._entries.values() if e.source == source]

    def filter_by_tags(self, tags: List[str]) -> List[KnowledgeEntry]:
        return [e for e in self._entries.values() if set(tags) & set(e.tags)]

    def all_entries(self) -> List[KnowledgeEntry]:
        return list(self._entries.values())

    def count(self) -> int:
        return len(self._entries)

    def clear(self) -> None:
        self._entries.clear()

    def _enforce_capacity(self) -> None:
        if len(self._entries) > self.capacity:
            # Remove lowest-confidence entries first.
            ordered = sorted(
                self._entries.values(), key=lambda e: (e.confidence_score, e.updated_at)
            )
            for e in ordered[: len(self._entries) - self.capacity]:
                del self._entries[e.entry_id]

    def get_stats(self) -> Dict[str, Any]:
        categories: Dict[str, int] = {}
        for e in self._entries.values():
            categories[e.category.value] = categories.get(e.category.value, 0) + 1
        return {
            "type": type(self).__name__,
            "name": self.name,
            "size": len(self._entries),
            "created_count": self._created_count,
            "capacity": self.capacity,
            "categories": categories,
        }
