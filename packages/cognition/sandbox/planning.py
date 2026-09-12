# Copyright (c) Ultrone Contributors. All rights reserved.
"""Domain-general task decomposition via backward chaining.

A *skill* declares preconditions and one postcondition as plain string
facts. Decomposition is means-ends backward chaining over those
declarations -- deliberately domain-blind. Transfer is then an empirical
question: the SAME decomposer must produce valid plans in unrelated domains
(kitchen vs logistics) given only their skill tables.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, FrozenSet, List, Optional


@dataclass(frozen=True)
class Skill:
    name: str
    domain: str
    requires: FrozenSet[str]
    provides: str
    cost: int = 1


class SkillRegistry:
    def __init__(self) -> None:
        self._skills: Dict[str, List[Skill]] = {}

    def register(self, skill: Skill) -> None:
        self._skills.setdefault(skill.domain, []).append(skill)

    def domain_skills(self, domain: str) -> List[Skill]:
        return list(self._skills.get(domain, ()))

    def providers(self, fact: str, domain: str) -> List[Skill]:
        provs = [s for s in self.domain_skills(domain) if s.provides == fact]
        return sorted(provs, key=lambda s: (s.cost, s.name))


def _achieve(
    registry: SkillRegistry, domain: str, fact: str,
    known: FrozenSet[str], depth: int,
) -> Optional[List[Skill]]:
    if fact in known:
        return []
    if depth <= 0:
        return None
    best: Optional[List[Skill]] = None
    for skill in registry.providers(fact, domain):
        head = _achieve_all(registry, domain, skill.requires, known, depth - 1)
        if head is None:
            continue
        candidate = head + [skill]
        if best is None or _plan_cost(candidate) < _plan_cost(best):
            best = candidate
    return best


def _achieve_all(
    registry: SkillRegistry, domain: str, goals: FrozenSet[str],
    known: FrozenSet[str], depth: int,
) -> Optional[List[Skill]]:
    plan: List[Skill] = []
    achieved = set(known)
    for goal in sorted(goals):
        sub = _achieve(registry, domain, goal, frozenset(achieved), depth)
        if sub is None:
            return None
        plan.extend(sub)
        achieved.add(goal)
    return plan


def backchain(
    registry: SkillRegistry,
    domain: str,
    goal_fact: str,
    known: FrozenSet[str] = frozenset(),
    max_depth: int = 6,
) -> Optional[List[Skill]]:
    """Return a cheapest-valid plan achieving goal_fact, or None."""
    return _achieve(registry, domain, goal_fact, known, max_depth)



def _plan_cost(plan: List[Skill]) -> int:
    return sum(s.cost for s in plan)


def build_example_domains() -> Dict[str, SkillRegistry]:
    """Two unrelated domains used by transfer evaluations."""
    kitchen = SkillRegistry()
    for s in (
        Skill("boil_water", "kitchen", frozenset({"water_in_kettle", "power"}), "boiling_water", 2),
        Skill("fill_kettle", "kitchen", frozenset(), "water_in_kettle", 1),
        Skill("plug_in", "kitchen", frozenset(), "power", 1),
        Skill("steep_leaves", "kitchen", frozenset({"boiling_water", "leaves"}), "tea", 3),
        Skill("get_leaves", "kitchen", frozenset(), "leaves", 1),
    ):
        kitchen.register(s)

    logistics = SkillRegistry()
    for s in (
        Skill("load_box", "logistics", frozenset({"box_at_dock"}), "box_in_truck", 2),
        Skill("move_box_to_dock", "logistics", frozenset({"forklift_ready"}), "box_at_dock", 1),
        Skill("check_forklift", "logistics", frozenset(), "forklift_ready", 1),
        Skill("drive_route", "logistics",
              frozenset({"box_in_truck", "route_cleared"}), "box_delivered", 4),
        Skill("clear_route", "logistics", frozenset(), "route_cleared", 2),
    ):
        logistics.register(s)
    return {"kitchen": kitchen, "logistics": logistics}
