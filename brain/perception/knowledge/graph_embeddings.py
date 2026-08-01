"""Knowledge graph entity embedding generation and management."""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("Ultrone.Brain.Perception.Knowledge.GraphEmbeddings")


@dataclass
class GraphEmbedConfig:
    """Configuration for graph embedding models."""
    embedding_dim: int = 128
    num_negatives: int = 5
    learning_rate: float = 1e-3
    num_epochs: int = 100
    margin: float = 1.0
    model_type: str = "transe"  # transe, transr, distmult, complex


@dataclass
class EntityEmbedding:
    """Embedding for a knowledge graph entity."""
    entity_id: str
    entity_type: str
    embedding: np.ndarray
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RelationEmbedding:
    """Embedding for a knowledge graph relation."""
    relation_id: str
    embedding: np.ndarray
    metadata: Dict[str, Any] = field(default_factory=dict)


class GraphEmbeddings:
    """Manages embeddings for knowledge graph entities and relations."""

    def __init__(self, config: Optional[GraphEmbedConfig] = None):
        self.config = config or GraphEmbedConfig()
        self._entity_embeddings: Dict[str, EntityEmbedding] = {}
        self._relation_embeddings: Dict[str, RelationEmbedding] = {}

    def embed_entity(self, entity_id: str, entity_type: str,
                     features: Optional[np.ndarray] = None,
                     metadata: Optional[Dict[str, Any]] = None) -> EntityEmbedding:
        """Create or update an entity embedding."""
        if features is not None:
            emb = self._normalize(features[:self.config.embedding_dim])
        else:
            emb = self._normalize(np.random.randn(self.config.embedding_dim))

        entity_emb = EntityEmbedding(
            entity_id=entity_id,
            entity_type=entity_type,
            embedding=emb,
            metadata=metadata or {},
        )
        self._entity_embeddings[entity_id] = entity_emb
        return entity_emb

    def embed_relation(self, relation_id: str,
                       features: Optional[np.ndarray] = None,
                       metadata: Optional[Dict[str, Any]] = None) -> RelationEmbedding:
        """Create or update a relation embedding."""
        if features is not None:
            emb = self._normalize(features[:self.config.embedding_dim])
        else:
            emb = self._normalize(np.random.randn(self.config.embedding_dim))

        rel_emb = RelationEmbedding(
            relation_id=relation_id,
            embedding=emb,
            metadata=metadata or {},
        )
        self._relation_embeddings[relation_id] = rel_emb
        return rel_emb

    def get_entity_embedding(self, entity_id: str) -> Optional[EntityEmbedding]:
        """Retrieve embedding for an entity."""
        return self._entity_embeddings.get(entity_id)

    def get_relation_embedding(self, relation_id: str) -> Optional[RelationEmbedding]:
        """Retrieve embedding for a relation."""
        return self._relation_embeddings.get(relation_id)

    def compute_triple_score(self, head_id: str, relation_id: str, tail_id: str) -> float:
        """Score a (head, relation, tail) triple using TransE model."""
        head = self._entity_embeddings.get(head_id)
        rel = self._relation_embeddings.get(relation_id)
        tail = self._entity_embeddings.get(tail_id)

        if head is None or rel is None or tail is None:
            return 0.0

        if self.config.model_type == "transe":
            score = -np.linalg.norm(head.embedding + rel.embedding - tail.embedding)
        elif self.config.model_type == "distmult":
            score = float(np.dot(head.embedding * rel.embedding, tail.embedding))
        else:
            score = -np.linalg.norm(head.embedding + rel.embedding - tail.embedding)

        return float(score)

    def find_similar_entities(self, entity_id: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """Find entities with similar embeddings."""
        query = self._entity_embeddings.get(entity_id)
        if query is None:
            return []

        similarities = []
        for eid, emb in self._entity_embeddings.items():
            if eid != entity_id:
                sim = float(np.dot(query.embedding, emb.embedding) /
                            (np.linalg.norm(query.embedding) * np.linalg.norm(emb.embedding)))
                similarities.append((eid, sim))

        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]

    @property
    def num_entities(self) -> int:
        return len(self._entity_embeddings)

    @property
    def num_relations(self) -> int:
        return len(self._relation_embeddings)

    @staticmethod
    def _normalize(v: np.ndarray) -> np.ndarray:
        norm = np.linalg.norm(v)
        return v / norm if norm > 0 else v

