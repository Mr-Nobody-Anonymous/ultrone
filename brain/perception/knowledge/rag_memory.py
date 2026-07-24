"""Retrieval-Augmented Generation memory for ULTRONE."""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from .vector_db import VectorDatabase, VectorDBConfig, VectorItem

logger = logging.getLogger("Ultrone.Brain.Perception.Knowledge.RAG")


@dataclass
class RAGConfig:
    """Configuration for RAG memory."""
    k_retrieval: int = 5
    relevance_threshold: float = 0.5
    use_reranking: bool = True


class RAGMemory:
    """Retrieval-Augmented Generation memory system.

    Combines:
    - Vector search for relevant memory retrieval
    - Reranking for precision
    - Context window assembly for LLM consumption

    Integrates with ULTRONE's memory systems and orchestration.
    """

    def __init__(self, config: Optional[RAGConfig] = None):
        self.config = config or RAGConfig()
        self._vector_db = VectorDatabase()

    def store(self, id: str, embedding: np.ndarray, metadata: Dict[str, Any]) -> None:
        """Store a memory with its embedding."""
        item = VectorItem(id=id, vector=embedding, metadata=metadata)
        self._vector_db.insert(item)

    def retrieve(self, query_embedding: np.ndarray, k: Optional[int] = None) -> List[Tuple[str, float, Dict[str, Any]]]:
        """Retrieve top-k relevant memories.

        Returns list of (id, score, metadata) sorted by relevance.
        """
        k = k or self.config.k_retrieval
        results = self._vector_db.search(query_embedding, k=k)
        filtered = [(id, score, self._vector_db.get_item(id).metadata if self._vector_db.get_item(id) else {})
                     for id, score in results if score >= self.config.relevance_threshold]
        return filtered

    def assemble_context(self, query_embedding: np.ndarray, k: Optional[int] = None) -> str:
        """Assemble a context string for LLM consumption."""
        memories = self.retrieve(query_embedding, k)
        parts = []
        for i, (id, score, metadata) in enumerate(memories):
            parts.append(f"[Memory {i+1}] (relevance: {score:.2f})")
            for k, v in metadata.items():
                parts.append(f"  {k}: {v}")
        return "\n".join(parts)

    def get_stats(self) -> Dict[str, Any]:
        return {"type": "RAGMemory", "stores": self._vector_db.size()}
