# Copyright (c) Ultrone Contributors. All rights reserved.
"""Continual-learning benchmark: acquire tasks in sequence, then measure
what survived.

A tabular associate (symbol -> action) with bounded capacity learns a
sequence of disjoint tasks. The harness reports:

- ``eval_after_training``  -- accuracy on each task right after learning it;
- ``retention_after_all``  -- accuracy on every task AFTER the whole
  sequence (the forgetting measurement);
- whether a *small*-capacity learner forgets while a *large*-capacity one
  retains -- proving the benchmark can detect forgetting rather than being
  insensitive to it.

No gradients anywhere: capacity pressure is the forgetting mechanism, so
every number is exactly explainable and reproducible.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Hashable, List, Optional


@dataclass(frozen=True)
class AssociativeTask:
    name: str
    pairs: Dict[Hashable, Hashable]


def build_task_sequence(n_tasks: int = 4, pairs_per_task: int = 4):
    """Disjoint symbol sets (task suffix guarantees uniqueness); shared actions."""
    tasks = []
    alphabet = "abcdefgh"
    for t in range(n_tasks):
        pairs = {}
        for i in range(pairs_per_task):
            sym = f"{alphabet[i % len(alphabet)]}{t}_{i}"
            pairs[sym] = f"act_{i % 3}"
        tasks.append(AssociativeTask(f"task_{t}", pairs))
    return tasks


class TabularLearner:
    """Least-recently-updated eviction under a hard capacity bound."""

    def __init__(self, capacity: Optional[int] = None) -> None:
        self.capacity = capacity
        self._rows: Dict[Hashable, Dict[Hashable, int]] = {}

    def _touch(self, sym: Hashable) -> None:
        if sym in self._rows:
            row = self._rows.pop(sym)
            self._rows[sym] = row

    def update(self, sym: Hashable, action: Hashable) -> None:
        self._touch(sym)
        self._rows.setdefault(sym, {})
        self._rows[sym][action] = self._rows[sym].get(action, 0) + 1
        if self.capacity is not None:
            while len(self._rows) > self.capacity:
                oldest = next(iter(self._rows))
                del self._rows[oldest]

    def predict(self, sym: Hashable) -> Optional[Hashable]:
        row = self._rows.get(sym)
        if not row:
            return None
        return sorted(row.items(), key=lambda kv: (-kv[1], str(kv[0])))[0][0]

    @property
    def known_symbols(self) -> int:
        return len(self._rows)


def _evaluate(learner: TabularLearner, tasks: List[AssociativeTask]) -> List[float]:
    out = []
    for task in tasks:
        hits = sum(
            1 for s, a in task.pairs.items() if learner.predict(s) == a
        )
        out.append(round(hits / len(task.pairs), 4))
    return out


def run_continual_sequence(
    tasks: List[AssociativeTask],
    n_train_reps: int = 12,
    capacities: tuple = (None, 6),
) -> Dict[str, object]:
    report: Dict[str, object] = {"n_tasks": len(tasks)}
    per_capacity: Dict[str, object] = {}
    for cap in capacities:
        learner = TabularLearner(capacity=cap)
        after_training: List[float] = []
        for task in tasks:
            for sym, action in task.pairs.items():
                for _ in range(n_train_reps):
                    learner.update(sym, action)
            after_training.append(_evaluate(learner, [task])[0])
        retention = _evaluate(learner, tasks)
        key = "unbounded" if cap is None else f"cap_{cap}"
        per_capacity[key] = {
            "capacity": cap,
            "eval_after_training": after_training,
            "retention_after_all": retention,
            "learned_each_task": all(a == 1.0 for a in after_training),
            "retained_everything": all(r == 1.0 for r in retention),
        }
    report["learners"] = per_capacity
    bounded_key = [k for k in per_capacity if k != "unbounded"]
    if bounded_key and "unbounded" in per_capacity:
        bounded = per_capacity[bounded_key[0]]
        report["benchmark_detects_forgetting"] = (
            per_capacity["unbounded"]["retained_everything"]
            and not bounded["retained_everything"]
        )
    elif bounded_key:
        # Single-capacity run: forgetting is detectable as any early-task
        # loss relative to what was just learned.
        bounded = per_capacity[bounded_key[0]]
        report["benchmark_detects_forgetting"] = (
            not bounded["retained_everything"]
        )
    return report
