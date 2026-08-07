"""Tests for the self-improvement loop."""

import asyncio
import pytest

from self_improvement.telemetry import TelemetryCollector
from self_improvement.hypothesis_generator import HypothesisGenerator
from self_improvement.literature_search import LiteratureSearch
from self_improvement.improvement_loop import SelfImprovementLoop


def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class TestTelemetryCollector:
    def test_record_metric(self):
        tc = TelemetryCollector()
        tc.record_metric("accuracy", 0.85)
        tc.record_metric("accuracy", 0.90)
        stats = tc.get_metric_stats("accuracy")
        assert stats["count"] == 2
        assert stats["mean"] == 0.875

    def test_record_failure(self):
        tc = TelemetryCollector()
        tc.record_failure("component_a", "error message")
        tc.record_failure("component_a", "error message")
        tc.record_failure("component_a", "error message")
        weaknesses = tc.identify_weaknesses()
        assert len(weaknesses) >= 1
        assert weaknesses[0]["type"] == "high_failure_rate"

    def test_stats(self):
        tc = TelemetryCollector()
        stats = tc.get_stats()
        assert stats["type"] == "TelemetryCollector"


class TestHypothesisGenerator:
    def test_generate_from_weaknesses(self):
        hg = HypothesisGenerator()
        weaknesses = [{"type": "high_failure_rate", "component": "test", "severity": "high"}]
        hypotheses = hg.generate_from_weaknesses(weaknesses)
        assert len(hypotheses) == 1
        assert hypotheses[0]["source"] == "telemetry"

    def test_generate_from_research(self):
        hg = HypothesisGenerator()
        from research_db.schema import PaperRecord
        paper = PaperRecord(title="Test", algorithms=["Transformer"])
        hypotheses = hg.generate_from_research([paper])
        assert len(hypotheses) == 1
        assert hypotheses[0]["source"] == "research"


class TestLiteratureSearch:
    def test_search_papers(self):
        ls = LiteratureSearch()
        from research_db.schema import PaperRecord
        paper = PaperRecord(title="Transformer paper", summary="About transformers")
        ls.research_db.save_paper(paper)
        results = ls.search_papers("transformer")
        assert len(results) >= 1

    def test_search_knowledge(self):
        ls = LiteratureSearch()
        ls.knowledge.store_auto_categorized(
            content="Knowledge about attention mechanisms",
            tags=["attention"],
        )
        results = ls.search_knowledge("attention")
        assert len(results) >= 1


class TestSelfImprovementLoop:
    def test_run_cycle(self):
        loop = SelfImprovementLoop(min_benchmark_gain=0.02)
        result = run_async(loop.run_cycle())
        assert result["cycle"] == 1
        assert "weaknesses_identified" in result
        assert "hypotheses_generated" in result
        assert "experiments_run" in result

    def test_stats(self):
        loop = SelfImprovementLoop()
        stats = loop.get_stats()
        assert stats["type"] == "SelfImprovementLoop"
        assert "telemetry" in stats
