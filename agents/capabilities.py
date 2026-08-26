# Copyright (c) Ultrone Contributors. All rights reserved.
"""Hierarchical capability model.

Leaf capabilities live under six branches (mobility / sensing / power /
communication / maintenance / mission). Platforms advertise LEAF strings;
the model validates them against the canonical tree and can report the
full pruned hierarchy via ``available()`` -- so higher-level AI reasons
over structure ("this platform has altitude control") instead of flags.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, Set

CAPABILITY_TREE: Dict[str, Tuple[str, ...]] = {
    "mobility": ("translation", "rotation", "altitude", "depth",
                 "orbital_motion"),
    "sensing": ("visual", "thermal", "acoustic", "navigation_sensors",
                "simulated_electromagnetic"),
    "power": ("generation", "storage", "distribution"),
    "communication": ("transmit", "receive", "routing"),
    "maintenance": ("diagnostics", "faults", "repair"),
    "mission": ("navigation", "observation", "task_execution"),
}

_ALL_LEAVES: Set[str] = {leaf for leaves in CAPABILITY_TREE.values()
                         for leaf in leaves}


def validate_leaves(leaves: Iterable[str]) -> Set[str]:
    unknown = set(leaves) - _ALL_LEAVES
    if unknown:
        raise ValueError(f"unknown capability leaves: {sorted(unknown)}")
    return set(leaves)


class HierarchicalCapabilitySet:
    """A platform's advertised leaf capabilities, tree-validated."""

    def __init__(self, leaves: Iterable[str]) -> None:
        self.leaves = validate_leaves(leaves)

    def supports(self, leaf: str) -> bool:
        return leaf in self.leaves

    def branch(self, branch_name: str) -> Set[str]:
        return {leaf for leaf in self.leaves
                if leaf in CAPABILITY_TREE.get(branch_name, ())}

    def available(self) -> Dict[str, Any]:
        """Pruned capability tree: every branch with its owned leaves."""
        out: Dict[str, Any] = {}
        for branch, all_leaves in CAPABILITY_TREE.items():
            owned = [leaf for leaf in all_leaves if leaf in self.leaves]
            if owned:
                out[branch] = owned
        return out

    def covers(self, required: Iterable[str]) -> bool:
        return set(required) <= self.leaves

    def __len__(self) -> int:
        return len(self.leaves)


def combine(*sets: HierarchicalCapabilitySet) -> HierarchicalCapabilitySet:
    """Union several platforms' capabilities (team-level view)."""
    union: Set[str] = set()
    for s in sets:
        union |= s.leaves
    return HierarchicalCapabilitySet(union)
