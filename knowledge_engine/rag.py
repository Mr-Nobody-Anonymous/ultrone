# Copyright (c) Ultrone Contributors. All rights reserved.
"""Retrieval-Augmented Generation (RAG) pipeline for ULTRONE.

Combines vector memory, knowledge graph, and citation database for
context-aware retrieval used by research agents. Supports hybrid search,
context assembly, and prompt building.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

from .base import KnowledgeEntry
from .vector_memory import VectorMemory
from .knowledge_graph import KnowledgeGraph
from .citation_db import CitationDatabase

logger = logging.getLogger("Ultrone.KnowledgeEngine.RAG")


class RAGPipeline:
    """Hybrid retrieval pipeline for research queries.

    Features
    --------
    - Vector semantic search
    - Keyword search fallback
    - Knowledge graph expansion
    - Citation-aware context
    - Prompt template assembly
    """

    def __init__(
        self,
        vector_memory: Optional[VectorMemory] = None,
        knowledge_graph: Optional[KnowledgeGraph] = None,
        citation_db: Optional[CitationDatabase] = None,
        generator: Optional[Callable[[str], str]] = None,
    ):
        self.vector_memory = vector_memory or VectorMemory()
        self.knowledge_graph = knowledge_graph or KnowledgeGraph()
        self.citation_db = citation_db or CitationDatabase()
        self.generator = generator
        self._entries: Dict[str, KnowledgeEntry] = {}

    def register_entry(self, entry: KnowledgeEntry) -> None:
        """Register an entry for retrieval."""
        self._entries[entry.entry_id] = entry
        self.vector_memory.index(entry)

    def register_entries(self, entries: List[KnowledgeEntry]) -> None:
        """Register multiple entries."""
        for entry in entries:
            self.register_entry(entry)

    def retrieve(
        self,
        query: str,
        limit: int = 5,
        hybrid: bool = True,
        expand_graph: bool = True,
    ) -> List[Tuple[KnowledgeEntry, float]]:
        """Retrieve relevant knowledge entries for a query.

        Returns list of (entry, score) tuples.
        """
        results: Dict[str, Tuple[KnowledgeEntry, float]] = {}

        # 1. Vector search (semantic)
        if self.vector_memory is not None:
            for entry, score in self.vector_memory.search_with_entries(query, self._entries, limit=limit):
                results[entry.entry_id] = (entry, max(score, results.get(entry.entry_id, (None, 0.0))[1]))

        # 2. Keyword search (lexical)
        if hybrid:
            for eid in self._entries:
                entry = self._entries[eid]
                q = query.lower()
                score = 0.0
                if q in entry.content.lower():
                    score = 0.6
                elif any(t in entry.content.lower() for t in query.lower().split()):
                    score = 0.3
                if score > 0.0:
                    current = results.get(eid, (entry, 0.0))[1]
                    results[eid] = (entry, max(score, current))

        # 3. Knowledge graph expansion
        if expand_graph and self.knowledge_graph is not None:
            # Find graph nodes matching query, then expand to neighbors
            expanded_ids = set()
            for entry_id, (entry, score) in results.items():
                # Look up related entries via graph relationships
                for rel in self.knowledge_graph.find_related(entry_id):
                    expanded_ids.add(rel.node_id)
            # Add entries whose IDs match expanded graph nodes
            for nid in expanded_ids:
                if nid in self._entries:
                    entry = self._entries[nid]
                    if entry.entry_id not in results:
                        results[entry.entry_id] = (entry, 0.4)

        # Sort by score desc, return top-limit
        sorted_results = sorted(results.values(), key=lambda x: x[1], reverse=True)
        return sorted_results[:limit]

    def build_context(
        self,
        query: str,
        limit: int = 5,
        include_citations: bool = True,
    ) -> str:
        """Build a context string for LLM generation."""
        retrieved = self.retrieve(query, limit=limit)
        if not retrieved:
            return ""

        parts = []
        for i, (entry, score) in enumerate(retrieved, 1):
            part = f"[{i}] (confidence={score:.2f}) {entry.content}"
            if entry.tags:
                part += f" [tags: {', '.join(entry.tags)}]"
            if include_citations and entry.metadata.get("citation_id"):
                cit = self.citation_db.get(entry.metadata["citation_id"])
                if cit:
                    authors = ", ".join(cit.authors[:3])
                    part += f" (Source: {cit.title} by {authors}, {cit.year})"
            parts.append(part)

        return "\n".join(parts)

    def generate(
        self,
        query: str,
        system_prompt: Optional[str] = None,
        limit: int = 5,
    ) -> str:
        """Generate a response using retrieved context and optional generator."""
        context = self.build_context(query, limit=limit)
        if self.generator is None:
            return context

        prompt = ""
        if system_prompt:
            prompt += f"{system_prompt}\n\n"
        prompt += f"Query: {query}\n\n"
        prompt += f"Context:\n{context}\n\n"
        prompt += "Answer:"

        try:
            return self.generator(prompt)
        except Exception as e:
            logger.error("RAG generation error: %s", e)
            return context

    def get_stats(self) -> Dict[str, Any]:
        return {
            "type": "RAGPipeline",
            "registered_entries": len(self._entries),
            "vector_memory": self.vector_memory.get_stats() if self.vector_memory else None,
            "knowledge_graph": self.knowledge_graph.get_stats() if self.knowledge_graph else None,
            "citation_db": self.citation_db.get_stats() if self.citation_db else None,
        }
