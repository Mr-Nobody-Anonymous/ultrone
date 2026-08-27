# Copyright (c) Ultrone Contributors. All rights reserved.
"""Curriculum: what should ULTRONE learn next.

A curriculum is a ladder of levels. A level graduates only when its
mean utility saturates -- average at or above the level's threshold
for a required number of consecutive batches. Until then the system
stays on that level and practices it (deterministic instances change
each batch, so saturation is real competence, not memorization).
When the final level saturates, the curriculum reports exhausted.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from orchestration.task_classifier import TaskProfile

from self_improvement.self_training.task_generator import (
    LevelSpec,
    default_curriculum,
)


@dataclass
class LevelProgress:
    name: str
    index: int
    completed: bool = False
    last_mean: float = 0.0
    consecutive_good: int = 0


@dataclass
class CurriculumStep:
    """Outcome of recording one batch against the current level."""

    level_name: str
    mean_utility: float
    advanced: bool
    completed_all: bool
    streak: int

    def to_dict(self) -> Dict[str, object]:
        return dict(self.__dict__)


class CurriculumManager:
    """Deterministic level ladder with saturation-based advancement."""

    def __init__(self,
                 levels: Optional[List[LevelSpec]] = None) -> None:
        self.levels = levels or default_curriculum()
        if not self.levels:
            raise ValueError("curriculum must have at least one level")
        self._index = 0
        self._streaks = {level.name: 0 for level in self.levels}
        self._history: List[CurriculumStep] = []

    # -- state ----------------------------------------------------------- #
    @property
    def current_level(self) -> LevelSpec:
        return self.levels[self._index]

    @property
    def completed(self) -> bool:
        return self._index >= len(self.levels)

    def progress(self) -> List[Dict[str, object]]:
        return [
            {"name": level.name,
             "index": index,
             "active": index == self._index,
             "streak": self._streaks[level.name],
             "completed": index < self._index}
            for index, level in enumerate(self.levels)]

    def tasks(self, batch: int) -> List[TaskProfile]:
        """Draw 'batch' deterministic instances of the current level."""
        level = self.current_level
        count = min(batch, level.num_tasks)
        seq = len(self._history) + 1
        return [level.sample(i, prefix=f"cur-{seq}")
                for i in range(count)]

    def record(self, mean_utility: float) -> CurriculumStep:
        """Feed one batch's mean utility back into the ladder."""
        if self.completed:
            raise RuntimeError("curriculum already complete")
        level = self.current_level
        good = mean_utility >= level.saturation_mean
        self._streaks[level.name] = (self._streaks[level.name] + 1) \
            if good else 0
        advanced = False
        if self._streaks[level.name] >= level.required_streaks \
                and not self.completed:
            self._index += 1
            advanced = True
        step = CurriculumStep(
            level_name=level.name,
            mean_utility=round(float(mean_utility), 6),
            advanced=advanced,
            completed_all=self.completed,
            streak=self._streaks[level.name])
        self._history.append(step)
        return step