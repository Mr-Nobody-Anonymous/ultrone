"""DuckDB backend (in-memory fallback)."""
from __future__ import annotations
from typing import Any, Optional
from .base import ClusterBackend

class DuckDBBackend(ClusterBackend):
    name = "duckdb"
    def __init__(self, config=None) -> None:
        super().__init__(config)
        self._tables: dict = {}
    def connect(self) -> bool:
        self._connected = True
        return True
    def disconnect(self) -> None:
        self._connected = False
    def put(self, key: str, value: Any) -> bool:
        self._tables[key] = value
        return True
    def get(self, key: str) -> Optional[Any]:
        return self._tables.get(key)
    def delete(self, key: str) -> bool:
        return self._tables.pop(key, None) is not None
