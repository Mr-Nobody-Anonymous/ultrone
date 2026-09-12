# Copyright (c) Ultrone Contributors. All rights reserved.
"""Noncombat multi-agent cooperation: coordinated task allocation.

Agents claim tasks through a shared blackboard. In ``cooperative`` mode,
claims are honored -- no two agents duplicate work and the greedy
least-loaded assignment balances the load. In ``isolated`` mode agents
cannot see claims: they grab whatever they can, producing duplicated work
and imbalance. The gap between the two modes is the measurable value of
communication.

Fully deterministic: task order is fixed, tie-breaks are by agent id.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class Task:
    task_id: str
    required_capability: str
    load: int = 1


@dataclass
class SandboxAgent:
    agent_id: str
    capabilities: frozenset

    def can_do(self, task: Task) -> bool:
        return task.required_capability in self.capabilities


class Blackboard:
    """Shared claim space; the coordination substrate."""

    def __init__(self) -> None:
        self.claims: Dict[str, str] = {}  # task_id -> agent_id

    def claim(self, task_id: str, agent_id: str) -> bool:
        if task_id in self.claims:
            return False  # already claimed: a cooperating agent stands down
        self.claims[task_id] = agent_id
        return True


def run_cooperation_episode(
    tasks: List[Task], agents: List[SandboxAgent], mode: str = "cooperative",
) -> Dict[str, object]:
    assert mode in ("cooperative", "isolated")
    board = Blackboard() if mode == "cooperative" else None
    workloads: Dict[str, int] = {a.agent_id: 0 for a in agents}
    assignments: Dict[str, str] = {}
    duplicates = 0

    for task in sorted(tasks, key=lambda t: (-t.load, t.task_id)):
        eligible = [a for a in agents if a.can_do(task)]
        if not eligible:
            assignments[task.task_id] = "UNASSIGNED"
            continue
        # Deterministic least-loaded choice; id breaks ties.
        eligible.sort(key=lambda a: (workloads[a.agent_id], a.agent_id))
        chosen = None
        for cand in eligible:
            if board is None or board.claim(task.task_id, cand.agent_id):
                chosen = cand
                break
        if chosen is None:  # isolated-mode double-claim of claimed work
            duplicates += 1
            chosen = eligible[0]
        assignments[task.task_id] = chosen.agent_id
        workloads[chosen.agent_id] += task.load

    loads = sorted(workloads.values())
    makespan = loads[-1] if loads else 0
    mean = sum(loads) / len(loads) if loads else 0.0
    variance = sum((v - mean) ** 2 for v in loads) / len(loads) if loads else 0.0
    return {
        "mode": mode,
        "makespan": makespan,
        "workloads": dict(sorted(workloads.items())),
        "imbalance_std": round(variance ** 0.5, 6),
        "duplicate_assignments": duplicates,
        "assignments": dict(sorted(assignments.items())),
        "unassigned": sum(1 for v in assignments.values() if v == "UNASSIGNED"),
    }


def cooperation_gain(
    tasks: List[Task], agents: List[SandboxAgent],
) -> Dict[str, object]:
    iso = run_cooperation_episode(tasks, agents, mode="isolated")
    coop = run_cooperation_episode(tasks, agents, mode="cooperative")
    return {
        "isolated": iso,
        "cooperative": coop,
        "makespan_improvement": max(0, iso["makespan"] - coop["makespan"]),
        "duplicates_eliminated": max(0, iso["duplicate_assignments"]
                                     - coop["duplicate_assignments"]),
    }
