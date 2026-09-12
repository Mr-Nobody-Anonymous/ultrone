# Copyright (c) Ultrone Contributors. All rights reserved.
"""Experience selection: traces become labeled learning signal.

Not every experience deserves to teach. The selector splits
orchestration traces into **good** (validator-accepted, judge quality
above bar), **bad** (rejected or fundamentally weak output), and
**uncertain** (everything between -- withheld from training rather
than guessed about). Only good experiences reach the dataset builder;
bad ones feed the weakness profile that steers targeted practice;
uncertain ones are counted and quarantined.

This module exists because bad experiences can teach bad behavior:
quality filtering happens HERE, deterministically, before any
training data is written.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from orchestration.traces import OrchestrationTrace

#: Quality thresholds on the simulator/adapter fidelity scale [0, 1].
GOOD_QUALITY_FLOOR = 0.55
BAD_QUALITY_CEILING = 0.30


def _result_quality(trace: OrchestrationTrace) -> float:
    """Best attempt fidelity recorded inside the trace."""
    qualities = [f.quality for f in trace.failures]
    if trace.result:
        try:
            return float(trace.result.get("quality", 0.0))
        except (TypeError, ValueError):
            pass
    return max(qualities) if qualities else 0.0


@dataclass
class SelectedExperiences:
    """Bucketed traces plus the bookkeeping needed downstream."""

    good: List[OrchestrationTrace] = field(default_factory=list)
    bad: List[OrchestrationTrace] = field(default_factory=list)
    uncertain: List[OrchestrationTrace] = field(default_factory=list)

    def counts(self) -> Dict[str, int]:
        return {"good": len(self.good), "bad": len(self.bad),
                "uncertain": len(self.uncertain)}

    def weakness_profile(self) -> Dict[str, float]:
        """Mean demand vector over FAILED work -- what to practice.

        Consumed by the dataset builder's mixture stage as the
        'targeted weaknesses' component (e.g. 10% of every batch).
        """
        if not self.bad:
            return {}
        profiles = [t.task_profile for t in self.bad]
        keys = ("difficulty", "reasoning_depth", "context_requirement",
                "tool_requirement", "latency_sensitivity")
        out: Dict[str, float] = {}
        for key in keys:
            values = [getattr(p, key) for p in profiles]
            out[key] = round(sum(values) / len(values), 4)
        domains = sorted({p.domain for p in profiles})
        out["domains"] = ",".join(domains)
        return out


class ExperienceSelector:
    """Deterministic three-way splitter over orchestration traces."""

    def __init__(self,
                 good_floor: float = GOOD_QUALITY_FLOOR,
                 bad_ceiling: float = BAD_QUALITY_CEILING) -> None:
        if not 0.0 <= bad_ceiling <= good_floor <= 1.0:
            raise ValueError(
                "require 0 <= bad_ceiling <= good_floor <= 1")
        self.good_floor = float(good_floor)
        self.bad_ceiling = float(bad_ceiling)

    def select(self, traces) -> SelectedExperiences:
        selected = SelectedExperiences()
        for trace in traces:
            quality = _result_quality(trace)
            if trace.accepted and quality >= self.good_floor:
                selected.good.append(trace)
            elif (not trace.accepted) or quality < self.bad_ceiling:
                selected.bad.append(trace)
            else:
                selected.uncertain.append(trace)
        return selected


def demand_key(profile) -> Tuple:
    """Round-trip-stable identity of a profile's demand signature."""
    return (
        profile.domain,
        round(profile.difficulty, 2),
        round(profile.reasoning_depth, 2),
        round(profile.context_requirement, 2),
        round(profile.tool_requirement, 2),
        round(profile.latency_sensitivity, 2),
        bool(profile.privacy_required),
    )
