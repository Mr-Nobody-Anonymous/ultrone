"""Service registry for UltroneOS."""
from __future__ import annotations
from typing import Any, Dict, List, Optional

class ServiceRegistry:
    def __init__(self) -> None:
        self._services: Dict[str, Dict[str, Any]] = {}
    def register(self, name: str, endpoint: str, metadata: Optional[Dict] = None) -> None:
        self._services[name] = {"endpoint": endpoint, "metadata": metadata or {}, "healthy": True}
    def unregister(self, name: str) -> bool:
        return self._services.pop(name, None) is not None
    def lookup(self, name: str) -> Optional[Dict[str, Any]]:
        return self._services.get(name)
    def set_health(self, name: str, healthy: bool) -> None:
        if name in self._services:
            self._services[name]["healthy"] = healthy
    def healthy_services(self) -> List[str]:
        return [n for n, s in self._services.items() if s["healthy"]]
    @property
    def count(self) -> int:
        return len(self._services)
