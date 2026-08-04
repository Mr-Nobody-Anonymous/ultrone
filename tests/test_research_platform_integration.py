# Copyright (c) Ultrone Contributors. All rights reserved.
"""Integration tests for the ULTRONE Research Platform.

Tests the full research pipeline:
- Research Scout → Paper Analyzer → Algorithm Extractor →
- Implementation Planner → Code Generator → Benchmark Agent →
- Experiment Manager → Knowledge Graph Builder → Citation Manager →
- Memory Manager → Quality Reviewer → Safety Validator →
- Performance Optimizer → Documentation Writer → Release Manager
"""

from __future__ import annotations

import logging
import time
import unittest
import asyncio
from typing import Any, Dict

from knowledge_engine.memory_manager import KnowledgeMemoryManager
from research_db.store import ResearchDatabase
from research_db.schema import PaperRecord, ExperimentRecord, BenchmarkRecord, ImplementationPlan
from research_division.coordinator import ResearchDivisionCoordinator
from research_division.base_agent import ResearchAgent, ResearchAgentRole
from research_division.research_scout import ResearchScout
from self_improvement.improvement_loop import SelfImprovementLoop
from extension_log.audit import AuditLogger, LogCategory, LogLevel

logger = logging.getLogger("Ultrone.IntegrationTests")


