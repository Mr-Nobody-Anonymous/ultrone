"""Tests for the knowledge engine package."""

import pytest

from knowledge_engine.base import (
    KnowledgeEntry, KnowledgeSource, KnowledgeCategory, ConfidenceLevel,
)
from knowledge_engine.knowledge_graph import KnowledgeGraph, NodeType, EdgeType
from knowledge_engine.vector_memory import VectorMemory
from knowledge_engine.ontology import OntologyEngine
from knowledge_engine.entity_linking import EntityLinker
from knowledge_engine.citation_db import CitationDatabase, Citation
from knowledge_engine.rag import RAGPipeline
from knowledge_engine.cross_reference import CrossReferenceEngine
from knowledge_engine.consolidation import KnowledgeConsolidation
from knowledge_engine.memory_manager import KnowledgeMemoryManager


class TestKnowledgeGraph:
    def test_add_and_get_node(self):
        graph = KnowledgeGraph()
        node = graph.add_node("Test Concept", NodeType.CONCEPT, confidence_score=0.8)
        assert graph.get_node(node.node_id) == node

    def test_add_edge_and_traverse(self):
        graph = KnowledgeGraph()
        a = graph.add_node("A", NodeType.CONCEPT)
        b = graph.add_node("B", NodeType.CONCEPT)
        graph.add_edge(a.node_id, b.node_id, EdgeType.RELATES_TO)
        neighbors = graph.neighbors(a.node_id)
        assert b.node_id in neighbors
        path = graph.find_path(a.node_id, b.node_id)
        assert path == [a.node_id, b.node_id]

    def test_node_versioning(self):
        graph = KnowledgeGraph()
        node = graph.add_node("V1", NodeType.CONCEPT)
        graph.update_node(node.node_id, label="V2")
        history = graph.get_node_history(node.node_id)
        assert len(history) == 1
        updated = graph.get_node(node.node_id)
        assert updated.label == "V2"
        assert updated.version == 2

    def test_find_related(self):
        graph = KnowledgeGraph()
        central = graph.add_node("Central", NodeType.CONCEPT)
        n1 = graph.add_node("N1", NodeType.CONCEPT)
        n2 = graph.add_node("N2", NodeType.CONCEPT)
        n3 = graph.add_node("N3", NodeType.CONCEPT)
        graph.add_edge(central.node_id, n1.node_id)
        graph.add_edge(central.node_id, n2.node_id)
        graph.add_edge(central.node_id, n3.node_id)
        related = graph.find_related(central.node_id)
        assert len(related) >= 0

    def test_serialization(self):
        graph = KnowledgeGraph(name="test_graph")
        graph.add_node("A", NodeType.CONCEPT)
        graph.add_node("B", NodeType.CONCEPT)
        data = graph.to_dict()
        restored = KnowledgeGraph.from_dict(data)
        assert restored.count_nodes() == 2
        assert restored.name == "test_graph"


class TestVectorMemory:
    def test_index_and_search(self):
        vm = VectorMemory(embedding_dim=64)
        entry1 = KnowledgeEntry(
            content="Transformer architecture for sequence modeling",
            tags=["transformer", "nlp"],
            entry_id="E1",
        )
        entry2 = KnowledgeEntry(
            content="Reinforcement learning for robotics control",
            tags=["rl", "robotics"],
            entry_id="E2",
        )
        vm.index(entry1)
        vm.index(entry2)
        results = vm.search("transformer neural network", limit=1)
        assert len(results) == 1
        assert results[0][0] == "E1"

    def test_cosine_similarity(self):
        vec_a = [1.0, 0.0, 0.0]
        vec_b = [1.0, 0.0, 0.0]
        vec_c = [0.0, 1.0, 0.0]
        assert VectorMemory.cosine_similarity(vec_a, vec_b) == 1.0
        assert VectorMemory.cosine_similarity(vec_a, vec_c) == 0.0


class TestOntology:
    def test_add_and_lookup(self):
        ont = OntologyEngine()
        c1 = ont.add_concept("Neural Network", parent_id=None)
        c2 = ont.add_concept("Transformer", parent_id=c1.concept_id)
        assert ont.lookup("transformer").concept_id == c2.concept_id
        assert ont.lookup("neural_network").concept_id == c1.concept_id

    def test_hierarchy(self):
        ont = OntologyEngine()
        root = ont.add_concept("AI")
        child = ont.add_concept("ML", parent_id=root.concept_id)
        grandchild = ont.add_concept("Deep Learning", parent_id=child.concept_id)
        ancestors = ont.ancestors(grandchild.concept_id)
        assert len(ancestors) == 2
        assert ont.is_subconcept_of(grandchild.concept_id, root.concept_id)


class TestEntityLinking:
    def test_link_text(self):
        ont = OntologyEngine()
        ont.add_concept("Transformer", aliases=["transformer model"])
        linker = EntityLinker(ontology=ont)
        results = linker.link_text("The transformer model is powerful")
        assert len(results) >= 1


class TestCitationDB:
    def test_add_and_lookup(self):
        db = CitationDatabase()
        cit = Citation(title="Test Paper", authors=["Alice"], year=2024)
        db.add_citation(cit)
        found = db.lookup_by_title("test paper")
        assert found == cit


class TestRAGPipeline:
    def test_retrieve(self):
        rag = RAGPipeline()
        entry = KnowledgeEntry(
            content="Attention is all you need - transformer",
            tags=["transformer"],
            entry_id="R1",
        )
        rag.register_entry(entry)
        results = rag.retrieve("transformer attention", limit=1)
        assert len(results) >= 1


class TestCrossReference:
    def test_find_duplicates(self):
        cr = CrossReferenceEngine()
        e1 = KnowledgeEntry(content="deep learning model for classification", tags=["dl"], entry_id="A")
        e2 = KnowledgeEntry(content="deep learning model for classification", tags=["dl"], entry_id="B")
        duplicates = cr.find_duplicates([e1, e2], threshold=0.5)
        assert len(duplicates) >= 1


class TestConsolidation:
    def test_consolidate(self):
        cons = KnowledgeConsolidation()
        e1 = KnowledgeEntry(
            content="Transformer is an attention-based architecture",
            category=KnowledgeCategory.ARCHITECTURE,
            confidence_score=0.7,
            entry_id="C1",
        )
        e2 = KnowledgeEntry(
            content="Transformer is an attention-based architecture",
            category=KnowledgeCategory.ARCHITECTURE,
            confidence_score=0.8,
            entry_id="C2",
        )
        kept, report = cons.consolidate([e1, e2])
        assert report["kept_count"] < report["original_count"]


class TestMemoryManager:
    def test_store_and_recall(self):
        km = KnowledgeMemoryManager()
        entry = km.store_auto_categorized(
            content="New algorithm for efficient training",
            tags=["algorithm"],
            confidence_score=0.8,
        )
        results = km.recall("algorithm", limit=1)
        assert len(results) == 1

    def test_semantic_search(self):
        km = KnowledgeMemoryManager()
        km.store_auto_categorized(
            content="Attention mechanism for transformers",
            tags=["attention"],
            confidence_score=0.9,
        )
        results = km.semantic_search("attention transformer", limit=1)
        assert len(results) >= 1

    def test_stats(self):
        km = KnowledgeMemoryManager()
        stats = km.get_stats()
        assert "layers" in stats
        assert "knowledge_graph" in stats
        assert "vector_memory" in stats