"""Tests for the research database package."""

import pytest
import tempfile
from pathlib import Path

from research_db.schema import (
    PaperRecord, ExperimentRecord, BenchmarkRecord, ImplementationPlan,
    ResearchDatabaseSchema,
)
from research_db.store import ResearchDatabase, JSONResearchStore, SQLiteResearchStore


class TestSchema:
    def test_paper_record(self):
        paper = PaperRecord(title="Test Paper", authors=["Alice", "Bob"])
        data = paper.to_dict()
        restored = PaperRecord.from_dict(data)
        assert restored.title == "Test Paper"
        assert restored.authors == ["Alice", "Bob"]

    def test_experiment_record(self):
        exp = ExperimentRecord(hypothesis="Test hypothesis", status="proposed")
        data = exp.to_dict()
        restored = ExperimentRecord.from_dict(data)
        assert restored.hypothesis == "Test hypothesis"

    def test_benchmark_record(self):
        bench = BenchmarkRecord(name="Test Benchmark", improvement=0.05)
        data = bench.to_dict()
        restored = BenchmarkRecord.from_dict(data)
        assert restored.improvement == 0.05

    def test_implementation_plan(self):
        plan = ImplementationPlan(title="Test Plan", steps=[{"step": 1}])
        data = plan.to_dict()
        restored = ImplementationPlan.from_dict(data)
        assert restored.title == "Test Plan"

    def test_schema_factory(self):
        record = ResearchDatabaseSchema.create_record("paper", title="Factory Paper")
        assert isinstance(record, PaperRecord)


class TestJSONStore:
    def test_save_and_get(self, tmp_path):
        store = JSONResearchStore(base_dir=str(tmp_path / "research_db"))
        paper = PaperRecord(title="JSON Paper")
        store.save("paper", paper)
        found = store.get("paper", paper.paper_id)
        assert found is not None
        assert found.title == "JSON Paper"

    def test_list_and_delete(self, tmp_path):
        store = JSONResearchStore(base_dir=str(tmp_path / "research_db"))
        paper = PaperRecord(title="List Paper")
        store.save("paper", paper)
        papers = store.list_all("paper")
        assert len(papers) == 1
        assert store.delete("paper", paper.paper_id)
        assert len(store.list_all("paper")) == 0


class TestSQLiteStore:
    def test_save_and_get(self, tmp_path):
        store = SQLiteResearchStore(db_path=str(tmp_path / "test.db"))
        exp = ExperimentRecord(hypothesis="SQLite hypothesis")
        store.save("experiment", exp)
        found = store.get("experiment", exp.experiment_id)
        assert found is not None
        assert found.hypothesis == "SQLite hypothesis"

    def test_version_history(self, tmp_path):
        store = SQLiteResearchStore(db_path=str(tmp_path / "test.db"))
        exp = ExperimentRecord(hypothesis="V1")
        store.save("experiment", exp)
        exp.hypothesis = "V2"
        store.save("experiment", exp)
        history = store.get_history("experiment", exp.experiment_id)
        assert len(history) >= 1


class TestResearchDatabase:
    def test_facade(self, tmp_path):
        db = ResearchDatabase(backend="json", base_dir=str(tmp_path / "rdb"))
        paper = PaperRecord(title="Facade Paper")
        db.save_paper(paper)
        assert db.get_paper(paper.paper_id) is not None
        assert len(db.list_papers()) == 1

    def test_stats(self, tmp_path):
        db = ResearchDatabase(backend="json", base_dir=str(tmp_path / "rdb"))
        stats = db.get_stats()
        assert "type" in stats
