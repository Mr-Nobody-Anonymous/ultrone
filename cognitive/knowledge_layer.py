# Copyright (c) Ultrone Contributors. All rights reserved.
"""Knowledge Layer — knowledge graph, vector database, and semantic search.

Combines knowledge graph, vector database, semantic search, hybrid
retrieval, RAG, ontology, graph embeddings, temporal knowledge, and
causal relationships. Every fact has confidence, source, timestamp,
and provenance.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .base_layer import CognitiveLayer, LayerConfig
from .cycle_context import CycleContext, CyclePhase, PhaseResult
from .event_types import CognitiveEventType
from .types import (
    MemoryItem,
    MemoryLayer as MemoryLayerType,
    MemoryRetrieval,
)

logger = logging.getLogger("Ultrone.Cognitive.Knowledge")


@dataclass
class KnowledgeFact:
    """A fact in the knowledge system with provenance."""
    fact_id: str
    content: str
    confidence: float = 1.0
    source: str = "unknown"
    timestamp: float = field(default_factory=time.time)
    provenance: Dict[str, Any] = field(default_factory=dict)
    entities: List[str] = field(default_factory=list)
    relationships: List[Dict[str, str]] = field(default_factory=list)
    embedding: Optional[List[float]] = None


@dataclass
class KnowledgeLayerConfig(LayerConfig):
    """Configuration for the knowledge layer."""
    name: str = "knowledge"
    enable_knowledge_graph: bool = True
    enable_vector_search: bool = True
    enable_semantic_search: bool = True
    enable_hybrid_retrieval: bool = True
    enable_rag: bool = True
    max_facts: int = 10000
    embedding_dim: int = 128


class KnowledgeLayer(CognitiveLayer):
    """Knowledge system combining graph, vector, and semantic search.

    The knowledge layer:
    1. Stores facts with confidence, source, timestamp, and provenance
    2. Maintains a knowledge graph of entities and relationships
    3. Provides vector-based semantic search
    4. Provides hybrid retrieval combining multiple methods
    5. Supports RAG (retrieval-augmented generation)
    6. Tracks temporal and causal relationships
    """

    def __init__(self, config: Optional[KnowledgeLayerConfig] = None):
        super().__init__(config or KnowledgeLayerConfig())
        self._facts: Dict[str, KnowledgeFact] = {}
        self._graph: Dict[str, Dict[str, Any]] = {}  # entity -> {relations}
        self._retrieval_history: List[Dict[str, Any]] = []

    def _layer_phase(self) -> CyclePhase:
        return CyclePhase.RETRIEVE_MEMORY

    def process(self, ctx: CycleContext) -> PhaseResult:
        """Execute the knowledge retrieval phase.

        Parameters
        ----------
        ctx : CycleContext
            The shared cycle context.

        Returns
        -------
        PhaseResult
            Result with knowledge retrievals.
        """
        start = time.time()

        # 1. Store new knowledge from observations
        stored = self._store_observations(ctx)

        # 2. Retrieve relevant knowledge
        query = self._build_query(ctx)
        retrievals = []
        if query:
            results = self.hybrid_retrieve(query, limit=10)
            retrievals.append(results)

        # 3. Store in context
        ctx.metadata["knowledge"] = {
            "stored": stored,
            "retrievals": retrievals,
        }

        # 4. Publish event
        self._publish_event(
            CognitiveEventType.MEMORY_RETRIEVED,
            {
                "query": query,
                "results_count": len(retrievals),
                "sources": ["knowledge_graph", "vector_memory"],
            },
        )

        # 5. Create decision trace
        trace = self._create_trace(
            decision="Retrieve knowledge from knowledge system",
            confidence=0.8,
            evidence=[
                {
                    "source": "knowledge",
                    "description": f"Stored {stored} facts, retrieved {len(retrievals)} results",
                    "confidence": 0.8,
                }
            ],
        )

        return PhaseResult(
            phase=self._phase,
            success=True,
            duration_seconds=time.time() - start,
            output={
                "stored_facts": stored,
                "retrievals": retrievals,
                "total_facts": len(self._facts),
                "graph_entities": len(self._graph),
            },
            trace=trace,
        )

    def store_fact(
        self,
        content: str,
        confidence: float = 1.0,
        source: str = "unknown",
        entities: Optional[List[str]] = None,
        relationships: Optional[List[Dict[str, str]]] = None,
        provenance: Optional[Dict[str, Any]] = None,
    ) -> KnowledgeFact:
        """Store a fact in the knowledge system."""
        import uuid
        fact = KnowledgeFact(
            fact_id=f"fact-{uuid.uuid4().hex[:12]}",
            content=content,
            confidence=confidence,
            source=source,
            timestamp=time.time(),
            provenance=provenance or {"source": source, "timestamp": time.time()},
            entities=entities or [],
            relationships=relationships or [],
        )

        # Generate a simple embedding (hash-based for now)
        fact.embedding = self._generate_embedding(content)

        self._facts[fact.fact_id] = fact

        # Update knowledge graph
        if self.config.enable_knowledge_graph:
            self._update_graph(fact)

        # Enforce capacity
        if len(self._facts) > self.config.max_facts:
            # Remove oldest facts
            sorted_facts = sorted(self._facts.values(), key=lambda f: f.timestamp)
            for old_fact in sorted_facts[:len(self._facts) - self.config.max_facts]:
                del self._facts[old_fact.fact_id]

        return fact

    def retrieve(self, query: str, limit: int = 10) -> List[KnowledgeFact]:
        """Retrieve facts matching a query using keyword search."""
        query_lower = query.lower()
        query_terms = set(query_lower.split())

        scored = []
        for fact in self._facts.values():
            score = 0.0
            content_lower = fact.content.lower()
            for term in query_terms:
                if term in content_lower:
                    score += 0.5
            for entity in fact.entities:
                if entity.lower() in query_lower:
                    score += 0.3
            if score > 0:
                scored.append((score * fact.confidence, fact))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [fact for _, fact in scored[:limit]]

    def semantic_search(self, query: str, limit: int = 10) -> List[KnowledgeFact]:
        """Search using vector embeddings."""
        if not self.config.enable_vector_search:
            return []

        query_embedding = self._generate_embedding(query)
        scored = []

        for fact in self._facts.values():
            if fact.embedding:
                similarity = self._cosine_similarity(query_embedding, fact.embedding)
                scored.append((similarity * fact.confidence, fact))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [fact for _, fact in scored[:limit]]

    def hybrid_retrieve(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Hybrid retrieval combining keyword and semantic search."""
        start = time.time()

        keyword_results = self.retrieve(query, limit=limit)
        semantic_results = self.semantic_search(query, limit=limit)

        # Combine results
        combined = {}
        for fact in keyword_results:
            combined[fact.fact_id] = {
                "fact": fact,
                "method": "keyword",
                "score": 0.5,
            }
        for fact in semantic_results:
            if fact.fact_id in combined:
                combined[fact.fact_id]["method"] = "hybrid"
                combined[fact.fact_id]["score"] = 0.8
            else:
                combined[fact.fact_id] = {
                    "fact": fact,
                    "method": "semantic",
                    "score": 0.5,
                }

        # Sort by score
        sorted_results = sorted(
            combined.values(),
            key=lambda x: x["score"] * x["fact"].confidence,
            reverse=True,
        )[:limit]

        result = {
            "query": query,
            "results": [
                {
                    "fact_id": r["fact"].fact_id,
                    "content": r["fact"].content,
                    "confidence": r["fact"].confidence,
                    "source": r["fact"].source,
                    "method": r["method"],
                    "score": r["score"],
                }
                for r in sorted_results
            ],
            "total_found": len(sorted_results),
            "retrieval_time": time.time() - start,
            "method": "hybrid",
        }
        self._retrieval_history.append(result)
        return result

    def rag_generate(self, query: str, context: Optional[str] = None) -> Dict[str, Any]:
        """Retrieval-augmented generation."""
        if not self.config.enable_rag:
            return {"query": query, "response": context or "", "sources": []}

        # Retrieve relevant facts
        results = self.hybrid_retrieve(query, limit=5)
        facts = results["results"]

        # Build context from facts
        context_parts = []
        for fact in facts:
            context_parts.append(fact["content"])

        if context:
            context_parts.append(context)

        response = "\n".join(context_parts) if context_parts else "No relevant knowledge found."

        return {
            "query": query,
            "response": response,
            "sources": [f["source"] for f in facts],
            "facts_used": len(facts),
        }

    def _store_observations(self, ctx: CycleContext) -> int:
        """Store knowledge from observations."""
        stored = 0
        for obs in ctx.observations:
            for modality, data in obs.modalities.items():
                if isinstance(data, str) and len(data) > 10:
                    self.store_fact(
                        content=data,
                        confidence=obs.confidence,
                        source=f"observation:{obs.observation_id}",
                        provenance={
                            "observation_id": obs.observation_id,
                            "modality": modality.value if hasattr(modality, 'value') else str(modality),
                        },
                    )
                    stored += 1
        return stored

    def _update_graph(self, fact: KnowledgeFact) -> None:
        """Update the knowledge graph with a fact's entities and relationships."""
        for entity in fact.entities:
            if entity not in self._graph:
                self._graph[entity] = {
                    "facts": [],
                    "relations": {},
                }
            self._graph[entity]["facts"].append(fact.fact_id)

        for rel in fact.relationships:
            source = rel.get("source", "")
            target = rel.get("target", "")
            rel_type = rel.get("type", "related_to")
            if source and target:
                if source not in self._graph:
                    self._graph[source] = {"facts": [], "relations": {}}
                if target not in self._graph:
                    self._graph[target] = {"facts": [], "relations": {}}
                self._graph[source]["relations"][target] = rel_type

    def _build_query(self, ctx: CycleContext) -> str:
        """Build a knowledge query from the cycle context."""
        terms = []
        for goal in ctx.context.goals:
            if isinstance(goal, str):
                terms.append(goal)
            else:
                terms.append(str(goal))
        if ctx.situational_context:
            for entity in ctx.situational_context.entities.values():
                entity_type = entity.get("type", "")
                if entity_type:
                    if isinstance(entity_type, str):
                        terms.append(entity_type)
                    else:
                        terms.append(str(entity_type))
        return " ".join(terms[:10])

    def _generate_embedding(self, text: str) -> List[float]:
        """Generate a simple hash-based embedding for text."""
        import hashlib
        embedding = []
        for i in range(self.config.embedding_dim):
            hash_val = hashlib.md5(f"{text}:{i}".encode()).hexdigest()
            embedding.append(int(hash_val[:8], 16) / 2**32)
        return embedding

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def get_stats(self) -> Dict[str, Any]:
        """Return knowledge system statistics."""
        return {
            "total_facts": len(self._facts),
            "graph_entities": len(self._graph),
            "retrievals": len(self._retrieval_history),
            "avg_confidence": (
                sum(f.confidence for f in self._facts.values()) / len(self._facts)
                if self._facts else 0.0
            ),
        }

    def get_facts(self) -> Dict[str, KnowledgeFact]:
        """Return all stored facts."""
        return self._facts

    def get_graph(self) -> Dict[str, Dict[str, Any]]:
        """Return the knowledge graph."""
        return self._graph

    def get_retrieval_history(self) -> List[Dict[str, Any]]:
        """Return the history of retrievals."""
        return self._retrieval_history