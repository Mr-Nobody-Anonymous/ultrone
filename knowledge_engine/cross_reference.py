# Copyright (c) Ultrone Contributors. All rights reserved.
"""Cross-reference discovery for the ULTRONE autonomous research platform.

Discovers relationships between knowledge entries across memory layers,
detects duplicates, identifies complementary information, and finds
related research via vector similarity and graph connectivity.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set, Tuple

from .base import KnowledgeEntry
from .vector_memory import VectorMemory
from .knowledge_graph import KnowledgeGraph

logger = logging.getLogger("Ultrone.KnowledgeEngine.CrossReference")


class CrossReferenceEngine:
    """Discovers cross-references between knowledge entries.

    Features
    --------
    - Similarity-based deduplication
    - Graph-based relatedness
    - Tag overlap scoring
    - Cross-layer reference discovery
    """

    def __init__(
        self,
        vector_memory: Optional[VectorMemory] = None,
        knowledge_graph: Optional[KnowledgeGraph] = None,
        similarity_threshold: float = 0.75,
    ):
        self.vector_memory = vector_memory or VectorMemory()
        self.knowledge_graph = knowledge_graph or KnowledgeGraph()
        self.similarity_threshold = similarity_threshold

    def find_duplicates(
        self,
        entries: List[KnowledgeEntry],
        threshold: Optional[float] = None,
    ) -> List[Tuple[KnowledgeEntry, KnowledgeEntry, float]]:
        """Find duplicate entries based on vector similarity.

        Returns list of (entry_a, entry_b, similarity) tuples.
        """
        threshold = threshold or self.similarity_threshold
        results = []
        # Index all entries
        for entry in entries:
            self.vector_memory.index(entry)

        # Compare pairwise (only first occurrence considered)
        compared: Set[str] = set()
        for i, entry_a in enumerate(entries):
            for j, entry_b in enumerate(entries):
                if i >= j:
                    continue
                pair = frozenset([entry_a.entry_id, entry_b.entry_id])
                if pair in compared:
                    continue
                compared.add(pair)
                score = self.vector_memory.similarity_between(entry_a.entry_id, entry_b.entry_id)
                if score >= threshold:
                    results.append((entry_a, entry_b, score))
        return results

    def find_complementary(
        self,
        entry: KnowledgeEntry,
        candidates: List[KnowledgeEntry],
        limit: int = 5,
    ) -> List[Tuple[KnowledgeEntry, float]]:
        """Find entries that complement the given entry (different but related).

        Complementary = moderate similarity, different categories.
        """
        self.vector_memory.index(entry)
        for cand in candidates:
            self.vector_memory.index(cand)

        results = []
        for cand in candidates:
            if cand.entry_id == entry.entry_id:
                continue
            score = self.vector_memory.similarity_between(entry.entry_id, cand.entry_id)
            # Complementary: moderate similarity (0.2-0.7) and different category
            if 0.2 <= score <= 0.7 and cand.category != entry.category:
                results.append((cand, score))
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]

    def find_related_by_tags(
        self,
        entry: KnowledgeEntry,
        candidates: List[KnowledgeEntry],
        limit: int = 5,
    ) -> List[Tuple[KnowledgeEntry, float]]:
        """Find entries related by shared tags."""
        entry_tags = set(entry.tags)
        results = []
        for cand in candidates:
            if cand.entry_id == entry.entry_id:
                continue
            overlap = entry_tags & set(cand.tags)
            if overlap:
                score = len(overlap) / max(1, len(entry_tags | set(cand.tags)))
                results.append((cand, score))
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]

    def find_graph_related(
        self,
        entry: KnowledgeEntry,
        graph: Optional[KnowledgeGraph] = None,
        limit: int = 5,
    ) -> List[str]:
        """Find graph-related node IDs for an entry."""
        g = graph or self.knowledge_graph
        related = g.find_related(entry.entry_id)
        return [r.node_id for r in related[:limit]]

    def create_references(
        self,
        entries: List[KnowledgeEntry],
        limit_per_entry: int = 3,
    ) -> Dict[str, List[str]]:
        """Auto-create cross-references between entries.

        Returns dict: entry_id -> list of related entry_ids.
        """
        references: Dict[str, List[str]] = {}
        for entry in entries:
            related = self.find_complementary(entry, entries, limit=limit_per_entry)
            tag_related = self.find_related_by_tags(entry, entries, limit=limit_per_entry)
            # Merge by entry_id
            merged: Dict[str, float] = {}
            for cand, score in related:
                merged[cand.entry_id] = max(score, merged.get(cand.entry_id, 0.0))
            for cand, score in tag_related:
                merged[cand.entry_id] = max(score, merged.get(cand.entry_id, 0.0))
            # Sort by score
            sorted_ids = sorted(merged.items(), key=lambda x: x[1], reverse=True)
            references[entry.entry_id] = [eid for eid, _ in sorted_ids[:limit_per_entry]]
        return references

    def get_stats(self) -> Dict[str, Any]:
        return {
            "type": "CrossReferenceEngine",
            "similarity_threshold": self.similarity_threshold,
            "vector_memory": self.vector_memory.get_stats(),
            "knowledge_graph": self.knowledge_graph.get_stats(),
        }
