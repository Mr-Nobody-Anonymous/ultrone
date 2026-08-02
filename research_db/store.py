# Copyright (c) Ultrone Contributors. All rights reserved.
"""Research database store — JSON and SQLite backends.

Provides persistent storage for paper records, experiment records,
benchmark records, and implementation plans with version history
and complete audit trails.
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("Ultrone.ResearchDB")


class BaseStore:
    """Abstract base for research database stores."""

    def save(self, record_type: str, record: Any) -> Any:
        raise NotImplementedError

    def get(self, record_type: str, record_id: str) -> Optional[Any]:
        raise NotImplementedError

    def list_all(self, record_type: str) -> List[Any]:
        raise NotImplementedError

    def delete(self, record_type: str, record_id: str) -> bool:
        raise NotImplementedError


class JSONResearchStore(BaseStore):
    """JSON-file-backed store with per-record files and version history."""

    def __init__(self, base_dir: str = "research_db"):
        self.base_dir = Path(base_dir)
        self.records_dir = self.base_dir / "records"
        self.history_dir = self.base_dir / "history"
        self.records_dir.mkdir(parents=True, exist_ok=True)
        self.history_dir.mkdir(parents=True, exist_ok=True)

    def save(self, record_type: str, record: Any) -> Any:
        """Save a record. Returns the saved record (may have bumped version)."""
        record_dict = record.to_dict()
        record_id = record_dict.get(
            f"{record_type}_id",
            record_dict.get("paper_id", record_dict.get("experiment_id",
                record_dict.get("benchmark_id", record_dict.get("plan_id", "")))),
        )
        if not record_id:
            record_id = f"{record_type}-{uuid.uuid4().hex[:8]}"
            if record_type == "paper":
                record.paper_id = record_id
            elif record_type == "experiment":
                record.experiment_id = record_id
            elif record_type == "benchmark":
                record.benchmark_id = record_id
            elif record_type == "implementation_plan":
                record.plan_id = record_id
            record_dict = record.to_dict()

        # Save history (previous version)
        existing_file = self.records_dir / record_type / f"{record_id}.json"
        if existing_file.exists():
            with open(existing_file, "r") as f:
                old_data = json.load(f)
            history_file = self.history_dir / record_type / f"{record_id}_v{old_data.get('version', 1)}.json"
            history_file.parent.mkdir(parents=True, exist_ok=True)
            with open(history_file, "w") as f:
                json.dump(old_data, f, indent=2, default=str)

        # Save record
        out_file = self.records_dir / record_type / f"{record_id}.json"
        out_file.parent.mkdir(parents=True, exist_ok=True)
        record_dict["updated_at"] = time.time()
        with open(out_file, "w") as f:
            json.dump(record_dict, f, indent=2, default=str)
        return record

    def get(self, record_type: str, record_id: str) -> Optional[Any]:
        """Get a record by ID."""
        from .schema import ResearchDatabaseSchema
        file_path = self.records_dir / record_type / f"{record_id}.json"
        if not file_path.exists():
            return None
        with open(file_path, "r") as f:
            data = json.load(f)
        record_cls = ResearchDatabaseSchema.RECORD_TYPES.get(record_type)
        if record_cls is None:
            return None
        return record_cls.from_dict(data)

    def list_all(self, record_type: str) -> List[Any]:
        """List all records of a type."""
        from .schema import ResearchDatabaseSchema
        record_cls = ResearchDatabaseSchema.RECORD_TYPES.get(record_type)
        if record_cls is None:
            return []
        dir_path = self.records_dir / record_type
        if not dir_path.exists():
            return []
        records = []
        for f in dir_path.glob("*.json"):
            try:
                with open(f, "r") as fh:
                    data = json.load(fh)
                records.append(record_cls.from_dict(data))
            except Exception:
                logger.warning("Failed to load record %s", f, exc_info=True)
        return records

    def delete(self, record_type: str, record_id: str) -> bool:
        """Delete a record."""
        file_path = self.records_dir / record_type / f"{record_id}.json"
        if file_path.exists():
            file_path.unlink()
            return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        stats = {"type": "JSONResearchStore", "base_dir": str(self.base_dir)}
        for record_type in ("paper", "experiment", "benchmark", "implementation_plan"):
            dir_path = self.records_dir / record_type
            count = len(list(dir_path.glob("*.json"))) if dir_path.exists() else 0
            stats[record_type] = count
        return stats


class SQLiteResearchStore(BaseStore):
    """SQLite-backed store for the research database."""

    def __init__(self, db_path: str = "research_db/ultrone_research.db"):
        import sqlite3
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self):
        import sqlite3
        return sqlite3.connect(self.db_path)

    def _init_schema(self) -> None:
        conn = self._connect()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS records (
                    record_type TEXT NOT NULL,
                    record_id TEXT NOT NULL,
                    data TEXT NOT NULL,
                    version INTEGER DEFAULT 1,
                    created_at REAL,
                    updated_at REAL,
                    PRIMARY KEY (record_type, record_id)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS record_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    record_type TEXT NOT NULL,
                    record_id TEXT NOT NULL,
                    data TEXT NOT NULL,
                    version INTEGER,
                    archived_at REAL
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def save(self, record_type: str, record: Any) -> Any:
        """Save a record. Returns saved record."""
        import sqlite3
        record_dict = record.to_dict()
        # Determine ID field based on type
        id_field = {
            "paper": "paper_id",
            "experiment": "experiment_id",
            "benchmark": "benchmark_id",
            "implementation_plan": "plan_id",
        }.get(record_type, "record_id")
        record_id = record_dict.get(id_field, "")

        conn = self._connect()
        try:
            # Check existing
            cur = conn.execute(
                "SELECT data, version FROM records WHERE record_type=? AND record_id=?",
                (record_type, record_id),
            )
            row = cur.fetchone()
            if row:
                # Archive history
                old_data, old_version = row
                conn.execute(
                    "INSERT INTO record_history (record_type, record_id, data, version, archived_at) VALUES (?,?,?,?,?)",
                    (record_type, record_id, old_data, old_version, time.time()),
                )
                # Update
                conn.execute(
                    "UPDATE records SET data=?, version=version+1, updated_at=? WHERE record_type=? AND record_id=?",
                    (json.dumps(record_dict), time.time(), record_type, record_id),
                )
            else:
                # Insert
                conn.execute(
                    "INSERT INTO records (record_type, record_id, data, version, created_at, updated_at) VALUES (?,?,?,1,?,?)",
                    (record_type, record_id, json.dumps(record_dict), time.time(), time.time()),
                )
            conn.commit()
        finally:
            conn.close()
        return record

    def get(self, record_type: str, record_id: str) -> Optional[Any]:
        """Get a record by ID."""
        from .schema import ResearchDatabaseSchema
        conn = self._connect()
        try:
            cur = conn.execute(
                "SELECT data FROM records WHERE record_type=? AND record_id=?",
                (record_type, record_id),
            )
            row = cur.fetchone()
        finally:
            conn.close()
        if row is None:
            return None
        data = json.loads(row[0])
        record_cls = ResearchDatabaseSchema.RECORD_TYPES.get(record_type)
        if record_cls is None:
            return None
        return record_cls.from_dict(data)

    def list_all(self, record_type: str) -> List[Any]:
        """List all records of a type."""
        from .schema import ResearchDatabaseSchema
        conn = self._connect()
        try:
            cur = conn.execute(
                "SELECT data FROM records WHERE record_type=?",
                (record_type,),
            )
            rows = cur.fetchall()
        finally:
            conn.close()
        record_cls = ResearchDatabaseSchema.RECORD_TYPES.get(record_type)
        if record_cls is None:
            return []
        return [record_cls.from_dict(json.loads(r[0])) for r in rows]

    def delete(self, record_type: str, record_id: str) -> bool:
        """Delete a record."""
        conn = self._connect()
        try:
            cur = conn.execute(
                "DELETE FROM records WHERE record_type=? AND record_id=?",
                (record_type, record_id),
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    def get_history(self, record_type: str, record_id: str) -> List[Dict[str, Any]]:
        """Get version history for a record."""
        conn = self._connect()
        try:
            cur = conn.execute(
                "SELECT data, version, archived_at FROM record_history WHERE record_type=? AND record_id=? ORDER BY version",
                (record_type, record_id),
            )
            rows = cur.fetchall()
        finally:
            conn.close()
        return [
            {"data": json.loads(r[0]), "version": r[1], "archived_at": r[2]}
            for r in rows
        ]

    def get_stats(self) -> Dict[str, Any]:
        conn = self._connect()
        try:
            cur = conn.execute("SELECT record_type, COUNT(*) FROM records GROUP BY record_type")
            rows = cur.fetchall()
        finally:
            conn.close()
        stats = {"type": "SQLiteResearchStore", "db_path": self.db_path}
        for record_type, count in rows:
            stats[record_type] = count
        return stats


class ResearchDatabase:
    """High-level research database facade.

    Supports both JSON and SQLite backends with automatic record
    versioning and complete audit trails.
    """

    def __init__(
        self,
        backend: str = "json",
        base_dir: str = "research_db",
        db_path: str = "research_db/ultrone_research.db",
    ):
        self.backend = backend
        if backend == "sqlite":
            self.store = SQLiteResearchStore(db_path=db_path)
        else:
            self.store = JSONResearchStore(base_dir=base_dir)

    # ------------------------------------------------------------------
    # Papers
    # ------------------------------------------------------------------
    def save_paper(self, paper: Any) -> Any:
        """Save a paper record."""
        return self.store.save("paper", paper)

    def get_paper(self, paper_id: str) -> Optional[Any]:
        """Get a paper by ID."""
        return self.store.get("paper", paper_id)

    def list_papers(self) -> List[Any]:
        """List all papers."""
        return self.store.list_all("paper")

    def delete_paper(self, paper_id: str) -> bool:
        """Delete a paper."""
        return self.store.delete("paper", paper_id)

    # ------------------------------------------------------------------
    # Experiments
    # ------------------------------------------------------------------
    def save_experiment(self, experiment: Any) -> Any:
        """Save an experiment record."""
        return self.store.save("experiment", experiment)

    def get_experiment(self, experiment_id: str) -> Optional[Any]:
        """Get an experiment by ID."""
        return self.store.get("experiment", experiment_id)

    def list_experiments(self) -> List[Any]:
        """List all experiments."""
        return self.store.list_all("experiment")

    def delete_experiment(self, experiment_id: str) -> bool:
        """Delete an experiment."""
        return self.store.delete("experiment", experiment_id)

    # ------------------------------------------------------------------
    # Benchmarks
    # ------------------------------------------------------------------
    def save_benchmark(self, benchmark: Any) -> Any:
        """Save a benchmark record."""
        return self.store.save("benchmark", benchmark)

    def get_benchmark(self, benchmark_id: str) -> Optional[Any]:
        """Get a benchmark by ID."""
        return self.store.get("benchmark", benchmark_id)

    def list_benchmarks(self) -> List[Any]:
        """List all benchmarks."""
        return self.store.list_all("benchmark")

    def delete_benchmark(self, benchmark_id: str) -> bool:
        """Delete a benchmark."""
        return self.store.delete("benchmark", benchmark_id)

    # ------------------------------------------------------------------
    # Implementation Plans
    # ------------------------------------------------------------------
    def save_implementation_plan(self, plan: Any) -> Any:
        """Save an implementation plan."""
        return self.store.save("implementation_plan", plan)

    def get_implementation_plan(self, plan_id: str) -> Optional[Any]:
        """Get an implementation plan by ID."""
        return self.store.get("implementation_plan", plan_id)

    def list_implementation_plans(self) -> List[Any]:
        """List all implementation plans."""
        return self.store.list_all("implementation_plan")

    def delete_implementation_plan(self, plan_id: str) -> bool:
        """Delete an implementation plan."""
        return self.store.delete("implementation_plan", plan_id)

    # ------------------------------------------------------------------
    # History & stats
    # ------------------------------------------------------------------
    def get_record_history(self, record_type: str, record_id: str) -> List[Dict[str, Any]]:
        """Get version history for a record (SQLite backend only)."""
        if isinstance(self.store, SQLiteResearchStore):
            return self.store.get_history(record_type, record_id)
        return []

    def get_stats(self) -> Dict[str, Any]:
        return self.store.get_stats()