class TestResearchPlatformIntegration(unittest.TestCase):
    """Integration tests for the complete research platform."""

    def setUp(self):
        """Set up test fixtures."""
        self.knowledge = KnowledgeMemoryManager()
        self.research_db = ResearchDatabase(backend="json", base_dir="test_research_db")
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        """Clean up test fixtures."""
        self.loop.close()
        # Clean up test directory
        import shutil
        shutil.rmtree("test_research_db", ignore_errors=True)

    def test_research_scout_discovers_papers(self):
        """Test that Research Scout discovers and stores papers."""
        scout = ResearchScout(
            knowledge=self.knowledge,
            research_db=self.research_db,
            config={"sample_papers": [
                {
                    "source": "arxiv",
                    "title": "Test Paper on Mixture of Experts",
                    "venue": "arXiv",
                    "arxiv_id": "2401.00001",
                }
            ]},
        )
        result = self.loop.run_until_complete(scout.run(max_papers=5))
        self.assertGreater(result["discovered"], 0)
        self.assertGreater(result["stored"], 0)
        self.assertEqual(len(result["paper_ids"]), result["stored"])

    def test_paper_record_persistence(self):
        """Test that paper records are persisted correctly."""
        paper = PaperRecord(
            title="Integration Test Paper",
            authors=["Alice", "Bob"],
            venue="Test Venue",
            arxiv_id="2401.00002",
            abstract="This is a test paper for integration testing.",
            algorithms=["TestAlgorithm"],
            confidence_score=0.9,
        )
        stored = self.research_db.save_paper(paper)
        retrieved = self.research_db.get_paper(stored.paper_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.title, paper.title)
        self.assertEqual(retrieved.authors, paper.authors)

    def test_experiment_lifecycle(self):
        """Test experiment creation, update, and retrieval."""
        experiment = ExperimentRecord(
            hypothesis="Test hypothesis",
            research_motivation="Testing experiment lifecycle",
            implementation="test_implementation",
            dataset="test_dataset",
            success_criteria="accuracy >= 0.9",
        )
        stored = self.research_db.save_experiment(experiment)
        self.assertEqual(stored.status, "proposed")
        
        # Update experiment
        stored.status = "running"
        stored.evaluation_metrics = {"accuracy": 0.95}
        self.research_db.save_experiment(stored)
        
        # Retrieve and verify
        retrieved = self.research_db.get_experiment(stored.experiment_id)
        self.assertEqual(retrieved.status, "running")
        self.assertEqual(retrieved.evaluation_metrics["accuracy"], 0.95)

    def test_benchmark_record(self):
        """Test benchmark record creation and storage."""
        benchmark = BenchmarkRecord(
            name="Test Benchmark",
            description="Integration test benchmark",
            task_type="classification",
            dataset="test_dataset",
            metrics={"accuracy": 0.9},
            baseline_results={"baseline": 0.8},
            candidate_results={"candidate": 0.85},
            improvement=0.05,
        )
        stored = self.research_db.save_benchmark(benchmark)
        retrieved = self.research_db.get_benchmark(stored.benchmark_id)
        self.assertEqual(retrieved.name, benchmark.name)
        self.assertEqual(retrieved.improvement, 0.05)

    def test_implementation_plan(self):
        """Test implementation plan creation and storage."""
        plan = ImplementationPlan(
            title="Test Implementation Plan",
            description="Integration test plan",
            source_paper_ids=["P-123"],
            steps=[{"step": 1, "action": "implement algorithm"}],
            expected_improvements=["10% accuracy gain"],
        )
        stored = self.research_db.save_implementation_plan(plan)
        retrieved = self.research_db.get_implementation_plan(stored.plan_id)
        self.assertEqual(retrieved.title, plan.title)
        self.assertEqual(len(retrieved.steps), 1)

    def test_knowledge_engine_storage_and_retrieval(self):
        """Test knowledge engine storage and retrieval."""
        from knowledge_engine.base import KnowledgeSource
        entry = self.knowledge.store_auto_categorized(
            content="Test knowledge entry about reinforcement learning",
            source=KnowledgeSource.PAPER,
            tags=["RL", "reinforcement learning"],
            entities=["Q-learning"],
            confidence_score=0.85,
            layer="semantic",
        )
        self.assertIsNotNone(entry.entry_id)
        
        # Test recall
        results = self.knowledge.recall("reinforcement learning", limit=5)
        self.assertGreater(len(results), 0)
        
        # Test semantic search
        semantic_results = self.knowledge.semantic_search("RL algorithms", limit=5)
        self.assertIsInstance(semantic_results, list)

    def test_research_division_coordinator_agents(self):
        """Test that coordinator initializes all agents."""
        coordinator = ResearchDivisionCoordinator(
            knowledge=self.knowledge,
            research_db=self.research_db,
        )
        agents = coordinator.get_all_agents()
        expected_agents = [
            "scout", "analyzer", "extractor", "planner", "codegen",
            "benchmark", "experiment", "graph", "citation", "memory",
            "reviewer", "safety", "optimizer", "writer", "release",
        ]
        for agent_name in expected_agents:
            self.assertIn(agent_name, agents)
            self.assertIsInstance(agents[agent_name], ResearchAgent)

    def test_self_improvement_loop_cycle(self):
        """Test that self-improvement loop executes a cycle."""
        loop = SelfImprovementLoop(
            knowledge=self.knowledge,
            research_db=self.research_db,
        )
        result = self.loop.run_until_complete(loop.run_cycle())
        self.assertIn("cycle", result)
        self.assertIn("weaknesses_identified", result)
        self.assertIn("hypotheses_generated", result)
        self.assertIn("experiments_run", result)
        self.assertIn("adopted", result)
        self.assertIn("rejected", result)
        self.assertEqual(result["cycle"], 1)

    def test_audit_logging(self):
        """Test audit logging framework."""
        logger_inst = AuditLogger()
        entry = logger_inst.log(
            message="Test log message",
            level=LogLevel.INFO,
            category=LogCategory.EXPERIMENT,
            component="test_component",
            details={"key": "value"},
        )
        self.assertIsNotNone(entry.log_id)
        self.assertEqual(entry.category, LogCategory.EXPERIMENT)
        self.assertEqual(entry.component, "test_component")
        
        entries = logger_inst.get_entries(limit=10)
        self.assertGreater(len(entries), 0)

    def test_knowledge_graph_integration(self):
        """Test knowledge graph integration with knowledge engine."""
        entry = self.knowledge.store_auto_categorized(
            content="Test concept for knowledge graph",
            tags=["concept", "test"],
            confidence_score=0.8,
        )
        
        # Verify graph node was created
        graph = self.knowledge.knowledge_graph
        node = graph.get_node(entry.entry_id)
        self.assertIsNotNone(node)
        self.assertEqual(node.label, entry.content[:80])

    def test_vector_memory_indexing(self):
        """Test vector memory indexing and retrieval."""
        entry = self.knowledge.store_auto_categorized(
            content="Vector memory test entry about neural networks",
            tags=["neural networks", "deep learning"],
            confidence_score=0.9,
        )
        
        # Search should find the entry
        results = self.knowledge.vector_memory.search("neural networks", limit=5)
        self.assertIsInstance(results, list)

    def test_citation_database(self):
        """Test citation database functionality."""
        from knowledge_engine.citation_db import Citation
        citation = Citation(
            title="Test Paper",
            authors=["Author One"],
            year=2024,
            venue="Test Venue",
        )
        citation_id = self.knowledge.register_citation(citation)
        self.assertIsNotNone(citation_id)
        
        # Verify citation was registered
        stats = self.knowledge.citation_db.get_stats()
        self.assertGreater(stats["citations"], 0)

    def test_research_pipeline_end_to_end(self):
        """Test a simplified end-to-end research pipeline."""
        # Phase 1: Discovery
        scout = ResearchScout(
            knowledge=self.knowledge,
            research_db=self.research_db,
        )
        discovery_result = self.loop.run_until_complete(scout.run(max_papers=2))
        self.assertGreaterEqual(discovery_result["stored"], 0)
        
        # Phase 2: Run self-improvement cycle
        loop = SelfImprovementLoop(
            knowledge=self.knowledge,
            research_db=self.research_db,
        )
        improvement_result = self.loop.run_until_complete(loop.run_cycle())
        self.assertEqual(improvement_result["cycle"], 1)

    def test_research_db_stats(self):
        """Test research database statistics."""
        # Add some records
        paper = PaperRecord(title="Stats Test Paper")
        self.research_db.save_paper(paper)
        
        experiment = ExperimentRecord(hypothesis="Stats test hypothesis")
        self.research_db.save_experiment(experiment)
        
        stats = self.research_db.get_stats()
        self.assertIn("paper", stats)
        self.assertIn("experiment", stats)
        self.assertGreaterEqual(stats["paper"], 1)
        self.assertGreaterEqual(stats["experiment"], 1)

    def test_multiple_memory_layers(self):
        """Test storing and retrieving from multiple memory layers."""
        layers = ["semantic", "episodic", "working", "procedural", "research"]
        for layer in layers:
            entry = self.knowledge.store_auto_categorized(
                content=f"Test entry for {layer} memory",
                tags=[layer, "test"],
                confidence_score=0.7,
                layer=layer,
            )
            self.assertIsNotNone(entry.entry_id)
        
        # Verify all layers have entries
        layer_stats = self.knowledge.get_stats()
        for layer in layers:
            self.assertIn(layer, layer_stats["layers"])

    def test_knowledge_consolidation(self):
        """Test knowledge consolidation."""
        # Add multiple entries
        for i in range(5):
            self.knowledge.store_auto_categorized(
                content=f"Duplicate test entry {i} about machine learning",
                tags=["ML", "duplicate"],
                confidence_score=0.5,
            )
        
        # Run consolidation
        report = self.knowledge.consolidate_all()
        self.assertIn("kept_count", report)
        self.assertIn("deduplicated_count", report)

    def test_agent_communication_bus(self):
        """Test agent communication via message bus."""
        from comms.protocol import Message, MessageType, Priority
        from comms.message_bus import MessageBus
        
        async def run_test():
            bus = MessageBus()
            received_messages = []
            
            async def handler(message):
                received_messages.append(message)
            
            bus.subscribe("test-agent", handler)
            await bus.start()
            
            # Publish a message
            msg = Message.create(
                message_type=MessageType.RESEARCH_PAPER_DISCOVERED,
                sender_id="test-sender",
                content={"paper_id": "P-TEST"},
                recipient_id="test-agent",
                priority=Priority.ROUTINE,
            )
            await bus.publish(msg)
            await asyncio.sleep(0.05)
            await bus.stop()
            return received_messages
        
        received_messages = self.loop.run_until_complete(run_test())
        self.assertEqual(len(received_messages), 1)
        self.assertEqual(received_messages[0].content["paper_id"], "P-TEST")


