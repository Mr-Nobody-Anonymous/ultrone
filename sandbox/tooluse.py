# Copyright (c) Ultrone Contributors. All rights reserved.
"""Autonomous tool composition over typed registries.

The agent does not hardcode tool sequences: it searches (BFS, deterministic
insertion order) for a chain of registered tools whose types lead from what
it *has* to what it *needs*, then executes the chain. Adding a new tool can
shorten or enable chains without touching agent code -- the definition of
tool use rather than scripting.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class Tool:
    name: str
    input_type: str
    output_type: str
    fn: Callable[[object], object]


class Toolbox:
    def __init__(self) -> None:
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    @property
    def tools(self) -> List[Tool]:
        return list(self._tools.values())

    def chain(
        self, start_type: str, goal_type: str, max_len: int = 4,
    ) -> Optional[List[Tool]]:
        """Shortest composition path start_type -> goal_type (BFS)."""
        if start_type == goal_type:
            return []
        frontier: List[Tuple[List[Tool], str]] = [([], start_type)]
        for _ in range(max_len):
            nxt: List[Tuple[List[Tool], str]] = []
            for path, cur in frontier:
                for tool in self.tools:          # insertion order: deterministic
                    if tool.input_type != cur:
                        continue
                    if any(t.name == tool.name for t in path):
                        continue                  # no repeated tools
                    new_path = path + [tool]
                    if tool.output_type == goal_type:
                        return new_path
                    nxt.append((new_path, tool.output_type))
            frontier = nxt
            if not frontier:
                break
        return None

    def execute(self, value: object, path: List[Tool]) -> object:
        for tool in path:
            assert tool.input_type is not None
            value = tool.fn(value)
        return value


def build_demo_toolbox() -> Toolbox:
    """Small deterministic toolbox for text-analysis tasks."""
    box = Toolbox()

    def tokenize(text: str) -> list:
        return text.lower().split()

    def drop_stopwords(tokens: list) -> list:
        stop = {"the", "a", "an", "of", "and", "to", "in"}
        return [t for t in tokens if t not in stop]

    def count(tokens: list) -> int:
        return len(tokens)

    def unique(tokens: list) -> set:
        return set(tokens)

    box.register(Tool("tokenize", "text", "tokens", tokenize))
    box.register(Tool("drop_stopwords", "tokens", "tokens", drop_stopwords))
    box.register(Tool("count_tokens", "tokens", "count", count))
    box.register(Tool("unique_tokens", "tokens", "set", unique))
    box.register(Tool("count_unique", "set", "count", len))
    return box
