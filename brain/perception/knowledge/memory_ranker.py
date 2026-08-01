"""Memory retrieval scoring and ranking system."""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("Ultrone.Brain.Perception.Knowledge.MemoryRanker")


@dataclass
class RankerConfig:
    """Configuration for memory retrieval ranking."""
    recency_weight: float = 0.3
    relevance_weight: float = 0.5
    importance_weight: float = 0.2
    decay_factor: float = 0.95
    max_age: int = 1000


@dataclass
class RankedMemory:
    """A memory item with its computed rank score."""
    content: str
    score: float
    age: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[np.ndarray] = None


class MemoryRetrievalRanker:
    """Scores and ranks retrieved memories using multi-factor scoring."""

    def __init__(self, config: Optional[RankerConfig] = None):
        self.config = config or RankerConfig()

    def rank(self, memories: List[Dict[str, Any]],
             query_embedding: Optional[np.ndarray] = None) -> List[RankedMemory]:
        """Rank memories based on recency, relevance, and importance."""
        scored = []
        for mem in memories:
            recency = self._compute_recency_score(mem.get("age", 0))
            relevance = self._compute_relevance_score(
                mem.get("embedding"), query_embedding
            ) if query_embedding is not None and mem.get("embedding") is not None else 0.5
            importance = self._compute_importance_score(mem.get("importance", 0.5))

            score = (
                self.config.recency_weight * recency +
                self.config.relevance_weight * relevance +
                self.config.importance_weight * importance
            )

            scored.append(RankedMemory(
                content=mem.get("content", ""),
                score=float(score),
                age=mem.get("age", 0),
                metadata=mem.get("metadata", {}),
                embedding=mem.get("embedding"),
            ))

        scored.sort(key=lambda x: x.score, reverse=True)
        return scored

    def rerank(self, memories: List[RankedMemory],
               query_embedding: Optional[np.ndarray] = None) -> List[RankedMemory]:
        """Re-rank already scored memories with a new query."""
        return self.rank(
            [{"content": m.content, "age": m.age, "metadata": m.metadata,
              "embedding": m.embedding, "importance": m.score}
             for m in memories],
            query_embedding
        )

    def _compute_recency_score(self, age: int) -> float:
        """Score based on how recent the memory is (0 = oldest, 1 = newest)."""
        return float(np.exp(-self.config.decay_factor * min(age, self.config.max_age)))

    def _compute_relevance_score(self, mem_emb: np.ndarray, query_emb: np.ndarray) -> float:
        """Score based on semantic similarity between memory and query."""
        norm_a = np.linalg.norm(mem_emb)
        norm_b = np.linalg.norm(query_emb)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(mem_emb, query_emb) / (norm_a * norm_b))

    @staticmethod
    def _compute_importance_score(importance: float) -> float:
        """Score based on intrinsic importance of the memory."""
        return max(0.0, min(1.0, importance))

