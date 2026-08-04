"""Operator fusion for computation graphs."""
from __future__ import annotations
from typing import Any, Dict, List

class OperatorFusion:
    def __init__(self) -> None:
        self._fusion_rules: Dict[str, str] = {}
    def register_rule(self, pattern: str, fused_name: str) -> None:
        self._fusion_rules[pattern] = fused_name
    def fuse(self, ops: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if len(ops) < 2:
            return ops
        fused = [ops[0]]
        for op in ops[1:]:
            prev = fused[-1]
            pattern = f"{prev.get('type','')}+{op.get('type','')}"
            if pattern in self._fusion_rules:
                fused[-1] = {"type": self._fusion_rules[pattern], "fused": True}
            else:
                fused.append(op)
        return fused
