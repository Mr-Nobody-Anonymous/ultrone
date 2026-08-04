"""Redis backend (in-memory fallback)."""
from __future__ import annotations
from typing import Any, Optional
from .base import ClusterBackend

class RedisBackend(ClusterBackend):
    name = "redis"
    def __init__(self, config=None) -> None:
        super().__init__(config)
        self._store: dict = {}
    def connect(self) -> bool:
        self._connected = True
        return True
    def disconnect(self) -> None:
        self._connected = False
        self._store.clear()
    def put(self, key: str, value: Any) -> bool:
        self._store[key] = value
        return True
    def get(self, key: str) -> Optional[Any]:
        return self._store.get(key)
    def delete(self, key: str) -> bool:
        return self._store.pop(key, None) is not None
