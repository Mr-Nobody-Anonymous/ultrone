# Copyright (c) Ultrone Contributors. All rights reserved.
"""Knowledge Graph Embeddings (TransE, RotatE, etc.)."""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger("Ultrone.Brain.Perception.GraphIntelligence.KGE")


@dataclass
class KGEConfig:
    """Configuration for knowledge graph embeddings."""
    embedding_dim: int = 128
    margin: float = 1.0
    learning_rate: float = 0.01


class KnowledgeEmbeddings:
    """Knowledge graph embedding models for link prediction."""

    def __init__(self, config: Optional[KGEConfig] = None):
        self.config = config or KGEConfig()
        self._entity_embeddings: Dict[str, np.ndarray] = {}
        self._relation_embeddings: Dict[str, np.ndarray] = {}

    def add_entity(self, name: str) -> None:
        self._entity_embeddings[name] = np.random.randn(self.config.embedding_dim)

    def add_relation(self, name: str) -> None:
        self._relation_embeddings[name] = np.random.randn(self.config.embedding_dim)

    def embed(self, entities: List[str]) -> np.ndarray:
        """Return embeddings for a list of entities.
        
        Args:
            entities: List of entity names to embed.
            
        Returns:
            Array of shape (len(entities), embedding_dim) with entity embeddings.
        """
        embeddings = []
        for entity in entities:
            if entity in self._entity_embeddings:
                embeddings.append(self._entity_embeddings[entity])
            else:
                embeddings.append(np.zeros(self.config.embedding_dim))
        return np.array(embeddings)

    def predict_triple(self, head: str, relation: str, tail: str) -> float:
        """Score a triple (head, relation, tail)."""
        h = self._entity_embeddings.get(head, np.zeros(self.config.embedding_dim))
        r = self._relation_embeddings.get(relation, np.zeros(self.config.embedding_dim))
        t = self._entity_embeddings.get(tail, np.zeros(self.config.embedding_dim))
        return -np.linalg.norm(h + r - t)

    def get_stats(self) -> Dict[str, Any]:
        return {"type": "KnowledgeEmbeddings", "num_entities": len(self._entity_embeddings)}
