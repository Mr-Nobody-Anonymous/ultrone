# Copyright (c) Ultrone Contributors. All rights reserved.
import pytest

from packages.agents.harness.goal import GoalManager
from packages.agents.harness.schemas import Goal


def test_create_goal_valid():
    goal = GoalManager.create_goal(
        description="Refactor network module",
        acceptance_criteria=["Zero packet loss", "Latency < 20ms"],
        constraints=["Do not modify external API"],
    )
    assert goal.description == "Refactor network module"
    assert len(goal.acceptance_criteria) == 2
    assert len(goal.constraints) == 1
    assert goal.goal_id.startswith("goal-")


def test_create_goal_empty_raises():
    with pytest.raises(ValueError):
        GoalManager.create_goal("")


def test_parse_from_prompt():
    prompt = """Analyze repository structure
- criteria: Identify circular dependencies
- criteria: Measure LOC
- constraint: Read-only access
- verify: Generate report
"""
    goal = GoalManager.parse_from_prompt(prompt)
    assert goal.description == "Analyze repository structure"
    assert "Identify circular dependencies" in goal.acceptance_criteria
    assert "Measure LOC" in goal.acceptance_criteria
    assert "Read-only access" in goal.constraints
