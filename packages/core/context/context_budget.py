# Copyright (c) Ultrone Contributors. All rights reserved.
"""Context Budget allocation across agent prompt sections."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ContextBudget:
    """Token budget allocations for assembling prompt contexts."""

    total_window: int = 32000
    system_instructions: int = 2000
    goal_and_task: int = 2000
    memories: int = 4000
    skills: int = 2000
    files_and_code: int = 12000
    observations_and_tools: int = 6000
    user_prompt: int = 4000

    def adjust_for_window(self, window_size: int) -> ContextBudget:
        """Scale budget proportionally to fit target model context window."""
        ratio = window_size / self.total_window
        return ContextBudget(
            total_window=window_size,
            system_instructions=int(self.system_instructions * ratio),
            goal_and_task=int(self.goal_and_task * ratio),
            memories=int(self.memories * ratio),
            skills=int(self.skills * ratio),
            files_and_code=int(self.files_and_code * ratio),
            observations_and_tools=int(self.observations_and_tools * ratio),
            user_prompt=int(self.user_prompt * ratio),
        )
