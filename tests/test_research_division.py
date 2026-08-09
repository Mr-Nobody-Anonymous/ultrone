"""Tests for the research division agents."""

import asyncio
import pytest

from research_division.base_agent import ResearchAgent, ResearchAgentRole
from research_division.research_scout import ResearchScout
from research_division.paper_analyzer import PaperAnalyzer
from research_division.algorithm_extractor import AlgorithmExtractor
from research_division.implementation_planner import ImplementationPlanner
from research_division.code_generator import CodeGeneratorAgent
from research_division.benchmark_agent import BenchmarkAgent
from research_division.experiment_manager import ExperimentManagerAgent
from research_division.knowledge_graph_builder import KnowledgeGraphBuilder
from research_division.citation_manager import CitationManager
from research_division.memory_manager import ResearchMemoryManagerAgent
from research_division.quality_reviewer import QualityReviewer
from research_division.safety_validator import SafetyValidator
from research_division.performance_optimizer import PerformanceOptimizer
from research_division.documentation_writer import DocumentationWriter
from research_division.release_manager import ReleaseManager
from research_division.coordinator import ResearchDivisionCoordinator


def run_async(coro):
    """Helper to run async coroutines in sync tests."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()
        asyncio.set_event_loop(None)


class TestBaseAgent:
    def test_agent_creation(self):
        agent = ResearchScout(agent_id="test-scout")
        assert agent.agent_id == "test-scout"
        assert agent.role == ResearchAgentRole.SCOUT

    def test_agent_logging(self):
        agent = ResearchScout(agent_id="test-scout")
        agent._log_action("test_action", {"key": "value"}, "result")
        assert len(agent.get_log()) == 1
        assert agent.actions_taken == 1

    def test_agent_stats(self):
        agent = ResearchScout(agent_id="test-scout")
        stats = agent.get_stats()
        assert stats["agent_id"] == "test-scout"
        assert stats["role"] == "research_scout"


class TestResearchScout:
    def test_discovery(self):
        scout = ResearchScout(agent_id="scout-test")
        result = run_async(scout.run(sources=["arxiv"], max_papers=1))
        assert result["discovered"] >= 1
        assert result["stored"] >= 1


class TestPaperAnalyzer:
    def test_analyze(self):
        analyzer = PaperAnalyzer(agent_id="analyzer-test")
        # Create a paper first
        from research_db.schema import PaperRecord
        paper = PaperRecord(title="Transformer architecture for NLP")
        analyzer.research_db.save_paper(paper)
        result = run_async(analyzer.run(paper_ids=[paper.paper_id]))
        assert result["analyzed"] == 1
        assert result["results"][0]["paper_id"] == paper.paper_id


class TestAlgorithmExtractor:
    def test_extract(self):
        extractor = AlgorithmExtractor(agent_id="extractor-test")
        from research_db.schema import PaperRecord
        paper = PaperRecord(title="Test", algorithms=["Transformer"])
        extractor.research_db.save_paper(paper)
        result = run_async(extractor.run(paper_ids=[paper.paper_id]))
        assert result["extracted"] == 1


class TestImplementationPlanner:
    def test_plan(self):
        planner = ImplementationPlanner(agent_id="planner-test")
        from research_db.schema import PaperRecord
        paper = PaperRecord(title="Test Paper", algorithms=["Transformer"])
        planner.research_db.save_paper(paper)
        result = run_async(planner.run(paper_ids=[paper.paper_id]))
        assert result["plans_created"] == 1


class TestCodeGenerator:
    def test_generate(self):
        coder = CodeGeneratorAgent(agent_id="coder-test")
        from research_db.schema import ImplementationPlan
        plan = ImplementationPlan(title="Test Module", steps=[{"step": 1}])
        coder.research_db.save_implementation_plan(plan)
        result = run_async(coder.run(plan_ids=[plan.plan_id]))
        assert result["generated"] == 1


class TestBenchmarkAgent:
    def test_benchmark(self):
        agent = BenchmarkAgent(agent_id="bench-test")
        from research_db.schema import ImplementationPlan
        plan = ImplementationPlan(title="Benchmark Plan")
        agent.research_db.save_implementation_plan(plan)
        result = run_async(agent.run(plan_ids=[plan.plan_id]))
        assert result["benchmarks_run"] == 1


class TestExperimentManager:
    def test_experiment(self):
        agent = ExperimentManagerAgent(agent_id="exp-test")
        from research_db.schema import ExperimentRecord
        exp = ExperimentRecord(hypothesis="Test hypothesis", status="proposed")
        agent.research_db.save_experiment(exp)
        result = run_async(agent.run(experiment_ids=[exp.experiment_id]))
        assert result["experiments_run"] == 1
        assert result["results"][0]["status"] == "completed"


class TestKnowledgeGraphBuilder:
    def test_build(self):
        agent = KnowledgeGraphBuilder(agent_id="graph-test")
        from research_db.schema import PaperRecord
        paper = PaperRecord(title="Graph Paper", authors=["Alice"], algorithms=["Transformer"])
        agent.research_db.save_paper(paper)
        result = run_async(agent.run())
        assert "nodes" in result


class TestCitationManager:
    def test_citations(self):
        agent = CitationManager(agent_id="cit-test")
        from research_db.schema import PaperRecord
        paper = PaperRecord(title="Citation Paper", authors=["Bob"], venue="NeurIPS")
        agent.research_db.save_paper(paper)
        result = run_async(agent.run())
        assert result["citations_added"] >= 1


class TestMemoryManagerAgent:
    def test_consolidation(self):
        agent = ResearchMemoryManagerAgent(agent_id="mem-test")
        result = run_async(agent.run())
        assert "consolidation" in result


class TestQualityReviewer:
    def test_review(self):
        agent = QualityReviewer(agent_id="review-test")
        from research_db.schema import ExperimentRecord
        exp = ExperimentRecord(
            hypothesis="H", dataset="D", evaluation_metrics={"acc": 0.9},
            conclusion="C", recommendation="adopt", status="completed",
        )
        agent.research_db.save_experiment(exp)
        result = run_async(agent.run())
        assert result["reviews"] >= 1


class TestSafetyValidator:
    def test_validate(self):
        agent = SafetyValidator(agent_id="safety-test")
        from research_db.schema import ExperimentRecord
        exp = ExperimentRecord(hypothesis="Safe hypothesis", dataset="D", status="completed")
        agent.research_db.save_experiment(exp)
        result = run_async(agent.run())
        assert result["validations"] >= 1


class TestPerformanceOptimizer:
    def test_optimize(self):
        agent = PerformanceOptimizer(agent_id="opt-test")
        from research_db.schema import ExperimentRecord
        exp = ExperimentRecord(
            hypothesis="H", resource_usage={"gpu_utilization": 0.3, "memory_gb": 5},
            status="completed",
        )
        agent.research_db.save_experiment(exp)
        result = run_async(agent.run())
        assert result["analyses"] >= 1


class TestDocumentationWriter:
    def test_document(self):
        agent = DocumentationWriter(agent_id="doc-test")
        from research_db.schema import PaperRecord
        paper = PaperRecord(title="Doc Paper")
        agent.research_db.save_paper(paper)
        result = run_async(agent.run())
        assert result["docs_generated"] >= 1


class TestReleaseManager:
    def test_release(self):
        agent = ReleaseManager(agent_id="rel-test")
        from research_db.schema import ExperimentRecord
        exp = ExperimentRecord(
            hypothesis="H", dataset="D", status="completed", recommendation="adopt",
        )
        agent.research_db.save_experiment(exp)
        result = run_async(agent.run())
        assert result["proposals"] >= 1


class TestCoordinator:
    def test_coordinator_creation(self):
        coord = ResearchDivisionCoordinator()
        assert len(coord.get_all_agents()) == 15

    def test_coordinator_stats(self):
        coord = ResearchDivisionCoordinator()
        stats = coord.get_stats()
        assert "coordinator" in stats
        assert "agents" in stats
