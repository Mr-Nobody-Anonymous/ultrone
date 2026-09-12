# Copyright (c) Ultrone Contributors. All rights reserved.
"""Interchangeable model catalog for routing.

A *model* here is any capability source ULTRONE may route a task to --
an LLM endpoint, a local weights-only build, a specialized reasoner.
What matters for orchestration is not who hosts it but what it is
*demonstrably good at* (:data:`ModelSpec.strengths`), what it costs,
how fast it answers, how much context it holds, and whether it may
touch private material.

This deliberately complements -- not duplicates -- the existing
registries elsewhere in the repo (``brain/models/registry.py``,
``frontier/model/model_registry.py``, ``mlops/``, ``training_platform``
), which manage artifact lifecycle/versioning. This one exists purely
so the router can choose among candidates per task and the optimizer
can learn that choice; swapping a simulated spec for a live provider
later requires no changes above this seam.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Mapping

#: Capability dimensions every ModelSpec is scored on. Keep this closed
#: and small: the routing objective blends exactly these weights.
DIMENSIONS = ("reasoning", "coding", "retrieval", "tool_use")


@dataclass(frozen=True)
class ModelSpec:
    """One routable inference backend."""

    name: str
    capabilities: frozenset             # {"fast","coding","reasoning",...}
    context_window: int                 # tokens
    cost_per_call: float                # abstract credits
    latency_ms: float                   # abstract milliseconds
    strengths: Dict[str, float] = field(default_factory=dict)
    local_only: bool = False            # True -> handles private tasks

    def __post_init__(self) -> None:
        missing = [d for d in DIMENSIONS if d not in self.strengths]
        if missing:
            raise ValueError(
                f"model '{self.name}' missing strength dims: {missing}")
        for dim, value in self.strengths.items():
            if dim not in DIMENSIONS:
                raise ValueError(f"unknown dimension '{dim}'")
            if not 0.0 <= value <= 1.0:
                raise ValueError(
                    f"strength {dim}={value} outside [0, 1]")
        if self.context_window <= 0 or self.cost_per_call < 0 \
                or self.latency_ms <= 0:
            raise ValueError(f"invalid physical spec for "
                             f"'{self.name}'")

    def has_capability(self, capability: str) -> bool:
        return capability in self.capabilities


class ModelRegistry:
    """Authoritative store of routable models (no silent overwrite)."""

    def __init__(self) -> None:
        self._models: Dict[str, ModelSpec] = {}

    def register(self, spec: ModelSpec) -> ModelSpec:
        if spec.name in self._models:
            raise ValueError(f"model '{spec.name}' already registered")
        self._models[spec.name] = spec
        return spec

    def get(self, name: str) -> ModelSpec:
        return self._models[name]

    def has(self, name: str) -> bool:
        return name in self._models

    def names(self) -> List[str]:
        return sorted(self._models)

    def models_with(self, capability: str) -> List[ModelSpec]:
        return [m for m in (self._models[n] for n in sorted(self._models))
                if m.has_capability(capability)]

    def fitting_context(self, tokens_needed: int) -> List[ModelSpec]:
        return [m for m in (self._models[n] for n in sorted(self._models))
                if m.context_window >= tokens_needed]


def default_model_registry() -> ModelRegistry:
    """Built-in research catalog.

    Hand-tuned tradeoffs so no single tier dominates: ``nano`` wins on
    price/latency only, ``reasoner`` on reasoning only, ``longctx`` on
    window only, etc. Real deployments register provider-backed specs
    with measured values instead.
    """
    registry = ModelRegistry()

    def add(name, caps, ctx, cost, lat, strengths, local=False):
        registry.register(ModelSpec(
            name=name, capabilities=frozenset(caps),
            context_window=ctx, cost_per_call=cost, latency_ms=lat,
            strengths={
                dim: value for dim, value in zip(DIMENSIONS, strengths)},
            local_only=local))

    add("nano", ("fast",), 16_000, 0.05, 120,
        (0.35, 0.40, 0.45, 0.30))
    add("balanced", ("standard", "coding", "reasoning"),
        48_000, 0.30, 400, (0.62, 0.58, 0.60, 0.55))
    add("coder", ("coding", "tool_use"), 64_000, 0.45, 520,
        (0.55, 0.95, 0.50, 0.70))
    add("reasoner", ("reasoning", "long_context"), 128_000, 1.80, 1400,
        (0.95, 0.72, 0.65, 0.75))
    add("longctx", ("long_context",), 256_000, 1.20, 900,
        (0.66, 0.55, 0.92, 0.45))
    add("local-7b", ("local", "fast"), 32_000, 0.0, 650,
        (0.52, 0.50, 0.58, 0.40), local=True)
    add("local-70b", ("local", "coding"), 64_000, 0.15, 1100,
        (0.74, 0.65, 0.72, 0.55), local=True)
    return registry