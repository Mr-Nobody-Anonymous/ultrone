# Copyright (c) Ultrone Contributors. All rights reserved.
"""Goal definition, parsing, and criteria validation."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .schemas import Goal

logger = logging.getLogger("Ultrone.Harness.Goal")


class GoalManager:
    """Manages goals, ensures structural validity, and parses constraints."""

    @staticmethod
    def create_goal(
        description: str,
        acceptance_criteria: Optional[List[str]] = None,
        constraints: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Goal:
        """Create and validate a new Goal specification."""
        goal = Goal(
            description=description.strip(),
            acceptance_criteria=acceptance_criteria or [],
            constraints=constraints or [],
            metadata=metadata or {},
        )
        goal.validate()
        return goal

    @staticmethod
    def parse_from_prompt(prompt: str) -> Goal:
        """Parse natural language instruction into a structured Goal."""
        lines = [line.strip() for line in prompt.splitlines() if line.strip()]
        if not lines:
            raise ValueError("Cannot construct goal from empty prompt.")

        description = lines[0]
        criteria: List[str] = []
        constraints: List[str] = []

        for line in lines[1:]:
            lower = line.lower()
            if lower.startswith(("- criteria:", "* criteria:", "- verify:", "- must:")):
                criteria.append(line.split(":", 1)[-1].strip())
            elif lower.startswith(("- constraint:", "* constraint:", "- limit:", "- forbidden:")):
                constraints.append(line.split(":", 1)[-1].strip())
            elif line.startswith(("- [ ]", "- [x]", "* [ ]", "* [x]")):
                criteria.append(line[5:].strip())
            elif line.startswith(("-", "*")):
                criteria.append(line[1:].strip())

        return Goal(
            description=description,
            acceptance_criteria=criteria,
            constraints=constraints,
        )
