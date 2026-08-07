"""Tests for the extension log package."""

import pytest
import tempfile
from pathlib import Path

from extension_log.audit import AuditLogger, LogLevel, LogCategory, LogEntry
from extension_log.stores import (
    JSONLogStore, MarkdownLogStore, SQLiteLogStore, VectorLogStore,
    KnowledgeGraphLogStore,
)


class TestAuditLogger:
    def test_log_entry(self):
        entry = LogEntry(message="Test message", level=LogLevel.INFO)
        assert entry.log_id is not None
        data = entry.to_dict()
        restored = LogEntry.from_dict(data)
        assert restored.message == "Test message"

    def test_logger_basic(self):
        logger = AuditLogger()
        entry = logger.info("Test info message")
        assert entry.level == LogLevel.INFO
        assert len(logger.get_entries()) == 1

    def test_logger_levels(self):
        logger = AuditLogger()
        logger.info("Info")
        logger.warning("Warning")
        logger.error("Error")
        logger.critical("Critical")
        assert len(logger.get_entries()) == 4

    def test_logger_categories(self):
        logger = AuditLogger()
        entry = logger.info("Experiment log", LogCategory.EXPERIMENT, "exp-1")
        assert entry.category == LogCategory.EXPERIMENT
        assert entry.component == "exp-1"


class TestJSONLogStore:
    def test_write_and_read(self, tmp_path):
        store = JSONLogStore(path=str(tmp_path / "logs.jsonl"))
        entry = LogEntry(message="JSON test")
        store.write(entry)
        entries = store.read()
        assert len(entries) == 1
        assert entries[0].message == "JSON test"


class TestMarkdownLogStore:
    def test_write(self, tmp_path):
        store = MarkdownLogStore(path=str(tmp_path / "log.md"))
        store.write(LogEntry(message="Markdown test"))
        assert store.path.exists()
        content = store.path.read_text()
        assert "Markdown test" in content


class TestSQLiteLogStore:
    def test_write_and_read(self, tmp_path):
        store = SQLiteLogStore(path=str(tmp_path / "logs.db"))
        store.write(LogEntry(message="SQLite test"))
        entries = store.read()
        assert len(entries) >= 1


class TestVectorLogStore:
    def test_write(self, tmp_path):
        store = VectorLogStore()
        store.write(LogEntry(message="Vector test"))
        entries = store.read()
        assert len(entries) == 1


class TestKnowledgeGraphLogStore:
    def test_write(self):
        store = KnowledgeGraphLogStore()
        store.write(LogEntry(message="Graph test"))
        entries = store.read()
        assert len(entries) == 1
        assert store.knowledge_graph.count_nodes() >= 1


class TestMultiStore:
    def test_multiple_stores(self, tmp_path):
        json_store = JSONLogStore(path=str(tmp_path / "multi.jsonl"))
        sqlite_store = SQLiteLogStore(path=str(tmp_path / "multi.db"))
        logger = AuditLogger(stores=[json_store, sqlite_store])
        logger.info("Multi-store test")
        assert len(logger.get_entries()) == 1
        assert len(json_store.read()) == 1
        assert len(sqlite_store.read()) == 1
