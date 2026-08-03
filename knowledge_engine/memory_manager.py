# Copyright (c) Ultrone Contributors. All rights reserved.
"""Knowledge memory manager for the ULTRONE autonomous research platform.

Orchestrates all knowledge memory layers: semantic, episodic, working,
procedural, research, algorithm, project, experiment, long-term, plus
knowledge graph, vector memory, ontology, entity linking, citation DB,
RAG, cross-reference, and consolidation.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from .base import KnowledgeEntry, KnowledgeSource, KnowledgeCategory
from .semantic_memory import SemanticKnowledgeMemory
from .episodic_memory import EpisodicKnowledgeMemory
from .working_memory import WorkingKnowledgeMemory
from .procedural_memory import ProceduralMemory
from .research_memory import ResearchMemory
from .algorithm_memory import AlgorithmMemory
from .project_memory import ProjectMemory
from .experiment_memory import ExperimentMemory
from .long_term_memory import LongTermMemory
from .knowledge_graph import KnowledgeGraph, NodeType, EdgeType
from .vector_memory import VectorMemory
from .ontology import OntologyEngine
from .entity_linking import EntityLinker
from .citation_db import CitationDatabase, Citation
from .rag import RAGPipeline
from .cross_reference import CrossReferenceEngine
from .consolidation import KnowledgeConsolidation

logger = logging.getLogger("Ultrone.KnowledgeEngine.MemoryManager")


class KnowledgeMemoryManager:
    """Central orchestrator for all knowledge engine layers.

    Features
    --------
    - Unified store/recall across all memory layers
    - Knowledge graph integration
    - Vector indexing
    - Ontology + entity linking
    - Citation registration
    - RAG retrieval
    - Cross-reference discovery
    - Consolidation / deduplication
    - Statistics across layers
    """

    def __init__(
        self,
        embedding_dim: int = 256,
        enable_graph: bool = True,
        enable_vector: bool = True,
        enable_ontology: bool = True,
        enable_entity_linking: bool = True,
        enable_rag: bool = True,
        enable_cross_reference: bool = True,
        enable_consolidation: bool = True,
    ):
        # Memory layers
        self.semantic = SemanticKnowledgeMemory()
        self.episodic = EpisodicKnowledgeMemory()
        self.working = WorkingKnowledgeMemory()
        self.procedural = ProceduralMemory()
        self.research = ResearchMemory()
        self.algorithm = AlgorithmMemory()
        self.project = ProjectMemory()
        self.experiment = ExperimentMemory()
        self.long_term = LongTermMemory()
        self._layers: Dict[str, Any] = {
            "semantic": self.semantic,
            "episodic": self.episodic,
            "working": self.working,
            "procedural": self.procedural,
            "research": self.research,
            "algorithm": self.algorithm,
            "project": self.project,
            "experiment": self.experiment,
            "long_term": self.long_term,
        }

        # Advanced engines
        self.enable_graph = enable_graph
        self.enable_vector = enable_vector
        self.enable_ontology = enable_ontology
        self.enable_entity_linking = enable_entity_linking
        self.enable_rag = enable_rag
        self.enable_cross_reference = enable_cross_reference
        self.enable_consolidation = enable_consolidation

        self.knowledge_graph = KnowledgeGraph()
        self.vector_memory = VectorMemory(embedding_dim=embedding_dim)
        self.ontology = OntologyEngine()
        self.entity_linker = EntityLinker(ontology=self.ontology)
        self.citation_db = CitationDatabase()
        self.rag = RAGPipeline(
            vector_memory=self.vector_memory if enable_vector else None,
            knowledge_graph=self.knowledge_graph if enable_graph else None,
            citation_db=self.citation_db,
        )
        self.cross_reference = CrossReferenceEngine(
            vector_memory=self.vector_memory,
            knowledge_graph=self.knowledge_graph,
        )
        self.consolidation = KnowledgeConsolidation(cross_reference=self.cross_reference)

        # Track all entries globally
        self._all_entries: Dict[str, KnowledgeEntry] = {}
        self._entry_layer: Dict[str, str] = {}

    # ------------------------------------------------------------------
    # Unified store
    # ------------------------------------------------------------------
    def store(
        self,
        entry: KnowledgeEntry,
        layer: str = "semantic",
    ) -> KnowledgeEntry:
        """Store an entry in the specified layer and propagate to engines."""
        layer_obj = self._layers.get(layer)
        if layer_obj is None:
            raise ValueError(f"Unknown knowledge layer: {layer}")

        stored = layer_obj.store(entry)

        # Track globally
        self._all_entries[stored.entry_id] = stored
        self._entry_layer[stored.entry_id] = layer

        # Vector indexing
        if self.enable_vector:
            self.vector_memory.index(stored)

        # Knowledge graph node
        if self.enable_graph:
            self._index_in_graph(stored)

        # Entity linking registration
        if self.enable_entity_linking:
            self.entity_linker.register_entity(stored.entry_id, stored.content[:50], aliases=stored.tags[:5])

        # RAG registration
        if self.enable_rag:
            self.rag.register_entry(stored)

        return stored

    def _index_in_graph(self, entry: KnowledgeEntry) -> None:
        """Add or update a knowledge graph node for the entry."""
        node_type = self._category_to_node_type(entry.category)
        self.knowledge_graph.add_node(
            label=entry.content[:80],
            node_type=node_type,
            properties={
                "entry_id": entry.entry_id,
                "category": entry.category.value,
                "tags": entry.tags,
                "entities": entry.entities,
            },
            source=entry.source.value,
            confidence_score=entry.confidence_score,
            node_id=entry.entry_id,
        )
        # Link related entries
        for rel_id in entry.related_entry_ids:
            if rel_id in self._all_entries:
                self.knowledge_graph.add_edge(
                    entry.entry_id,
                    rel_id,
                    edge_type=EdgeType.RELATES_TO,
                    confidence_score=entry.confidence_score,
                )

    @staticmethod
    def _category_to_node_type(category: KnowledgeCategory) -> NodeType:
        mapping = {
            KnowledgeCategory.ALGORITHM: NodeType.ALGORITHM,
            KnowledgeCategory.ARCHITECTURE: NodeType.ARCHITECTURE,
            KnowledgeCategory.DATASET: NodeType.DATASET,
            KnowledgeCategory.METRIC: NodeType.METRIC,
            KnowledgeCategory.METHOD: NodeType.METHOD,
            KnowledgeCategory.RESULT: NodeType.BENCHMARK,
            KnowledgeCategory.HYPERPARAMETER: NodeType.ALGORITHM,
        }
        return mapping.get(category, NodeType.CONCEPT)

    def store_auto_categorized(
        self,
        content: str,
        source: KnowledgeSource = KnowledgeSource.OTHER,
        tags: Optional[List[str]] = None,
        entities: Optional[List[str]] = None,
        confidence_score: float = 0.5,
        layer: str = "semantic",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> KnowledgeEntry:
        """Create and store an entry with auto-categorization."""
        category = self._auto_categorize(content)
        entry = KnowledgeEntry(
            content=content,
            category=category,
            source=source,
            confidence_score=confidence_score,
            tags=tags or [],
            entities=entities or [],
            metadata=metadata or {},
        )
        return self.store(entry, layer=layer)

    @staticmethod
    def _auto_categorize(content: str) -> KnowledgeCategory:
        lower = content.lower()
        if any(w in lower for w in ("algorithm", "method", "technique", "procedure")):
            return KnowledgeCategory.ALGORITHM
        if any(w in lower for w in ("architecture", "network", "model", "transformer")):
            return KnowledgeCategory.ARCHITECTURE
        if any(w in lower for w in ("dataset", "corpus", "benchmark set")):
            return KnowledgeCategory.DATASET
        if any(w in lower for w in ("metric", "accuracy", "f1", "precision", "recall")):
            return KnowledgeCategory.METRIC
        if any(w in lower for w in ("hyperparameter", "learning rate", "batch size")):
            return KnowledgeCategory.HYPERPARAMETER
        if any(w in lower for w in ("limitation", "drawback", "fails", "weakness")):
            return KnowledgeCategory.LIMITATION
        if any(w in lower for w in ("result", "improvement", "outperform", "novel")):
            return KnowledgeCategory.RESULT
        return KnowledgeCategory.THEORY

    # ------------------------------------------------------------------
    # Unified recall
    # ------------------------------------------------------------------
    def recall(self, query: str, limit: int = 10, layer: Optional[str] = None) -> List[KnowledgeEntry]:
        """Recall entries from layers (optionally filtered)."""
        if layer:
            layer_obj = self._layers.get(layer)
            if layer_obj:
                return layer_obj.search(query, limit=limit)
            return []
        results = []
        for layer_obj in self._layers.values():
            results.extend(layer_obj.search(query, limit=limit))
        results.sort(key=lambda e: e.confidence_score, reverse=True)
        return results[:limit]

    def semantic_search(self, query: str, limit: int = 10) -> List[Tuple[KnowledgeEntry, float]]:
        """Vector-based semantic search across all indexed entries."""
        if not self.enable_vector:
            return []
        return self.vector_memory.search_with_entries(query, self._all_entries, limit=limit)

    def graph_search(self, query: str, limit: int = 10) -> List[KnowledgeEntry]:
        """Search via knowledge graph traversal."""
        if not self.enable_graph:
            return []
        # Find nodes matching query
        matching_nodes = []
        for node in self.knowledge_graph._nodes.values():
            if query.lower() in node.label.lower() or query.lower() in " ".join(node.properties.get("tags", [])):
                matching_nodes.append(node)
        # Get related entries
        result = []
        for node in matching_nodes[:limit]:
            entry = self._all_entries.get(node.node_id)
            if entry:
                result.append(entry)
            # Add related via graph
            for rel in self.knowledge_graph.find_related(node.node_id):
                entry = self._all_entries.get(rel.node_id)
                if entry and entry not in result:
                    result.append(entry)
        return result[:limit]

    def rag_retrieve(self, query: str, limit: int = 5) -> List[Tuple[KnowledgeEntry, float]]:
        """RAG-based hybrid retrieval."""
        if not self.enable_rag:
            return []
        return self.rag.retrieve(query, limit=limit)

    # ------------------------------------------------------------------
    # Graph / ontology helpers
    # ------------------------------------------------------------------
    def add_graph_node(
        self,
        label: str,
        node_type: NodeType = NodeType.CONCEPT,
        properties: Optional[Dict[str, Any]] = None,
        confidence_score: float = 0.5,
    ) -> str:
        """Add a standalone graph node. Returns node_id."""
        node = self.knowledge_graph.add_node(
            label=label,
            node_type=node_type,
            properties=properties or {},
            confidence_score=confidence_score,
        )
        return node.node_id

    def add_graph_edge(
        self,
        source_id: str,
        target_id: str,
        edge_type: EdgeType = EdgeType.RELATES_TO,
        confidence_score: float = 0.5,
    ) -> bool:
        """Add a graph edge. Returns True on success."""
        return (
            self.knowledge_graph.add_edge(source_id, target_id, edge_type=edge_type, confidence_score=confidence_score)
            is not None
        )

    def add_ontology_concept(
        self,
        name: str,
        description: str = "",
        parent_id: Optional[str] = None,
        aliases: Optional[List[str]] = None,
    ) -> str:
        """Add an ontology concept. Returns concept_id."""
        concept = self.ontology.add_concept(
            name=name,
            description=description,
            parent_id=parent_id,
            aliases=aliases,
        )
        return concept.concept_id

    def register_citation(self, citation: Citation) -> str:
        """Register a citation. Returns citation_id."""
        return self.citation_db.add_citation(citation).citation_id

    # ------------------------------------------------------------------
    # Consolidation
    # ------------------------------------------------------------------
    def consolidate_all(self) -> Dict[str, Any]:
        """Run consolidation across all layers. Returns report."""
        all_entries = list(self._all_entries.values())
        if not all_entries or not self.enable_consolidation:
            return {"skipped": True}

        kept, report = self.consolidation.consolidate(all_entries)

        # Rebuild tracking with consolidated entries
        new_entries = {e.entry_id: e for e in kept}
        self._all_entries = new_entries
        return report

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        return {
            "layers": {name: layer.get_stats() for name, layer in self._layers.items()},
            "knowledge_graph": self.knowledge_graph.get_stats(),
            "vector_memory": self.vector_memory.get_stats(),
            "ontology": self.ontology.get_stats(),
            "entity_linker": self.entity_linker.get_stats(),
            "citation_db": self.citation_db.get_stats(),
            "rag": self.rag.get_stats(),
            "cross_reference": self.cross_reference.get_stats(),
            "consolidation": self.consolidation.get_stats(),
            "total_entries": len(self._all_entries),
        }

    def get_stats(self) -> Dict[str, Any]:
        return self.to_dict()

    def get_layer_stats(self, layer: str) -> Dict[str, Any]:
        layer_obj = self._layers.get(layer)
        if layer_obj:
            return layer_obj.get_stats()
        return {"error": f"Unknown layer: {layer}"}

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------
    def export_json(self) -> Dict[str, Any]:
        """Export all data as JSON-serializable dict."""
        return {
            "graph": self.knowledge_graph.to_dict(),
            "vector_memory": self.vector_memory.to_dict(),
            "ontology": self.ontology.to_dict(),
            "citations": self.citation_db.to_dict(),
        }

    def import_json(self, data: Dict[str, Any]) -> None:
        """Import data from dict."""
        if "graph" in data:
            self.knowledge_graph = KnowledgeGraph.from_dict(data["graph"])
        if "vector_memory" in data:
            self.vector_memory = VectorMemory.from_dict(data["vector_memory"])
        if "ontology" in data:
            self.ontology = OntologyEngine.from_dict(data["ontology"])
        if "citations" in data:
            self.citation_db = CitationDatabase.from_dict(data["citations"])
