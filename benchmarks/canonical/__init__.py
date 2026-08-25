# Copyright (c) Ultrone Contributors. All rights reserved.
"""Canonical ULTRONE benchmark/evaluation suite (Sprint B-B).

The existing canonical ``DecisionPipeline`` and ``DecisionTrace`` are the
benchmark's source of truth. Run as a CI gate:

    python -m benchmarks.canonical                 # compare vs baselines.json
    python -m benchmarks.canonical --update-baselines
"""

from benchmarks.canonical.scenarios import (
    REQUIRED_SCENARIO_IDS,
    SCENARIO_SUITE_VERSION,
    SCENARIOS,
    ScenarioSpec,
)
from benchmarks.canonical.runner import run_all, run_scenario

__all__ = [
    "SCENARIO_SUITE_VERSION",
    "REQUIRED_SCENARIO_IDS",
    "SCENARIOS",
    "ScenarioSpec",
    "run_all",
    "run_scenario",
]
