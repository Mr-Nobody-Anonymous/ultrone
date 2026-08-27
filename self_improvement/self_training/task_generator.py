# Copyright (c) Ultrone Contributors. All rights reserved.
"""Task generation for the self-training curriculum.

A ``CurriculumLevel`` declares a band of task demands; the
``TaskGenerator`` materializes deterministic instances inside that
band. Generation is seeded -- identical levels produce identical task
families forever -- so every downstream stage (execution, selection,
dataset hashing, evaluation) inherits reproducibility for free.

The five default levels follow the intended competence ladder:

1. basic planning            -- low difficulty, no tools
2. resource constraints      -- cost/latency-sensitive
3. multiple objectives       -- tools + deeper reasoning
4. fault recovery            -- long-context with shortfalls
5. unseen environments       -- mixed hard regimes, private tasks
"""

from __future__ import annotations

import random
import zlib
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from orchestration.task_classifier import DOMAINS, TaskProfile


@dataclass(frozen=True)
class LevelSpec:
    """One curriculum band: demands ranges + instance count."""

    name: str
    description: str = ""
    difficulty: Tuple[float, float] = (0.05, 0.45)
    reasoning_depth: Tuple[float, float] = (0.05, 0.40)
    context_requirement: Tuple[float, float] = (0.02, 0.35)
    tool_probability: float = 0.0
    tool_requirement: Tuple[float, float] = (0.2, 0.9)
    privacy_probability: float = 0.0
    latency_sensitivity: Tuple[float, float] = (0.0, 0.5)
    num_tasks: int = 12
    saturation_mean: float = 0.75     # mean utility to graduate
    required_streaks: int = 2         # consecutive passing batches
    domains: Tuple[str, ...] = DOMAINS

    def sample(self, index: int, *, prefix: str,
               seed: Optional[int] = None) -> TaskProfile:
        """Deterministically draw one instance inside the band."""
        # Stable 32-bit seed: crc32, NOT builtin hash() -- str hashing
        # is salted per process (PYTHONHASHSEED) and would silently
        # break cross-process reproducibility. When no explicit seed is
        # given, vary by index so sibling instances differ.
        stable = (zlib.crc32(f"{prefix}:{self.name}".encode()) & 0xFFFFFFFF)
        if seed is None:
            rng = random.Random((stable + index * 1000003) & 0xFFFFFFFF)
        else:
            rng = random.Random(seed + index)
        lo_d, hi_d = self.difficulty
        lo_r, hi_r = self.reasoning_depth
        lo_c, hi_c = self.context_requirement
        lo_l, hi_l = self.latency_sensitivity
        return TaskProfile(
            domain=rng.choice(self.domains),
            difficulty=round(rng.uniform(lo_d, hi_d), 4),
            reasoning_depth=round(rng.uniform(lo_r, hi_r), 4),
            context_requirement=round(rng.uniform(lo_c, hi_c), 4),
            tool_requirement=(round(rng.uniform(*self.tool_requirement), 4)
                              if rng.random() < self.tool_probability
                              else 0.0),
            latency_sensitivity=round(rng.uniform(lo_l, hi_l), 4),
            privacy_required=rng.random() < self.privacy_probability,
            task_id=f"{prefix}-{index:04d}",
            source_summary=f"curriculum:{self.name}",
        )


def default_curriculum() -> List[LevelSpec]:
    """The five-rung ladder, easy exploration to hostile transfer."""
    return [
        LevelSpec(
            name="basic_planning",
            description="short low-stakes reasoning",
            difficulty=(0.05, 0.35), reasoning_depth=(0.05, 0.30),
            tool_probability=0.0, num_tasks=10),
        LevelSpec(
            name="resource_constraints",
            description="cost/latency pressure shapes routes",
            difficulty=(0.20, 0.50), reasoning_depth=(0.10, 0.45),
            latency_sensitivity=(0.4, 0.9), num_tasks=10),
        LevelSpec(
            name="multiple_objectives",
            description="tools plus deeper reasoning chains",
            difficulty=(0.40, 0.70), reasoning_depth=(0.45, 0.80),
            tool_probability=0.85, num_tasks=10),
        LevelSpec(
            name="fault_recovery",
            description="context stress and shortfall penalties",
            difficulty=(0.55, 0.85), reasoning_depth=(0.55, 0.90),
            context_requirement=(0.60, 0.98), num_tasks=10),
        LevelSpec(
            name="unseen_environments",
            description="mixed hard regimes including private work",
            difficulty=(0.65, 0.95), reasoning_depth=(0.60, 0.95),
            context_requirement=(0.30, 0.95), tool_probability=0.6,
            privacy_probability=0.25, num_tasks=10),
    ]
