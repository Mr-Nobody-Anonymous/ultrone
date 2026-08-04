"""UltroneOS process scheduler."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class Process:
    pid: int
    name: str
    priority: int = 0
    state: str = "ready"

class OSScheduler:
    def __init__(self) -> None:
        self._processes: List[Process] = []
        self._next_pid: int = 1
    def spawn(self, name: str, priority: int = 0) -> int:
        pid = self._next_pid
        self._next_pid += 1
        self._processes.append(Process(pid=pid, name=name, priority=priority))
        return pid
    def kill(self, pid: int) -> bool:
        before = len(self._processes)
        self._processes = [p for p in self._processes if p.pid != pid]
        return len(self._processes) < before
    def schedule(self) -> Optional[Process]:
        ready = [p for p in self._processes if p.state == "ready"]
        if not ready:
            return None
        return max(ready, key=lambda p: p.priority)
    @property
    def process_count(self) -> int:
        return len(self._processes)
