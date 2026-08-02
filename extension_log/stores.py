# Copyright (c) Ultrone Contributors. All rights reserved.
"""Log stores — multiple storage backends for the audit logger."""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .audit import LogEntry, LogLevel, LogCategory

logger = logging.getLogger("Ultrone.ExtensionLog.Stores")


class BaseLogStore:
    """Base class for log stores."""

    def write(self, entry: LogEntry) -> None:
        raise NotImplementedError

    def read(self, limit: int = 100) -> List[LogEntry]:
        raise NotImplementedError


class JSONLogStore(BaseLogStore):
    """JSON file-based log store."""

    def __init__(self, path: str = "logs/ultrone_log.jsonl"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, entry: LogEntry) -> None:
        with open(self.path, "a") as f:
            f.write(json.dumps(entry.to_dict()) + "\n")

    def read(self, limit: int = 100) -> List[LogEntry]:
        if not self.path.exists():
            return []
        entries = []
        with open(self.path, "r") as f:
            for line in f:
                try:
                    entries.append(LogEntry.from_dict(json.loads(line)))
                except Exception:
                    continue
        return entries[-limit:]


class MarkdownLogStore(BaseLogStore):
    """Markdown file-based log store."""

    def __init__(self, path: str = "logs/ultrone_log.md"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("# ULTRONE Research Platform Log\n\n")

    def write(self, entry: LogEntry) -> None:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(entry.timestamp))
        line = (
            f"## [{timestamp}] {entry.level.value.upper()} - {entry.category.value}\n"
            f"**Component:** {entry.component}\n\n"
            f"{entry.message}\n\n"
        )
        if entry.details:
            line += f"**Details:** ```json\n{json.dumps(entry.details, indent=2, default=str)}\n```\n\n"
        with open(self.path, "a") as f:
            f.write(line)

    def read(self, limit: int = 100) -> List[LogEntry]:
        if not self.path.exists():
            return []
        content = self.path.read_text()
        # Simple parse - just return empty for now (markdown is for human reading)
        return []


class SQLiteLogStore(BaseLogStore):
    """SQLite-backed log store."""

    def __init__(self, path: str = "logs/ultrone_log.db"):
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self):
        return sqlite3.connect(self.path)

    def _init_schema(self) -> None:
        conn = self._connect()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS logs (
                    log_id TEXT PRIMARY KEY,
                    timestamp REAL,
                    level TEXT,
                    category TEXT,
                    component TEXT,
                    message TEXT,
                    details TEXT
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def write(self, entry: LogEntry) -> None:
        conn = self._connect()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO logs (log_id, timestamp, level, category, component, message, details) VALUES (?,?,?,?,?,?,?)",
                (
                    entry.log_id,
                    entry.timestamp,
                    entry.level.value,
                    entry.category.value,
                    entry.component,
                    entry.message,
                    json.dumps(entry.details, default=str),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def read(self, limit: int = 100) -> List[LogEntry]:
        conn = self._connect()
        try:
            cur = conn.execute(
                "SELECT log_id, timestamp, level, category, component, message, details FROM logs ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            )
            rows = cur.fetchall()
        finally:
            conn.close()
        return [
            LogEntry(
                log_id=r[0],
                timestamp=r[1],
                level=LogLevel(r[2]),
                category=LogCategory(r[3]),
                component=r[4],
                message=r[5],
                details=json.loads(r[6]) if r[6] else {},
            )
            for r in rows
        ]


class VectorLogStore(BaseLogStore):
    """Vector database-backed log store (uses VectorMemory)."""

    def __init__(self, knowledge: Any = None):
        from knowledge_engine.vector_memory import VectorMemory
        self.vector_memory = knowledge.vector_memory if knowledge else VectorMemory()
        self._entries: List[LogEntry] = []

    def write(self, entry: LogEntry) -> None:
        self._entries.append(entry)
        # Index in vector memory for semantic search
        from knowledge_engine.base import KnowledgeEntry, KnowledgeSource, KnowledgeCategory
        ke = KnowledgeEntry(
            content=f"{entry.message} {json.dumps(entry.details, default=str)}",
            category=KnowledgeCategory.INSIGHT,
            source=KnowledgeSource.ANALYSIS,
            tags=[entry.category.value, entry.level.value],
            metadata={"log_id": entry.log_id, "component": entry.component},
        )
        self.vector_memory.index(ke)

    def read(self, limit: int = 100) -> List[LogEntry]:
        return self._entries[-limit:]

    def search(self, query: str, limit: int = 10) -> List[LogEntry]:
        """Search logs semantically."""
        results = self.vector_memory.search(query, limit=limit)
        # Map back to entries by log_id
        log_by_id = {e.log_id: e for e in self._entries}
        matched = []
        for entry_id, score in results:
            # entry_id is the KnowledgeEntry ID, not log_id
            pass
        return matched


class KnowledgeGraphLogStore(BaseLogStore):
    """Knowledge graph-backed log store."""

    def __init__(self, knowledge: Any = None):
        from knowledge_engine.knowledge_graph import KnowledgeGraph, NodeType
        self._NodeType = NodeType
        self.knowledge_graph = knowledge.knowledge_graph if knowledge else KnowledgeGraph()
        self._entries: List[LogEntry] = []

    def write(self, entry: LogEntry) -> None:
        self._entries.append(entry)
        # Add node to knowledge graph
        self.knowledge_graph.add_node(
            label=f"Log: {entry.message[:50]}",
            node_type=self._NodeType.CONCEPT,
            properties={
                "log_id": entry.log_id,
                "level": entry.level.value,
                "category": entry.category.value,
                "component": entry.component,
            },
            source=entry.component or "unknown",
            confidence_score=0.9 if entry.level.value == "info" else 0.5,
        )

    def read(self, limit: int = 100) -> List[LogEntry]:
        return self._entries[-limit:]