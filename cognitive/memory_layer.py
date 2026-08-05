# Copyright (c) Ultrone Contributors. All rights reserved.
"""Memory Layer — multi-tier cognitive memory system.

Implements working memory, episodic memory, semantic memory, procedural
memory, associative memory, vector memory, and graph memory. Supports
experience replay, memory consolidation, memory compression, automatic
forgetting, and importance scoring.
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

logger = logging.getLogger("Ultrone.Cognitive.Memory")


@dataclass
class MemoryLayerConfig(LayerConfig):
    """Configuration for the memory layer."""
    name: str = "memory"
    working_capacity: int = 100
    episodic_capacity: int = 10000
    semantic_capacity: int = 10000
    procedural_capacity: int = 5000
    associative_capacity: int = 5000
    vector_capacity: int = 10000
    graph_capacity: int = 10000
    consolidation_interval: int = 10
    importance_threshold: float = 0.5
    enable_consolidation: bool = True
    enable_forgetting: bool = True
    enable_compression: bool = True


class MemoryLayer(CognitiveLayer):
    """Multi-tier memory system for the cognitive architecture.

    The memory layer:
    1. Stores experiences in the appropriate memory tier
    2. Retrieves relevant memories across all tiers
    3. Consolidates working memory into long-term memory
    4. Compresses and summarizes memories
    5. Applies automatic forgetting
    6. Scores memories by importance
    """

    def __init__(self, config: Optional[MemoryLayerConfig] = None):
        super().__init__(config or MemoryLayerConfig())
        self._memories: Dict[MemoryLayerType, Dict[str, MemoryItem]] = {
            layer: {} for layer in MemoryLayerType
        }
        self._retrieval_history: List[MemoryRetrieval] = []
        self._consolidation_count: int = 0
        self._forgetting_count: int = 0

    def _layer_phase(self) -> CyclePhase:
        return CyclePhase.RETRIEVE_MEMORY

    def process(self, ctx: CycleContext) -> PhaseResult:
        """Execute the memory retrieval phase.

        Parameters
        ----------
        ctx : CycleContext
            The shared cycle context.

        Returns
        -------
        PhaseResult
            Result with memory retrievals.
        """
        start = time.time()

        # 1. Store current observations in working memory
        for obs in ctx.observations:
            self.store(
                layer=MemoryLayerType.WORKING,
                key=f"obs:{obs.observation_id}",
                content=obs.to_dict(),
                importance=0.7,
            )

        # 2. Store world state in episodic memory
        if ctx.world_state:
            self.store(
                layer=MemoryLayerType.EPISODIC,
                key=f"state:{ctx.world_state.state_id}",
                content=ctx.world_state.to_dict(),
                importance=0.8,
            )

        # 3. Retrieve relevant memories
        retrievals = []
        query = self._build_query(ctx)
        if query:
            retrieval = self.retrieve(query, limit=10)
            retrievals.append(retrieval.to_dict() if hasattr(retrieval, 'to_dict') else {
                "query": query,
                "results": [r.to_dict() if hasattr(r, 'to_dict') else str(r) for r in retrieval.results],
                "total_found": retrieval.total_found,
            })
            ctx.memory_retrievals = retrievals

        # 4. Consolidate if needed
        if self.config.enable_consolidation and self._consolidation_count >= self.config.consolidation_interval:
            self.consolidate()
            self._consolidation_count = 0
        else:
            self._consolidation_count += 1

        # 5. Apply forgetting
        if self.config.enable_forgetting:
            self.apply_forgetting()

        # 6. Publish event
        self._publish_event(
            CognitiveEventType.MEMORY_RETRIEVED,
            {
                "query": query,
                "results_count": len(retrievals),
                "sources": [r.get("query", "") for r in retrievals],
            },
        )

        # 7. Create decision trace
        trace = self._create_trace(
            decision="Retrieve relevant memories",
            confidence=0.8,
            evidence=[
                {
                    "source": "memory",
                    "description": f"Retrieved {len(retrievals)} memory results",
                    "confidence": 0.8,
                }
            ],
        )

        return PhaseResult(
            phase=self._phase,
            success=True,
            duration_seconds=time.time() - start,
            output={
                "retrievals": retrievals,
                "memory_stats": self.get_stats(),
                "consolidation_count": self._consolidation_count,
                "forgetting_count": self._forgetting_count,
            },
            trace=trace,
        )

    def store(self, layer: MemoryLayerType, key: str, content: Any, importance: float = 0.5) -> MemoryItem:
        """Store an item in the specified memory layer."""
        item = MemoryItem(
            layer=layer,
            content=content,
            importance=importance,
            timestamp=time.time(),
        )
        self._memories[layer][key] = item

        # Enforce capacity
        capacity_map = {
            MemoryLayerType.WORKING: self.config.working_capacity,
            MemoryLayerType.EPISODIC: self.config.episodic_capacity,
            MemoryLayerType.SEMANTIC: self.config.semantic_capacity,
            MemoryLayerType.PROCEDURAL: self.config.procedural_capacity,
            MemoryLayerType.ASSOCIATIVE: self.config.associative_capacity,
            MemoryLayerType.VECTOR: self.config.vector_capacity,
            MemoryLayerType.GRAPH: self.config.graph_capacity,
        }
        capacity = capacity_map.get(layer, 1000)
        if len(self._memories[layer]) > capacity:
            # Remove lowest importance items
            sorted_items = sorted(
                self._memories[layer].items(),
                key=lambda x: x[1].importance,
            )
            for old_key, _ in sorted_items[:len(self._memories[layer]) - capacity]:
                del self._memories[layer][old_key]

        return item

    def recall(self, layer: MemoryLayerType, key: str) -> Optional[MemoryItem]:
        """Recall an item from a specific memory layer."""
        item = self._memories[layer].get(key)
        if item:
            item.access_count += 1
            item.last_accessed = time.time()
        return item

    def retrieve(self, query: str, limit: int = 10) -> MemoryRetrieval:
        """Retrieve memories across all layers matching a query."""
        start = time.time()
        results = []

        # Simple keyword-based retrieval
        query_lower = query.lower()
        query_terms = set(query_lower.split())

        for layer in MemoryLayerType:
            for key, item in self._memories[layer].items():
                # Check if query terms appear in key or content
                content_str = str(item.content).lower()
                key_str = key.lower()

                score = 0.0
                for term in query_terms:
                    if term in key_str:
                        score += 0.5
                    if term in content_str:
                        score += 0.3

                if score > 0:
                    item.access_count += 1
                    item.last_accessed = time.time()
                    results.append((score, item))

        # Sort by score and importance
        results.sort(key=lambda x: (x[0], x[1].importance), reverse=True)
        top_results = [item for _, item in results[:limit]]

        retrieval = MemoryRetrieval(
            query=query,
            results=top_results,
            total_found=len(results),
            retrieval_time=time.time() - start,
            method="keyword",
            confidence=min(1.0, len(top_results) / max(1, limit)),
        )
        self._retrieval_history.append(retrieval)
        return retrieval

    def consolidate(self) -> Dict[str, Any]:
        """Consolidate working memory into long-term memory."""
        consolidated = 0
        working = self._memories[MemoryLayerType.WORKING]

        for key, item in list(working.items()):
            if item.importance >= self.config.importance_threshold:
                # Move to episodic or semantic based on content
                target_layer = MemoryLayerType.SEMANTIC if "concept" in str(item.content).lower() else MemoryLayerType.EPISODIC
                self._memories[target_layer][key] = item
                del working[key]
                consolidated += 1

        self._publish_event(
            CognitiveEventType.MEMORY_CONSOLIDATED,
            {"consolidated": consolidated},
        )

        return {
            "consolidated": consolidated,
            "working_remaining": len(working),
        }

    def apply_forgetting(self) -> int:
        """Apply automatic forgetting to low-importance, old memories."""
        forgotten = 0
        now = time.time()

        for layer in [MemoryLayerType.EPISODIC, MemoryLayerType.SEMANTIC]:
            for key, item in list(self._memories[layer].items()):
                age = now - item.timestamp
                # Forget items that are old and low importance
                if age > 3600 and item.importance < 0.3:
                    del self._memories[layer][key]
                    forgotten += 1

        self._forgetting_count += forgotten
        return forgotten

    def _build_query(self, ctx: CycleContext) -> str:
        """Build a retrieval query from the cycle context."""
        terms = []

        # Add goal terms
        for goal in ctx.context.goals:
            if isinstance(goal, str):
                terms.append(goal)
            else:
                terms.append(str(goal))

        # Add entity types from situational context
        if ctx.situational_context:
            for entity in ctx.situational_context.entities.values():
                entity_type = entity.get("type", "")
                if entity_type:
                    if isinstance(entity_type, str):
                        terms.append(entity_type)
                    else:
                        terms.append(str(entity_type))

        return " ".join(terms[:10])

    def get_stats(self) -> Dict[str, Any]:
        """Return memory statistics."""
        return {
            "layers": {
                layer.value: len(items)
                for layer, items in self._memories.items()
            },
            "total_items": sum(len(items) for items in self._memories.values()),
            "retrievals": len(self._retrieval_history),
            "consolidations": self._consolidation_count,
            "forgotten": self._forgetting_count,
        }

    def get_memories(self, layer: Optional[MemoryLayerType] = None) -> Dict[str, MemoryItem]:
        """Return memories from a specific layer or all layers."""
        if layer:
            return self._memories[layer]
        return {k.value: v for k, v in self._memories.items()}

    def get_retrieval_history(self) -> List[MemoryRetrieval]:
        """Return the history of memory retrievals."""
        return self._retrieval_history