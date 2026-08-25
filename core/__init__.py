# Copyright (c) Ultrone Contributors. All rights reserved.
"""ULTRONE core - the canonical end-to-end decision pipeline.

This package is the authoritative integration layer proving that the
full chain works as one system:

    observation -> sensors -> fusion -> world estimate -> COA planning
        -> independent safety gate -> execution -> outcome -> decision trace

Public API:
    Observation, WorldEstimate, ActionOrder, AssetSnapshot,
    SafetyVerdict, DecisionTrace, StepResult   - contracts
    SensorSuite, DecisionPipeline              - pipeline
    SafetyConfig, SafetyGate                   - safety enforcement
"""

from core.contracts import (
    ActionOrder,
    AssetSnapshot,
    DecisionTrace,
    Observation,
    SafetyRuleResult,
    SafetyVerdict,
    SensorRecord,
    StepResult,
    WorldEstimate,
    new_id,
)
from core.pipeline import DecisionPipeline, SensorSuite
from core.safety_gate import SafetyConfig, SafetyGate

__all__ = [
    # Contracts
    "Observation",
    "SensorRecord",
    "WorldEstimate",
    "ActionOrder",
    "AssetSnapshot",
    "SafetyRuleResult",
    "SafetyVerdict",
    "DecisionTrace",
    "StepResult",
    "new_id",
    # Pipeline
    "SensorSuite",
    "DecisionPipeline",
    # Safety
    "SafetyConfig",
    "SafetyGate",
]
