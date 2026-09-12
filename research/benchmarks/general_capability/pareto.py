# Copyright (c) Ultrone Contributors. All rights reserved.
"""Pareto archive: elites as a frontier, not a scalar ranking.

A candidate joins the frontier if it is NOT dominated -- i.e. no
existing member is >= on every objective and > on at least one.
This preserves tradeoff points like:

    A: reasoning 0.92, memory 0.71, latency 20ms   <- capability elite
    B: reasoning 0.88, memory 0.91, latency 12ms   <- balanced elite

Both are useful; single-scalar selection would discard one of them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from self_improvement.lab.evaluator import CapabilitySnapshot

__all__ = ["ParetoArchive"]


def _objective_values(snapshot: CapabilitySnapshot) -> Dict[str, float]:
    return {
        **{f"cap:{d}": v for d, v in sorted(snapshot.capabilities.items())},
        "efficiency": snapshot.efficiency,
        "resource:latency": -snapshot.resource.get("latency_proxy", 0.0),
        "resource:parameters": -snapshot.resource["parameter_count"],
    }


@dataclass
class ParetoArchive:
    """Frontier of non-dominated candidates across named objectives."""

    max_size: int = 32
    members: List[CapabilitySnapshot] = field(default_factory=list)
    evictions: List[str] = field(default_factory=list)   # audit trail

    @staticmethod
    def dominates(a: CapabilitySnapshot, b: CapabilitySnapshot) -> bool:
        """True if a >= b on every objective and > on at least one."""
        va, vb = _objective_values(a), _objective_values(b)
        geq = all(va[k] >= vb[k] for k in va)
        gt = any(va[k] > vb[k] + 1e-9 for k in va)
        return geq and gt

    def consider(self, snapshot: CapabilitySnapshot) -> str:
        """Add if non-dominated; returns 'added'|'dominated'."""
        if any(self.dominates(m, snapshot) for m in self.members):
            return "dominated"
        # Remove members the newcomer dominates (frontier stays minimal).
        kept: List[CapabilitySnapshot] = []
        for m in self.members:
            if self.dominates(snapshot, m):
                self.evictions.append(m.candidate_id)
            else:
                kept.append(m)
        kept.append(snapshot)
        self.members = sorted(kept,
                              key=lambda s: s.candidate_id)[-self.max_size:]
        return "added"

    def front_by(self, key: str) -> Optional[CapabilitySnapshot]:
        """The frontier member best on one objective (for reporting)."""
        best = None
        best_v = None
        for s in self.members:
            v = _objective_values(s).get(key)
            if v is not None and (best_v is None or v > best_v):
                best, best_v = s, v
        return best

    def summary(self) -> Dict[str, Any]:
        return {
            "frontier_size": len(self.members),
            "candidates": [m.candidate_id for m in self.members],
            "evicted": list(self.evictions),
        }
