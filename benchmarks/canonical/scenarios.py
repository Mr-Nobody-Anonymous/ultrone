# Copyright (c) Ultrone Contributors. All rights reserved.
"""Deterministic scenario suite for the canonical ULTRONE benchmark.

Each scenario pins (version, seed, configuration, faults, human policy) so
that running :meth:`benchmarks.canonical.runner.run_scenario` reproduces
identical decisions. The canonical ``DecisionPipeline`` + ``DecisionTrace``
are the single source of truth; nothing here re-implements pipeline logic.
"""

from __future__ import annotations

import zlib
from dataclasses import dataclass, field
from typing import Any, Dict, Tuple

from sim.fault_injection import FaultSpec, FaultType

#: Bump when scenario semantics change so baselines are invalidated cleanly.
SCENARIO_SUITE_VERSION = "canonical-scenarios-v1"


@dataclass(frozen=True)
class ScenarioSpec:
    """Fully-pinned configuration of one benchmark scenario."""

    scenario_id: str
    description: str
    seed: int = 42
    n_steps: int = 6
    n_candidates: int = 3
    sensor_dropout: float = 0.10
    sensor_noise_sigma: float = 2.0
    confidence_jitter: float = 0.15
    min_engagement_confidence: float = 0.45
    blacklisted_actions: Tuple[str, ...] = ()
    faults: Tuple[FaultSpec, ...] = ()
    # none -> autonomous (audit-only); approve/reject/override -> HITL-gated
    human_policy: str = "none"

    @property
    def fault_seed(self) -> int:
        """Stable per-scenario seed for the injector's own RNG."""
        return (self.seed * 7919 + zlib.crc32(self.scenario_id.encode())) % (2 ** 31)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_suite_version": SCENARIO_SUITE_VERSION,
            "scenario_id": self.scenario_id,
            "description": self.description,
            "seed": self.seed,
            "fault_seed": self.fault_seed,
            "n_steps": self.n_steps,
            "n_candidates": self.n_candidates,
            "sensor_dropout": self.sensor_dropout,
            "sensor_noise_sigma": self.sensor_noise_sigma,
            "confidence_jitter": self.confidence_jitter,
            "min_engagement_confidence": self.min_engagement_confidence,
            "blacklisted_actions": list(self.blacklisted_actions),
            "faults": [f.to_dict() for f in self.faults],
            "human_policy": self.human_policy,
        }


EXECUTABLE_ALL = ("strike", "jam", "move", "resupply")

SCENARIOS: Dict[str, ScenarioSpec] = {
    spec.scenario_id: spec
    for spec in [
        ScenarioSpec(
            scenario_id="normal_operation",
            description="Nominal sensing, resources, and autonomy loop.",
        ),
        ScenarioSpec(
            scenario_id="partial_observation_dropout",
            description="Heavy sensor dropout: belief must degrade gracefully.",
            sensor_dropout=0.55,
        ),
        ScenarioSpec(
            scenario_id="conflicting_sensor_observations",
            description=(
                "SIGINT feed grossly corrupted (large offset): sensors "
                "disagree and fusion must arbitrate."
            ),
            faults=(
                FaultSpec(
                    fault_type=FaultType.NOISY_OBSERVATION,
                    probability=1.0,
                    intensity=40.0,
                    feed_type="sigint",
                ),
            ),
        ),
        ScenarioSpec(
            scenario_id="low_resource_condition",
            description="Fuel/ammo degraded to ~20%: safety rules should bite.",
            faults=(
                FaultSpec(
                    fault_type=FaultType.RESOURCE_DEGRADATION,
                    probability=1.0,
                    intensity=0.2,
                ),
            ),
        ),
        ScenarioSpec(
            scenario_id="safety_gate_rejection",
            description="All executable actions blacklisted: pure no-op loop.",
            blacklisted_actions=EXECUTABLE_ALL,
        ),
        ScenarioSpec(
            scenario_id="human_rejection",
            description="HITL-gated; the human rejects every proposal.",
            human_policy="reject",
        ),
        ScenarioSpec(
            scenario_id="human_override",
            description="HITL-gated; supervisor overrides the first proposal.",
            human_policy="override",
        ),
        ScenarioSpec(
            scenario_id="stale_observations",
            description=(
                "Roughly half of observations are aged snapshots: the pipeline "
                "acts on belief that lags ground truth."
            ),
            faults=(
                FaultSpec(
                    fault_type=FaultType.STALE_OBSERVATION,
                    probability=0.5,
                ),
            ),
        ),
        ScenarioSpec(
            scenario_id="actuator_failure",
            description=(
                "Missile actuators intermittently fail (~50%): approved "
                "strikes silently degrade to no-ops."
            ),
            faults=(
                FaultSpec(
                    fault_type=FaultType.ACTUATOR_FAILURE,
                    probability=0.5,
                    asset_type="missiles",
                ),
            ),
        ),
        ScenarioSpec(
            scenario_id="comms_blackout",
            description=(
                "Total communications blackout: every feed is dropped each "
                "tick; the pipeline must act (or refrain) blind."
            ),
            faults=(
                FaultSpec(
                    fault_type=FaultType.COMMS_LOSS,
                    probability=1.0,
                ),
            ),
        ),
        ScenarioSpec(
            scenario_id="deterministic_replay",
            description="Run twice under the same seed; fingerprints must match.",
            seed=1337,
        ),
    ]
}

REQUIRED_SCENARIO_IDS = tuple(SCENARIOS.keys())
