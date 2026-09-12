# Copyright (c) Ultrone Contributors. All rights reserved.
"""Tool catalog and per-task tool attachment.

Tools are capability sources that are *used during* a run (simulators,
code execution, retrieval). Selection is a transparent two-stage rule:
domain relevance first, then reliability-per-credit ranking, capped by
the routing policy's ``max_tools``. The simulator-side value of an
attached toolkit lives in ``orchestration.router`` so truth and policy
stay separate judgments.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from orchestration.task_classifier import TaskProfile


@dataclass(frozen=True)
class ToolSpec:
    """One invocable tool with measured operating characteristics."""

    name: str
    domains: frozenset                  # which task domains it serves
    capabilities: frozenset             # what it can do
    cost_per_call: float
    latency_ms: float
    reliability: float                  # 0..1 empirical success rate

    def __post_init__(self) -> None:
        if not 0.0 <= self.reliability <= 1.0:
            raise ValueError("reliability must be in [0, 1]")
        if self.cost_per_call < 0 or self.latency_ms <= 0:
            raise ValueError("invalid physical spec")


class ToolRegistry:
    """Authoritative store of tools (no silent overwrite)."""

    def __init__(self) -> None:
        self._tools: Dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> ToolSpec:
        if spec.name in self._tools:
            raise ValueError(f"tool '{spec.name}' already registered")
        self._tools[spec.name] = spec
        return spec

    def get(self, name: str) -> ToolSpec:
        return self._tools[name]

    def names(self) -> List[str]:
        return sorted(self._tools)


def default_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()

    def add(name, domains, caps, cost, lat, rel):
        registry.register(ToolSpec(
            name=name, domains=frozenset(domains),
            capabilities=frozenset(caps), cost_per_call=cost,
            latency_ms=lat, reliability=rel))

    add("sim-runner", ("simulation",),
        ("simulation", "sensing"), 0.20, 150, 0.93)
    add("python-exec", ("coding", "analysis"),
        ("compute",), 0.15, 80, 0.97)
    add("retriever", ("analysis", "simulation", "coding"),
        ("retrieval",), 0.10, 220, 0.90)
    add("calculator", ("analysis",),
        ("compute",), 0.02, 5, 0.99)
    add("geo-query", ("simulation",),
        ("maps", "sensing"), 0.08, 180, 0.88)
    return registry


def select_tools(registry: ToolRegistry, profile: TaskProfile,
                 max_tools: int) -> Tuple[ToolSpec, ...]:
    """Attach the most relevant tools for one profile.

    Ranking = domain match, then reliability-per-credit efficiency,
    minus a mild latency pressure scaled by the task's latency
    sensitivity. Tools irrelevant to the domain are never attached even
    when the cap allows -- a wasted call is worse than a smaller kit.
    """
    if max_tools <= 0 or profile.tool_requirement <= 0.0:
        return ()

    ranked: List[Tuple[float, str, ToolSpec]] = []
    for name in registry.names():
        tool = registry.get(name)
        if profile.domain not in tool.domains:
            continue
        score = (
            1.0                                             # relevant
            + 0.5 * tool.reliability                        # dependable
            - 0.2 * min(tool.cost_per_call / 0.25, 1.0)
            - 0.3 * min(tool.latency_ms / 300.0, 1.0)
            * (0.25 + profile.latency_sensitivity))
        ranked.append((round(score, 6), name, tool))

    ranked.sort(key=lambda item: (-item[0], item[1]))
    return tuple(t for _, _, t in ranked[:max_tools])