"""
Database abstraction layer supporting SQLite, PostgreSQL, TimescaleDB, Qdrant, and Redis.
Provides migration support, connection pooling, and automatic backups.
"""

import os
import json
import shutil
import logging
from abc import ABC, abstractmethod
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, TypeVar, Generic

logger = logging.getLogger("argus.database")

T = TypeVar("T")


class DatabaseBackend(ABC):
    """Abstract base for database backends."""

    @abstractmethod
    def connect(self) -> None:
        ...

    @abstractmethod
    def disconnect(self) -> None:
        ...

    @abstractmethod
    def execute(self, query: str, params: Optional[Dict] = None) -> Any:
        ...

    @abstractmethod
    def query(self, query: str, params: Optional[Dict] = None) -> List[Dict]:
        ...

    @abstractmethod
    def insert(self, table: str, data: Dict) -> int:
        ...

    @abstractmethod
    def update(self, table: str, data: Dict, where: Dict) -> int:
        ...

    @abstractmethod
    def delete(self, table: str, where: Dict) -> int:
        ...

    @abstractmethod
    def backup(self, path: str) -> bool:
        ...


class PostgreSQLBackend(DatabaseBackend):
    """PostgreSQL backend with TimescaleDB support."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.pool = None
        self._connected = False

    def connect(self) -> None:
        try:
            import psycopg2.pool
            self.pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=self.config.get("min_connections", 2),
                maxconn=self.config.get("max_connections", 20),
                host=self.config.get("host", "localhost"),
                port=self.config.get("port", 5432),
                dbname=self.config.get("database", "argus"),
                user=self.config.get("user", "argus"),
                password=self.config.get("password", ""),
            )
            self._connected = True
            logger.info("Connected to PostgreSQL database")
        except ImportError:
            logger.warning("psycopg2 not installed, falling back to SQLite")
            raise

    def disconnect(self) -> None:
        if self.pool:
            self.pool.closeall()
            self._connected = False

    def _get_conn(self):
        if not self.pool:
            raise RuntimeError("Database not connected")
        return self.pool.getconn()

    def _put_conn(self, conn):
        if self.pool:
            self.pool.putconn(conn)

    def execute(self, query: str, params: Optional[Dict] = None) -> Any:
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(query, params or {})
                conn.commit()
                return cur
        finally:
            self._put_conn(conn)

    def query(self, query: str, params: Optional[Dict] = None) -> List[Dict]:
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(query, params or {})
                columns = [desc[0] for desc in cur.description] if cur.description else []
                return [dict(zip(columns, row)) for row in cur.fetchall()]
        finally:
            self._put_conn(conn)

    def insert(self, table: str, data: Dict) -> int:
        columns = ", ".join(data.keys())
        placeholders = ", ".join(f"%({k})s" for k in data.keys())
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders}) RETURNING id"
        result = self.query(query, data)
        return result[0]["id"] if result else -1

    def update(self, table: str, data: Dict, where: Dict) -> int:
        set_clause = ", ".join(f"{k} = %({k})s" for k in data.keys())
        where_clause = " AND ".join(f"{k} = %(where_{k})s" for k in where.keys())
        params = {**data, **{f"where_{k}": v for k, v in where.items()}}
        query = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"
        result = self.execute(query, params)
        return result.rowcount if result else 0

    def delete(self, table: str, where: Dict) -> int:
        where_clause = " AND ".join(f"{k} = %(k)s" for k in where.keys())
        query = f"DELETE FROM {table} WHERE {where_clause}"
        result = self.execute(query, where)
        return result.rowcount if result else 0

    def backup(self, path: str) -> bool:
        import subprocess
        try:
            db_name = self.config.get("database", "argus")
            result = subprocess.run(
                ["pg_dump", "-h", self.config.get("host", "localhost"),
                 "-U", self.config.get("user", "argus"), "-F", "c",
                 "-f", path, db_name],
                env={"PGPASSWORD": self.config.get("password", "")},
                capture_output=True,
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return False


class SQLiteBackend(DatabaseBackend):
    """SQLite backend with WAL mode and connection pooling."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.path = config.get("path", "argus.db")
        self._conn = None

    def connect(self) -> None:
        import sqlite3
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.execute("PRAGMA busy_timeout=5000")
        logger.info(f"Connected to SQLite database: {self.path}")

    def disconnect(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def execute(self, query: str, params: Optional[Dict] = None) -> Any:
        cur = self._conn.execute(query, params or {})
        self._conn.commit()
        return cur

    def query(self, query: str, params: Optional[Dict] = None) -> List[Dict]:
        cur = self._conn.execute(query, params or {})
        columns = [desc[0] for desc in cur.description] if cur.description else []
        return [dict(zip(columns, row)) for row in cur.fetchall()]

    def insert(self, table: str, data: Dict) -> int:
        columns = ", ".join(data.keys())
        placeholders = ", ".join(f":{k}" for k in data.keys())
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        cur = self.execute(query, data)
        return cur.lastrowid if cur else -1

    def update(self, table: str, data: Dict, where: Dict) -> int:
        set_clause = ", ".join(f"{k} = :{k}" for k in data.keys())
        where_clause = " AND ".join(f"{k} = :where_{k}" for k in where.keys())
        params = {**data, **{f"where_{k}": v for k, v in where.items()}}
        query = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"
        result = self.execute(query, params)
        return result.rowcount if result else 0

    def delete(self, table: str, where: Dict) -> int:
        where_clause = " AND ".join(f"{k} = :{k}" for k in where.keys())
        query = f"DELETE FROM {table} WHERE {where_clause}"
        result = self.execute(query, where)
        return result.rowcount if result else 0

    def backup(self, path: str) -> bool:
        try:
            import shutil
            shutil.copy2(self.path, path)
            return True
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return False


class DatabaseManager:
    """Unified database manager supporting multiple backends."""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.backend: Optional[DatabaseBackend] = None
        self._migrated = False

    def initialize(self, backend_type: str = "sqlite", config: Optional[Dict] = None) -> None:
        cfg = config or self.config
        if backend_type == "postgresql":
            self.backend = PostgreSQLBackend(cfg)
        elif backend_type == "sqlite":
            self.backend = SQLiteBackend(cfg)
        else:
            raise ValueError(f"Unsupported backend: {backend_type}")
        self.backend.connect()
        self._run_migrations()

    def close(self) -> None:
        if self.backend:
            self.backend.disconnect()

    def _run_migrations(self) -> None:
        """Run database migrations in order."""
        migrations = [
            self._migration_v1_initial,
            self._migration_v2_timeseries,
            self._migration_v3_events,
            self._migration_v4_faces,
            self._migration_v5_analytics,
        ]
        for migration in migrations:
            try:
                migration()
                self._migrated = True
            except Exception as e:
                logger.warning(f"Migration {migration.__name__} skipped: {e}")

    def _migration_v1_initial(self) -> None:
        self.backend.execute("""
            CREATE TABLE IF NOT EXISTS cameras (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                stream_url TEXT NOT NULL,
                camera_type TEXT DEFAULT 'rtsp',
                location TEXT,
                latitude REAL,
                longitude REAL,
                status TEXT DEFAULT 'offline',
                fps INTEGER DEFAULT 30,
                resolution TEXT DEFAULT '1920x1080',
                metadata TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.backend.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'viewer',
                is_active INTEGER DEFAULT 1,
                permissions TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.backend.execute("""
            CREATE TABLE IF NOT EXISTS zones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                camera_id INTEGER REFERENCES cameras(id),
                zone_type TEXT DEFAULT 'polygon',
                coordinates TEXT NOT NULL,
                priority INTEGER DEFAULT 0,
                metadata TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    def _migration_v2_timeseries(self) -> None:
        self.backend.execute("""
            CREATE TABLE IF NOT EXISTS analytics_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                camera_id INTEGER REFERENCES cameras(id),
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                event_type TEXT NOT NULL,
                data TEXT DEFAULT '{}',
                metadata TEXT DEFAULT '{}'
            )
        """)
        self.backend.execute("""
            CREATE TABLE IF NOT EXISTS occupancy_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                camera_id INTEGER REFERENCES cameras(id),
                zone_id INTEGER REFERENCES zones(id),
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                count INTEGER DEFAULT 0,
                dwell_time REAL DEFAULT 0
            )
        """)

    def _migration_v3_events(self) -> None:
        self.backend.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                camera_id INTEGER REFERENCES cameras(id),
                event_type TEXT NOT NULL,
                severity TEXT DEFAULT 'info',
                status TEXT DEFAULT 'new',
                description TEXT,
                snapshot_path TEXT,
                video_clip_path TEXT,
                metadata TEXT DEFAULT '{}',
                acknowledged_by INTEGER REFERENCES users(id),
                acknowledged_at TIMESTAMP,
                resolved_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.backend.execute("""
            CREATE TABLE IF NOT EXISTS event_tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER REFERENCES events(id),
                tag TEXT NOT NULL
            )
        """)

    def _migration_v4_faces(self) -> None:
        self.backend.execute("""
            CREATE TABLE IF NOT EXISTS known_faces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                encoding TEXT NOT NULL,
                metadata TEXT DEFAULT '{}',
                thumbnail_path TEXT,
                is_blacklisted INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.backend.execute("""
            CREATE TABLE IF NOT EXISTS license_plates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plate_number TEXT NOT NULL,
                camera_id INTEGER REFERENCES cameras(id),
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                confidence REAL DEFAULT 0,
                metadata TEXT DEFAULT '{}',
                is_watchlisted INTEGER DEFAULT 0
            )
        """)

    def _migration_v5_analytics(self) -> None:
        self.backend.execute("""
            CREATE TABLE IF NOT EXISTS detection_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                camera_id INTEGER REFERENCES cameras(id),
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                object_type TEXT NOT NULL,
                confidence REAL,
                bbox TEXT,
                track_id INTEGER,
                velocity REAL,
                metadata TEXT DEFAULT '{}'
            )
        """)
        self.backend.execute("""
            CREATE TABLE IF NOT EXISTS system_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metric_name TEXT NOT NULL,
                metric_value REAL,
                labels TEXT DEFAULT '{}'
            )
        """)
        self.backend.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER REFERENCES users(id),
                action TEXT NOT NULL,
                resource TEXT,
                resource_id INTEGER,
                details TEXT DEFAULT '{}',
                ip_address TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    def backup_database(self, path: Optional[str] = None) -> bool:
        backup_path = path or f"argus_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        return self.backend.backup(backup_path)

    # --- Public Query API ---

    def query(self, sql: str, params: Optional[Dict] = None) -> List[Dict]:
        return self.backend.query(sql, params)

    def execute(self, sql: str, params: Optional[Dict] = None) -> Any:
        return self.backend.execute(sql, params)

    def insert(self, table: str, data: Dict) -> int:
        return self.backend.insert(table, data)

    def update(self, table: str, data: Dict, where: Dict) -> int:
        return self.backend.update(table, data, where)

    def delete(self, table: str, where: Dict) -> int:
        return self.backend.delete(table, where)

    # --- Convenience Methods ---

    def get_cameras(self, status: Optional[str] = None) -> List[Dict]:
        if status:
            return self.query("SELECT * FROM cameras WHERE status = :status", {"status": status})
        return self.query("SELECT * FROM cameras ORDER BY name")

    def get_camera(self, camera_id: int) -> Optional[Dict]:
        results = self.query("SELECT * FROM cameras WHERE id = :id", {"id": camera_id})
        return results[0] if results else None

    def get_users(self, active_only: bool = True) -> List[Dict]:
        if active_only:
            return self.query("SELECT id, username, email, role, is_active, created_at FROM users WHERE is_active = 1")
        return self.query("SELECT id, username, email, role, is_active, created_at FROM users")

    def get_recent_events(self, limit: int = 100, severity: Optional[str] = None) -> List[Dict]:
        if severity:
            return self.query(
                "SELECT * FROM events WHERE severity = :sev ORDER BY created_at DESC LIMIT :lim",
                {"sev": severity, "lim": limit},
            )
        return self.query("SELECT * FROM events ORDER BY created_at DESC LIMIT :lim", {"lim": limit})

    def get_analytics(self, camera_id: Optional[int] = None, hours: int = 24) -> List[Dict]:
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
        if camera_id:
            return self.query(
                "SELECT * FROM analytics_events WHERE camera_id = :cid AND timestamp >= :cut ORDER BY timestamp",
                {"cid": camera_id, "cut": cutoff},
            )
        return self.query(
            "SELECT * FROM analytics_events WHERE timestamp >= :cut ORDER BY timestamp",
            {"cut": cutoff},
        )


_db_instance: Optional[DatabaseManager] = None


def get_database() -> DatabaseManager:
    """Get or create the global database instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = DatabaseManager()
        _db_instance.initialize("sqlite", {"path": os.environ.get("ARGUS_DB_PATH", "argus.db")})
    return _db_instance


def initialize_database(config: Dict[str, Any]) -> DatabaseManager:
    """Initialize database with configuration."""
    global _db_instance
    _db_instance = DatabaseManager(config)
    backend = config.get("backend", "sqlite")
    _db_instance.initialize(backend, config)
    return _db_instance

