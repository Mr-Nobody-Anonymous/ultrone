# Copyright (c) Ultrone Contributors. All rights reserved.
"""Memory strategy selection for a routed run.

ULTRONE already has durable long-term memory
(``brain.learning.experience_memory``); this module chooses *how much*
of it each task should be allowed to lean on -- from no recall at all
up through episodic buffers to tiered vector recall -- trading a known
recall benefit against real credits and latency.

Strategies declare the context level they cover. Tasks demanding more
than a strategy covers incur a shortfall penalty at scoring time (see
``orchestration.router``), so under-provisioning memory is measurable
rather than invisible.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from orchestration.task_classifier import TaskProfile


@dataclass(frozen=True)
class MemoryStrategy:
    """One memory configuration a run may operate under."""

    name: str
    coverage_until: float               # context_requirement fully served
    recall_boost: float                 # max quality contribution 0..~0.4
    cost_per_call: float
    latency_ms: float


class MemoryRegistry:
    """Small closed catalog of strategies (no silent overwrite)."""

    def __init__(self) -> None:
        self._strategies: Dict[str, MemoryStrategy] = {}

    def register(self, strategy: MemoryStrategy) -> MemoryStrategy:
        if strategy.name in self._strategies:
            raise ValueError(
                f"memory strategy '{strategy.name}' already registered")
        if not 0.0 <= strategy.coverage_until <= 1.0 \
                or strategy.recall_boost < 0.0:
            raise ValueError("invalid memory spec")
        self._strategies[strategy.name] = strategy
        return strategy

    def get(self, name: str) -> MemoryStrategy:
        return self._strategies[name]

    def names(self) -> List[str]:
        return sorted(self._strategies)


def default_memory_registry() -> MemoryRegistry:
    registry = MemoryRegistry()
    registry.register(MemoryStrategy(
        name="none", coverage_until=0.12,
        recall_boost=0.0, cost_per_call=0.0, latency_ms=0.0))
    registry.register(MemoryStrategy(
        name="episodic_buffer", coverage_until=0.55,
        recall_boost=0.18, cost_per_call=0.05, latency_ms=40))
    registry.register(MemoryStrategy(
        name="vector_recall", coverage_until=0.85,
        recall_boost=0.34, cost_per_call=0.18, latency_ms=120))
    registry.register(MemoryStrategy(
        name="tiered", coverage_until=1.0,
        recall_boost=0.38, cost_per_call=0.28, latency_ms=160))
    return registry


def select_memory(registry: MemoryRegistry, profile: TaskProfile,
                  richness_weight: float = 0.0) -> MemoryStrategy:
    """Pick the cheapest strategy that serves the actual demand.

    ``richness_weight`` multiplies *realized* recall support -- appetite
    for headroom cannot conjure value where the task has nothing to
    recall into -- so low-context tasks fall back to cheap strategies
    naturally instead of defaulting to the most expensive tier.
    """
    best = None
    best_key = None
    for name in registry.names():
        strategy = registry.get(name)
        shortfall = max(0.0, profile.context_requirement
                        - strategy.coverage_until)
        support = strategy.recall_boost * min(
            1.0, profile.context_requirement
            / max(strategy.coverage_until, 0.05))
        # Value of this strategy for THIS task: realized support plus an
        # insurance term -- richness appetite may pay for headroom the
        # task does not strictly need, but NEVER discounts shortfall.
        key = round(support * (1.0 + richness_weight)
                    + richness_weight * strategy.recall_boost
                    * (1.0 - profile.context_requirement)
                    - 10.0 * shortfall
                    - 0.001 * strategy.cost_per_call
                    - 0.0002 * strategy.latency_ms
                    * (0.25 + profile.latency_sensitivity), 6)
        if best_key is None or key > best_key:
            best, best_key = strategy, key
    assert best is not None
    return best