class TestResearchAgentLifecycle(unittest.TestCase):
    """Test research agent lifecycle and statistics."""

    def setUp(self):
        self.knowledge = KnowledgeMemoryManager()
        self.research_db = ResearchDatabase(backend="json", base_dir="test_research_db")
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()
        import shutil
        shutil.rmtree("test_research_db", ignore_errors=True)

    def test_agent_creation_and_stats(self):
        """Test agent creation and statistics tracking."""
        scout = ResearchScout(
            knowledge=self.knowledge,
            research_db=self.research_db,
        )
        stats = scout.get_stats()
        self.assertEqual(stats["role"], "research_scout")
        self.assertEqual(stats["actions_taken"], 0)
        self.assertEqual(stats["log_entries"], 0)

    def test_agent_logging(self):
        """Test that agents log actions."""
        scout = ResearchScout(
            knowledge=self.knowledge,
            research_db=self.research_db,
        )
        
        # Run a discovery cycle
        self.loop.run_until_complete(scout.run(max_papers=1))
        
        # Check log entries
        log = scout.get_log()
        self.assertGreater(len(log), 0)
        
        # Check stats
        stats = scout.get_stats()
        self.assertGreater(stats["actions_taken"], 0)
        self.assertGreater(stats["log_entries"], 0)

    def test_coordinator_pipeline_stats(self):
        """Test coordinator pipeline statistics."""
        coordinator = ResearchDivisionCoordinator(
            knowledge=self.knowledge,
            research_db=self.research_db,
        )
        stats = coordinator.get_stats()
        self.assertIn("coordinator", stats)
        self.assertIn("agents", stats)
        self.assertEqual(len(stats["agents"]), 15)


class TestDatabaseBackends(unittest.TestCase):
    """Test both JSON and SQLite database backends."""

    def test_json_backend(self):
        """Test JSON backend functionality."""
        db = ResearchDatabase(backend="json", base_dir="test_json_db")
        paper = PaperRecord(title="JSON Backend Test")
        stored = db.save_paper(paper)
        retrieved = db.get_paper(stored.paper_id)
        self.assertEqual(retrieved.title, "JSON Backend Test")
        import shutil
        shutil.rmtree("test_json_db", ignore_errors=True)

    def test_sqlite_backend(self):
        """Test SQLite backend functionality."""
        db = ResearchDatabase(backend="sqlite", db_path="test_sqlite.db")
        paper = PaperRecord(title="SQLite Backend Test")
        stored = db.save_paper(paper)
        retrieved = db.get_paper(stored.paper_id)
        self.assertEqual(retrieved.title, "SQLite Backend Test")
        import os
        os.remove("test_sqlite.db")


if __name__ == "__main__":
    unittest.main()