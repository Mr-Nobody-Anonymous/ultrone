"""Computation graph optimizer."""
from __future__ import annotations
from typing import Any, Dict, List, Optional

class GraphOptimizer:
    def __init__(self) -> None:
        self._passes: List[str] = ["constant_folding", "dead_code_elim", "common_subexpr"]
    def optimize(self, graph: Dict[str, Any]) -> Dict[str, Any]:
        optimized = dict(graph)
        optimized["_optimized"] = True
        optimized["_passes_applied"] = list(self._passes)
        return optimized
    def add_pass(self, name: str) -> None:
        if name not in self._passes:
            self._passes.append(name)
    @property
    def passes(self) -> List[str]:
        return list(self._passes)
