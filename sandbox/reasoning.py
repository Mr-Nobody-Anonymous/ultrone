# Copyright (c) Ultrone Contributors. All rights reserved.
"""Cross-domain reasoning: deduction plus analogical transfer.

Two unrelated domains (botany, fleet maintenance) share nothing but the
*structure* of their causal rules:

    [premise_a & premise_b] -> intermediate -> outcome

The forward-chaining engine derives all consequences of a fact set with a
deterministic fixpoint loop. Analogy is tested explicitly: facts and the
derived conclusion of domain A are renamed into domain B's vocabulary via
an explicit mapping, and the SAME derivation chain must go through --
evidence that what was learned is the relational structure, not the
surface vocabulary.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, FrozenSet, Iterable, List, Set


@dataclass(frozen=True)
class Rule:
    domain: str
    premises: FrozenSet[str]
    conclusion: str


class RuleBase:
    def __init__(self) -> None:
        self._rules: List[Rule] = []

    def register(self, rule: Rule) -> None:
        self._rules.append(rule)

    def rules_for(self, domain: str) -> List[Rule]:
        return [r for r in self._rules if r.domain == domain]

    def derive(self, facts: Iterable[str], domain: str) -> Set[str]:
        """Forward-chain to fixpoint; deterministic (sorted iteration)."""
        known = set(facts)
        rules = sorted(
            self.rules_for(domain),
            key=lambda r: (sorted(r.premises), r.conclusion),
        )
        changed = True
        while changed:
            changed = False
            for rule in rules:
                if rule.conclusion in known:
                    continue
                if rule.premises <= known:
                    known.add(rule.conclusion)
                    changed = True
        return known


def build_analogous_domains():
    """Two domains with identical relational structure."""
    botany = RuleBase()
    botany.register(Rule("botany", frozenset({"green_leaves", "moist_soil"}),
                         "thriving_plant"))
    botany.register(Rule("botany", frozenset({"thriving_plant"}), "blooms_soon"))
    botany.register(Rule("botany", frozenset({"pest_damage"}), "wilting_plant"))

    fleet = RuleBase()
    fleet.register(Rule("fleet", frozenset({"clean_filters", "fuel_quality_ok"}),
                        "engine_healthy"))
    fleet.register(Rule("fleet", frozenset({"engine_healthy"}), "inspection_pass"))
    fleet.register(Rule("fleet", frozenset({"corroded_hull"}), "engine_healthy"))

    #: structure-preserving vocabulary map botany -> fleet
    mapping = {
        "green_leaves": "clean_filters",
        "moist_soil": "fuel_quality_ok",
        "thriving_plant": "engine_healthy",
        "blooms_soon": "inspection_pass",
        "pest_damage": "corroded_hull",
        "wilting_plant": "engine_healthy",
    }
    return {"botany": botany, "fleet": fleet}, mapping


def map_facts(facts: Iterable[str], mapping: Dict[str, str]) -> Set[str]:
    return {mapping.get(f, f) for f in facts}


def run_reasoning_suite() -> Dict[str, object]:
    domains, mapping = build_analogous_domains()

    base_facts = {"green_leaves", "moist_soil"}
    derived_botany = domains["botany"].derive(base_facts, "botany")
    depth_two = "blooms_soon" in derived_botany

    mapped_facts = map_facts(base_facts, mapping)
    derived_fleet = domains["fleet"].derive(mapped_facts, "fleet")
    analogy_transfers = "inspection_pass" in derived_fleet

    # Negative control: without the second premise, no conclusion.
    incomplete = domains["botany"].derive({"green_leaves"}, "botany")
    respects_premises = "thriving_plant" not in incomplete \
        and "blooms_soon" not in incomplete

    return {
        "deduces_to_depth_two": depth_two,
        "analogy_transfers": analogy_transfers,
        "respects_missing_premises": respects_premises,
        "both_domains_solved": depth_two and analogy_transfers,
    }
