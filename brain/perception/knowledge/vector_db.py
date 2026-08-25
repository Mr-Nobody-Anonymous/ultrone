"""Vector database for embedding-based memory and retrieval."""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("Ultrone.Brain.Perception.Knowledge.VectorDB")


@dataclass
class VectorDBConfig:
    """Configuration for vector database."""
    dimension: int = 768
    index_type: str = "flat"  # flat, ivf, hnsw
    similarity: str = "cosine"  # cosine, euclidean, dot
    max_items: int = 100_000


@dataclass
class VectorItem:
    """A stored vector with metadata."""
    id: str
    vector: np.ndarray
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0


class VectorDatabase:
    """Vector database for storing and retrieving embeddings.

    Provides:
    - Insert/delete vectors with metadata
    - k-NN similarity search (vectorized with NumPy)
    - Cosine, Euclidean, dot-product similarity
    - Metadata filtering
    """

    def __init__(self, config: Optional[VectorDBConfig] = None):
        self.config = config or VectorDBConfig()
        self._items: Dict[str, VectorItem] = {}
        self._vectors: List[np.ndarray] = []
        self._ids: List[str] = []

    def insert(self, item: VectorItem) -> None:
        """Insert a vector item."""
        self._items[item.id] = item
        self._vectors.append(item.vector)
        self._ids.append(item.id)
        # Limit size
        if len(self._vectors) > self.config.max_items:
            oldest = self._ids.pop(0)
            self._vectors.pop(0)
            self._items.pop(oldest, None)

    def insert_batch(self, items: List[VectorItem]) -> int:
        """Insert multiple vector items at once. Returns number inserted."""
        count = 0
        for item in items:
            self.insert(item)
            count += 1
        return count

    def delete(self, id: str) -> None:
        """Delete a vector by ID."""
        if id in self._items:
            idx = self._ids.index(id)
            self._ids.pop(idx)
            self._vectors.pop(idx)
            del self._items[id]

    def search(self, query: np.ndarray, k: int = 10) -> List[Tuple[str, float]]:
        """Search for k nearest neighbors using vectorized NumPy operations.

        Returns list of (id, similarity_score) sorted by score descending.
        """
        if not self._vectors:
            return []

        # Vectorize: stack all vectors into a single matrix
        matrix = np.stack(self._vectors) if len(self._vectors) > 1 else self._vectors[0][None, :]
        query_vec = np.asarray(query, dtype=np.float32).reshape(1, -1)

        if self.config.similarity == "cosine":
            # Normalize once (cache normalization for speed)
            norms = np.linalg.norm(matrix, axis=1, keepdims=True)
            norms[norms == 0] = 1e-10
            matrix_normed = matrix / norms
            q_norm = np.linalg.norm(query_vec) or 1e-10
            q_normed = query_vec / q_norm
            scores = (matrix_normed @ q_normed.T).ravel()
        elif self.config.similarity == "euclidean":
            # Negative Euclidean distance (higher = closer)
            diff = matrix - query_vec
            scores = -np.linalg.norm(diff, axis=1)
        else:  # dot
            scores = (matrix @ query_vec.T).ravel()

        # Get top-k indices
        k = min(k, len(scores))
        if k <= 0:
            return []
        top_indices = np.argsort(scores)[::-1][:k]
        return [(self._ids[i], float(scores[i])) for i in top_indices]

    def get_item(self, id: str) -> Optional[VectorItem]:
        return self._items.get(id)

    def size(self) -> int:
        return len(self._items)

    def clear(self) -> None:
        self._items.clear()
        self._vectors.clear()
        self._ids.clear()

    def get_stats(self) -> Dict[str, Any]:
        return {
            "type": "VectorDatabase",
            "size": len(self._items),
            "dimension": self.config.dimension,
            "similarity": self.config.similarity,
        }