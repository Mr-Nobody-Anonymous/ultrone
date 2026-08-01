"""Embedding-based semantic similarity search for knowledge retrieval."""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("Ultrone.Brain.Perception.Knowledge.SemanticSearch")


@dataclass
class SearchConfig:
    """Configuration for semantic search."""
    embedding_dim: int = 768
    top_k: int = 10
    similarity_threshold: float = 0.5
    use_faiss: bool = True
    index_type: str = "flat"  # flat, ivf, hnsw


@dataclass
class SearchResult:
    """Result of a semantic search query."""
    content: str
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[np.ndarray] = None


class SemanticSearch:
    """Performs embedding-based similarity search over stored knowledge."""

    def __init__(self, config: Optional[SearchConfig] = None):
        self.config = config or SearchConfig()
        self._embeddings: List[np.ndarray] = []
        self._documents: List[Dict[str, Any]] = []
        self._index = None

    def add_document(self, content: str, embedding: np.ndarray, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add a document with its embedding to the search index."""
        self._embeddings.append(embedding)
        self._documents.append({
            "content": content,
            "metadata": metadata or {},
        })

    def add_documents(self, contents: List[str], embeddings: List[np.ndarray],
                      metadatas: Optional[List[Dict[str, Any]]] = None) -> None:
        """Add multiple documents with embeddings."""
        for i, (content, emb) in enumerate(zip(contents, embeddings)):
            meta = metadatas[i] if metadatas else {}
            self.add_document(content, emb, meta)

    def search(self, query_embedding: np.ndarray, top_k: Optional[int] = None) -> List[SearchResult]:
        """Search for most similar documents given a query embedding."""
        k = top_k or self.config.top_k
        if not self._embeddings:
            return []

        scores = []
        for doc_emb in self._embeddings:
            sim = self._cosine_similarity(query_embedding, doc_emb)
            scores.append(sim)

        scores = np.array(scores)
        top_indices = np.argsort(scores)[::-1][:k]

        results = []
        for idx in top_indices:
            if scores[idx] >= self.config.similarity_threshold:
                results.append(SearchResult(
                    content=self._documents[idx]["content"],
                    score=float(scores[idx]),
                    metadata=self._documents[idx]["metadata"],
                    embedding=self._embeddings[idx],
                ))
        return results

    def batch_search(self, query_embeddings: np.ndarray, top_k: Optional[int] = None) -> List[List[SearchResult]]:
        """Search multiple queries at once."""
        return [self.search(q, top_k) for q in query_embeddings]

    def remove_document(self, index: int) -> None:
        """Remove a document from the index by its position."""
        if 0 <= index < len(self._documents):
            self._embeddings.pop(index)
            self._documents.pop(index)

    def clear(self) -> None:
        """Clear all documents from the search index."""
        self._embeddings.clear()
        self._documents.clear()
        self._index = None

    @property
    def size(self) -> int:
        return len(self._documents)

    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

