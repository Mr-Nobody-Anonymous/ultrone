# Copyright (c) Ultrone Contributors. All rights reserved.
"""Long-horizon memory and goal management.

Two cooperating structures:

- :class:`EpisodicMemory` -- salience-weighted episodes with recency decay;
  retrieval is a transparent, deterministic score (no hidden state), so
  forgetting is inspectable rather than mysterious.
- :class:`GoalStack` -- explicit goal lifecycle (ACTIVE / SUSPENDED /
  DONE / STALLED) so long-horizon drift becomes detectable instead of
  silent.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Set

_MEMORY_TAU = 40.0  # recency decay constant (ticks)


@dataclass
class MemoryItem:
    key: str
    content: str
    tags: Set[str]
    salience: float
    created_tick: int
    last_access_tick: int


class EpisodicMemory:
    def __init__(self, tau: float = _MEMORY_TAU) -> None:
        self._items: Dict[str, MemoryItem] = {}
        self.tau = tau

    def remember(
        self, key: str, content: str, tags: Iterable[str] = (),
        salience: float = 1.0, tick: int = 0,
    ) -> MemoryItem:
        item = MemoryItem(
            key=key, content=content, tags=set(tags),
            salience=float(salience), created_tick=tick, last_access_tick=tick,
        )
        self._items[key] = item
        return item

    def recall(
        self, keywords: Iterable[str] = (), tags: Iterable[str] = (),
        tick: int = 0, k: int = 3,
    ) -> List[MemoryItem]:
        """Top-k items by keyword overlap + tag overlap + salience + recency."""
        words = {w.lower() for w in keywords}
        wanted = set(tags)
        scored: List[tuple] = []
        for item in self._items.values():
            text_overlap = sum(
                1 for w in words if w in item.content.lower()
            )
            tag_overlap = len(wanted & item.tags)
            age = max(0, tick - item.last_access_tick)
            recency = math.exp(-age / self.tau)
            score = (
                2.0 * text_overlap + 1.5 * tag_overlap
                + item.salience + recency
            )
            scored.append((score, item.key, item))
        scored.sort(key=lambda t: (-t[0], t[1]))
        top = [item for _, _, item in scored[:k]]
        for item in top:
            item.last_access_tick = tick  # recall refreshes recency
        return top

    def __len__(self) -> int:
        return len(self._items)


GOAL_ACTIVE = "ACTIVE"
GOAL_SUSPENDED = "SUSPENDED"
GOAL_DONE = "DONE"
GOAL_STALLED = "STALLED"


@dataclass
class Goal:
    goal_id: str
    description: str
    status: str = GOAL_ACTIVE
    created_tick: int = 0
    deadline_tick: Optional[int] = None
    parent: Optional[str] = None


class GoalStack:
    """Explicit goal lifecycle with stall detection."""

    def __init__(self) -> None:
        self.goals: Dict[str, Goal] = {}
        self._order: List[str] = []

    def push(
        self, goal_id: str, description: str, tick: int = 0,
        deadline_tick: Optional[int] = None, parent: Optional[str] = None,
    ) -> Goal:
        goal = Goal(
            goal_id=goal_id, description=description, created_tick=tick,
            deadline_tick=deadline_tick, parent=parent,
        )
        self.goals[goal_id] = goal
        self._order.append(goal_id)
        return goal

    def complete(self, goal_id: str, tick: int = 0) -> Goal:
        goal = self.goals[goal_id]
        assert goal.status == GOAL_ACTIVE, f"{goal_id} is {goal.status}, not ACTIVE"
        goal.status = GOAL_DONE
        return goal

    def suspend(self, goal_id: str) -> Goal:
        goal = self.goals[goal_id]
        goal.status = GOAL_SUSPENDED
        return goal

    def resume(self, goal_id: str) -> Goal:
        goal = self.goals[goal_id]
        assert goal.status == GOAL_SUSPENDED
        goal.status = GOAL_ACTIVE
        return goal

    def sweep(self, tick: int) -> List[Goal]:
        """Flag ACTIVE goals past their deadline as STALLED."""
        stalled: List[Goal] = []
        for gid in self._order:
            g = self.goals[gid]
            if (
                g.status == GOAL_ACTIVE and g.deadline_tick is not None
                and tick > g.deadline_tick
            ):
                g.status = GOAL_STALLED
                stalled.append(g)
        return stalled

    @property
    def active(self) -> List[Goal]:
        return [self.goals[g] for g in self._order
                if self.goals[g].status == GOAL_ACTIVE]
