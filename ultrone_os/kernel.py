"""UltroneOS kernel."""
from __future__ import annotations
from typing import Any, Dict, List

class Kernel:
    def __init__(self) -> None:
        self._services: Dict[str, Any] = {}
        self._running: bool = False
    def register_service(self, name: str, service: Any) -> None:
        self._services[name] = service
    def get_service(self, name: str) -> Any:
        return self._services.get(name)
    def start(self) -> None:
        self._running = True
    def stop(self) -> None:
        self._running = False
    @property
    def is_running(self) -> bool:
        return self._running
    @property
    def service_names(self) -> List[str]:
        return list(self._services.keys())
