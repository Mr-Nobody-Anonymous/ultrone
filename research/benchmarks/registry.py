"""Benchmark registry for environment management."""
from __future__ import annotations
from typing import Dict, List, Optional
from .base import Benchmark, BenchmarkConfig

class BenchmarkRegistry:
    def __init__(self) -> None:
        self._benchmarks: Dict[str, type] = {}
    def register(self, name: str, cls: type) -> None:
        self._benchmarks[name] = cls
    def create(self, name: str, config: Optional[BenchmarkConfig] = None) -> Benchmark:
        cls = self._benchmarks.get(name)
        if cls is None:
            raise KeyError(f"Benchmark not found: {name}")
        return cls(config=config)
    def names(self) -> List[str]:
        return list(self._benchmarks.keys())
    def count(self) -> int:
        return len(self._benchmarks)
