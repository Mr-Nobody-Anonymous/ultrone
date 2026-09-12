# Copyright (c) Ultrone Contributors. All rights reserved.
"""Vector memory for the ULTRONE autonomous research platform.

Provides dense vector embeddings for semantic retrieval over knowledge
entries. Supports pluggable embedding backends (hash, TF-IDF, or external
LLM embeddings), cosine similarity search, and incremental indexing.
"""

from __future__ import annotations

import hashlib
import logging
import math
import re
import time
from collections import Counter
from typing import Any, Callable, Dict, List, Optional, Tuple

from .base import KnowledgeEntry

logger = logging.getLogger("Ultrone.KnowledgeEngine.VectorMemory")


def _default_tokenizer(text: str) -> List[str]:
    """Simple word tokenizer with lowercasing."""
    return re.findall(r"[a-z0-9_]+", text.lower())


class VectorMemory:
    """Dense vector memory for semantic retrieval over knowledge entries.

    Features
    --------
    - Pluggable embedding backends (hash / TF-IDF / external callable)
    - Cosine similarity search
    - Incremental indexing
    - Confidence-weighted retrieval
    """

    def __init__(
        self,
        embedding_dim: int = 256,
        backend: str = "hash",
        embedder: Optional[Callable[[str], List[float]]] = None,
        tokenizer: Optional[Callable[[str], List[str]]] = None,
    ):
        self.embedding_dim = embedding_dim
        self.backend = backend
        self.embedder = embedder
        self.tokenizer = tokenizer or _default_tokenizer
        self._vectors: Dict[str, List[float]] = {}
        self._doc_freq: Counter = Counter()
        self._total_docs: int = 0
        self._indexed_at: Dict[str, float] = {}

    # ------------------------------------------------------------------
    # Embedding backends
    # ------------------------------------------------------------------
    def _hash_embed(self, text: str) -> List[float]:
        """Feature-hash embedding: bag-of-words with hashing trick."""
        vector = [0.0] * self.embedding_dim
        for token in self.tokenizer(text):
            digest = hashlib.md5(token.encode("utf-8")).digest()
            idx = int.from_bytes(digest[:4], "big") % self.embedding_dim
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[idx] += sign
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [v / norm for v in vector]

    def _tfidf_embed(self, text: str) -> List[float]:
        """TF-IDF-like embedding (approximate using hash feature space)."""
        tf = Counter(self.tokenizer(text))
        if not tf:
            return [0.0] * self.embedding_dim
        vector = [0.0] * self.embedding_dim
        for token, count in tf.items():
            digest = hashlib.md5(token.encode("utf-8")).digest()
            idx = int.from_bytes(digest[:4], "big") % self.embedding_dim
            # TF-IDF: term freq * log(N / doc_freq)
            df = self._doc_freq.get(token, 1)
            idf = math.log((self._total_docs + 1) / (df + 1)) + 1.0
            vector[idx] += (count / len(tf)) * idf
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [v / norm for v in vector]

    def _embed_text(self, text: str) -> List[float]:
        """Embed text using configured backend."""
        if self.embedder is not None:
            vec = self.embedder(text)
            if len(vec) != self.embedding_dim:
                # Pad or truncate
                if len(vec) > self.embedding_dim:
                    vec = vec[: self.embedding_dim]
                else:
                    vec = vec + [0.0] * (self.embedding_dim - len(vec))
            return vec
        if self.backend == "tfidf":
            return self._tfidf_embed(text)
        return self._hash_embed(text)

    # ------------------------------------------------------------------
    # Indexing
    # ------------------------------------------------------------------
    def index(self, entry: KnowledgeEntry) -> None:
        """Embed and index a knowledge entry."""
        text = f"{entry.content} {' '.join(entry.tags)} {' '.join(entry.entities)}"
        vec = self._embed_text(text)
        self._vectors[entry.entry_id] = vec

        # Update doc frequencies for TF-IDF backend
        tokens = set(self.tokenizer(text))
        for token in tokens:
            self._doc_freq[token] += 1
        self._total_docs += 1
        self._indexed_at[entry.entry_id] = time.time()

    def index_batch(self, entries: List[KnowledgeEntry]) -> int:
        """Index multiple entries. Returns number indexed."""
        count = 0
        for entry in entries:
            self.index(entry)
            count += 1
        return count

    def remove(self, entry_id: str) -> bool:
        """Remove an entry's vector."""
        if entry_id in self._vectors:
            del self._vectors[entry_id]
            self._indexed_at.pop(entry_id, None)
            return True
        return False

    def clear(self) -> None:
        self._vectors.clear()
        self._doc_freq.clear()
        self._total_docs = 0
        self._indexed_at.clear()

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------
    @staticmethod
    def cosine_similarity(a: List[float], b: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot / (norm_a * norm_b)

    def search(
        self,
        query: str,
        limit: int = 10,
        min_score: float = 0.0,
    ) -> List[Tuple[str, float]]:
        """Search for entries most similar to query.

        Returns list of (entry_id, similarity_score) tuples sorted by score.
        Uses vectorized NumPy operations when available for speed.
        """
        query_vec = self._embed_text(query)
        if not self._vectors:
            return []

        try:
            import numpy as np

            # Vectorized search
            ids = list(self._vectors.keys())
            matrix = np.array([self._vectors[eid] for eid in ids], dtype=np.float32)
            q = np.array(query_vec, dtype=np.float32).reshape(1, -1)

            # Cosine similarity via matrix multiplication
            norms = np.linalg.norm(matrix, axis=1, keepdims=True)
            norms[norms == 0] = 1e-10
            matrix_normed = matrix / norms
            q_norm = np.linalg.norm(q) or 1e-10
            q_normed = q / q_norm
            scores = (matrix_normed @ q_normed.T).ravel()

            # Filter by min_score
            mask = scores >= min_score
            filtered_ids = [ids[i] for i in range(len(ids)) if mask[i]]
            filtered_scores = scores[mask]

            # Sort by score descending
            order = np.argsort(filtered_scores)[::-1][:limit]
            return [(filtered_ids[i], float(filtered_scores[i])) for i in order]
        except ImportError:
            # Fallback to pure-Python
            results: List[Tuple[str, float]] = []
            for entry_id, vec in self._vectors.items():
                score = self.cosine_similarity(query_vec, vec)
                if score >= min_score:
                    results.append((entry_id, score))
            results.sort(key=lambda x: x[1], reverse=True)
            return results[:limit]

    def search_with_entries(
        self,
        query: str,
        entries: Dict[str, KnowledgeEntry],
        limit: int = 10,
        min_score: float = 0.0,
    ) -> List[Tuple[KnowledgeEntry, float]]:
        """Search and return actual KnowledgeEntry objects."""
        results = self.search(query, limit=limit, min_score=min_score)
        output = []
        for entry_id, score in results:
            entry = entries.get(entry_id)
            if entry:
                output.append((entry, score))
        return output

    def get_vector(self, entry_id: str) -> Optional[List[float]]:
        return self._vectors.get(entry_id)

    def similarity_between(self, id_a: str, id_b: str) -> float:
        """Compute similarity between two indexed entries."""
        vec_a = self._vectors.get(id_a)
        vec_b = self._vectors.get(id_b)
        if vec_a is None or vec_b is None:
            return 0.0
        return self.cosine_similarity(vec_a, vec_b)

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------
    def get_stats(self) -> Dict[str, Any]:
        return {
            "type": "VectorMemory",
            "backend": self.backend,
            "embedding_dim": self.embedding_dim,
            "indexed_entries": len(self._vectors),
            "total_docs": self._total_docs,
            "unique_tokens": len(self._doc_freq),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "embedding_dim": self.embedding_dim,
            "backend": self.backend,
            "vectors": {eid: vec for eid, vec in self._vectors.items()},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VectorMemory":
        vm = cls(
            embedding_dim=data.get("embedding_dim", 256),
            backend=data.get("backend", "hash"),
        )
        for eid, vec in data.get("vectors", {}).items():
            vm._vectors[eid] = vec
        return vm
