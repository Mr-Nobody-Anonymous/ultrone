# Copyright (c) Ultrone Contributors. All rights reserved.
"""Skill selection: composable domain boosters attached per task.

Skills differ from tools: they are *procedures* ULTRONE itself knows
(doctrine checklists, code-review passes, summarization templates)
that lift expected quality in their domain at bounded cost. The router
attaches at most ``max_skills`` of them, highest bonus first; scoring
credits exactly the bonus they advertise, so over-attachment shows up
as cost without quality -- making skill bloat learnable-away.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, FrozenSet, List, Tuple

from orchestration.task_classifier import TaskProfile


@dataclass(frozen=True)
class SkillSpec:
    """A named procedural booster scoped to specific domains."""

    name: str
    domains: FrozenSet[str]
    bonus: float                        # quality contribution when applied
    cost_per_use: float
    latency_ms: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.bonus <= 0.30:
            raise ValueError("bonus must be within [0, 0.30]")
        if self.cost_per_use < 0 or self.latency_ms <= 0:
            raise ValueError("invalid physical spec")


class SkillRegistry:
    """Authoritative store of skills (no silent overwrite)."""

    def __init__(self) -> None:
        self._skills: Dict[str, SkillSpec] = {}

    def register(self, spec: SkillSpec) -> SkillSpec:
        if spec.name in self._skills:
            raise ValueError(f"skill '{spec.name}' already registered")
        self._skills[spec.name] = spec
        return spec

    def get(self, name: str) -> SkillSpec:
        return self._skills[name]

    def names(self) -> List[str]:
        return sorted(self._skills)


def default_skill_registry() -> SkillRegistry:
    registry = SkillRegistry()
    specs = (
        ("tactics-planner", ("simulation",), 0.15, 0.06, 60),
        ("mission-logistics", ("simulation",), 0.10, 0.04, 45),
        ("code-review-pass", ("coding",), 0.18, 0.07, 70),
        ("test-first-heuristic", ("coding",), 0.12, 0.03, 35),
        ("docs-summarizer", ("analysis",), 0.14, 0.05, 55),
        ("structured-analysis", ("analysis",), 0.16, 0.08, 80),
    )
    for name, domains, bonus, cost, lat in specs:
        registry.register(SkillSpec(
            name=name, domains=frozenset(domains), bonus=bonus,
            cost_per_use=cost, latency_ms=lat))
    return registry


def select_skills(registry: SkillRegistry, profile: TaskProfile,
                  max_skills: int) -> Tuple[SkillSpec, ...]:
    """Top-bonus skills for the task's domain, capped deterministically."""
    if max_skills <= 0:
        return ()
    eligible = [registry.get(name)
                for name in registry.names()
                if profile.domain in registry.get(name).domains]
    ranked = sorted(eligible,
                    key=lambda s: (-s.bonus, s.cost_per_use, s.name))
    return tuple(ranked[:max_skills])