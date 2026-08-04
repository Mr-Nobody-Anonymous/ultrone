"""Hardware backend abstractions."""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

class HardwareBackend(ABC):
    name: str = "base"
    def __init__(self) -> None:
        self._available: bool = False
    @abstractmethod
    def is_available(self) -> bool: ...
    @abstractmethod
    def device_count(self) -> int: ...
    @abstractmethod
    def get_device_info(self, device_id: int = 0) -> Dict[str, str]: ...
    def allocate(self, size: int) -> Optional[bytes]:
        return bytes(size) if self.is_available() else None

class CPUBackend(HardwareBackend):
    name = "cpu"
    def is_available(self) -> bool:
        self._available = True
        return True
    def device_count(self) -> int:
        return 1
    def get_device_info(self, device_id: int = 0) -> Dict[str, str]:
        return {"name": "CPU", "type": "cpu"}

class BackendRegistry:
    def __init__(self) -> None:
        self._backends: Dict[str, HardwareBackend] = {}
        self.register("cpu", CPUBackend())
    def register(self, name: str, backend: HardwareBackend) -> None:
        self._backends[name] = backend
    def get(self, name: str) -> Optional[HardwareBackend]:
        return self._backends.get(name)
    def available(self) -> List[str]:
        return [name for name, b in self._backends.items() if b.is_available()]
    def count(self) -> int:
        return len(self._backends)
