"""Base classes for distributed memory backends."""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

class ClusterBackend(ABC):
    name: str = "base"
    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config = config or {}
        self._connected: bool = False
    @abstractmethod
    def connect(self) -> bool: ...
    @abstractmethod
    def disconnect(self) -> None: ...
    @abstractmethod
    def put(self, key: str, value: Any) -> bool: ...
    @abstractmethod
    def get(self, key: str) -> Optional[Any]: ...
    @abstractmethod
    def delete(self, key: str) -> bool: ...
    @property
    def is_connected(self) -> bool:
        return self._connected

class ClusterRegistry:
    def __init__(self) -> None:
        self._backends: Dict[str, type] = {}
    def register(self, name: str, cls: type) -> None:
        self._backends[name] = cls
    def create(self, name: str, config: Optional[Dict] = None) -> Optional[ClusterBackend]:
        cls = self._backends.get(name)
        return cls(config=config) if cls else None
    def names(self) -> List[str]:
        return list(self._backends.keys())
