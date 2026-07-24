# Copyright (c) Ultrone Contributors. All rights reserved.
"""Curriculum learning scheduler for progressive task difficulty.

Automatically adjusts task difficulty based on agent performance,
creating an optimal learning progression.
"""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("Ultrone.Brain.Learning.RL.Curriculum")


@dataclass
class CurriculumConfig:
    """Configuration for curriculum learning."""
    initial_difficulty: float = 0.1
    max_difficulty: float = 1.0
    step_size: float = 0.05
    success_threshold: float = 0.8
    window_size: int = 20
    patience: int = 5


class TaskGenerator:
    """Generates tasks at specified difficulty levels."""

    def __init__(self, task_fn: Optional[Callable] = None):
        self.task_fn = task_fn

    def generate(self, difficulty: float, **kwargs) -> Any:
        """Generate a task at the given difficulty."""
        if self.task_fn:
            return self.task_fn(difficulty, **kwargs)
        return {"difficulty": difficulty}


class CurriculumLearning:
    """Curriculum learning scheduler.

    Adjusts task difficulty based on rolling success rate.
    Difficulty increases when performance exceeds threshold.
    """

    def __init__(self, config: Optional[CurriculumConfig] = None):
        self.config = config or CurriculumConfig()
        self._difficulty = self.config.initial_difficulty
        self._recent_successes: List[bool] = []
        self._stagnation_counter = 0

    @property
    def difficulty(self) -> float:
        return self._difficulty

    def record_outcome(self, success: bool) -> None:
        """Record whether the agent succeeded at the current difficulty."""
        self._recent_successes.append(success)
        if len(self._recent_successes) > self.config.window_size:
            self._recent_successes.pop(0)

    def step(self) -> float:
        """Update difficulty based on recent performance."""
        if len(self._recent_successes) < self.config.window_size:
            return self._difficulty

        success_rate = sum(self._recent_successes) / len(self._recent_successes)

        if success_rate >= self.config.success_threshold:
            self._stagnation_counter += 1
            if self._stagnation_counter >= self.config.patience:
                self._difficulty = min(
                    self.config.max_difficulty,
                    self._difficulty + self.config.step_size,
                )
                self._stagnation_counter = 0
                logger.info("Curriculum: difficulty increased to %.2f", self._difficulty)
        else:
            self._stagnation_counter = max(0, self._stagnation_counter - 1)

        return self._difficulty

    def get_stats(self) -> Dict[str, Any]:
        return {
            "current_difficulty": self._difficulty,
            "recent_successes": len(self._recent_successes),
            "stagnation_counter": self._stagnation_counter,
        }