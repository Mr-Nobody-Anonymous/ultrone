# Copyright (c) Ultrone Contributors. All rights reserved.
"""Cost and latency accounting for routing decisions.

Two jobs: (1) price a candidate route *before* running it so selection
can trade quality against budget; (2) accumulate what was actually
spent across attempts -- including retries after validation failure --
so fallback-heavy policies pay visibly for their resilience. The
weights here are ordinary registry parameters, i.e. things the
AdaptiveOptimizer is allowed to have opinions about.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Tuple

#: Normalization ceilings: costs/latencies near these saturate to 1.0
#: in utility terms, keeping any single model from dominating linearly.
_COST_CEILING_CREDITS = 2.5
_LATENCY_CEILING_MS = 1500.0


@dataclass(frozen=True)
class CostEstimate:
    """Priced resources of one candidate (or accumulated) decision."""

    credits: float
    latency_ms: float

    @property
    def normalized_cost(self) -> float:
        return min(self.credits / _COST_CEILING_CREDITS, 1.0)

    @property
    def normalized_latency(self) -> float:
        return min(self.latency_ms / _LATENCY_CEILING_MS, 1.0)


@dataclass(frozen=True)
class CostPolicy:
    """Preference weights over spend vs speed (registry-driven)."""

    cost_weight: float = 0.5            # 0..2 — how much we hate credits
    latency_weight: float = 0.4         # 0..2 — how much we hate waiting
    budget_cap_credits: float = 6.0     # per-run hard ceiling

    def estimate(self, *prices: CostEstimate) -> CostEstimate:
        credits = sum(p.credits for p in prices)
        latency = sum(p.latency_ms for p in prices)
        return CostEstimate(credits=round(credits, 6),
                            latency_ms=float(latency))

    def penalty(self, estimate: CostEstimate,
                latency_sensitivity: float) -> float:
        """Utility units this spend pattern should give up."""
        return round(
            self.cost_weight * estimate.normalized_cost
            + self.latency_weight * estimate.normalized_latency
            * (0.25 + 0.75 * latency_sensitivity), 6)

    def within_budget(self, estimate: CostEstimate) -> bool:
        return estimate.credits <= self.budget_cap_credits


def price_items(costs: Iterable[Tuple[float, float]]) -> CostEstimate:
    """Fold (cost, latency) pairs into one aggregate estimate."""
    credits = 0.0
    latency = 0.0
    for c, l in costs:
        credits += c
        latency += l
    return CostEstimate(credits=round(credits, 6), latency_ms=float(latency))