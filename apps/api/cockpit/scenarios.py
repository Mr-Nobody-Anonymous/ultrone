# Copyright (c) Ultrone Contributors. All rights reserved.
"""Declarative scenario specifications for the ULTRONE cockpit.

A scenario is *data*, not code: it declares the environment, the ground-truth
entities, the sensing apparatus, the agents, and the pinned model/policy/dataset
versions. The cockpit renders scenarios from this spec (schema-driven UI) and can
run/replay/compare them without editing Python or YAML by hand.

Every scenario is ``simulation_only=True``. The cockpit never exposes physical
actuation controls.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Tuple

#: The cockpit is explicit about *what kind of world* is being shown.
ENVIRONMENT_MODES: Tuple[str, ...] = ("simulation", "replay", "benchmark", "shadow", "lab")

#: Fault-injection levers exposed to the researcher UI.
FAULT_LEVERS: Tuple[str, ...] = (
    "sensor_dropout",
    "telemetry_delay",
    "sensor_disagreement",
    "device_offline",
    "lease_expiry",
    "latency_injection",
    "agent_pause",
)


@dataclass(frozen=True)
class EntitySpec:
    """Ground-truth entity in the simulated world."""

    entity_id: str
    label: str
    domain: str  # "air" | "ground" | "sea" | "structure"
    kind: str  # "friendly" | "unknown" | "hostile" | "neutral"
    position: Tuple[float, float]  # km in world frame
    heading_deg: float = 0.0
    speed_kmh: float = 0.0
    pattern: str = "linear"  # "linear" | "orbit" | "patrol" | "static"
    orbit_radius_km: float = 2.0

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["position"] = list(self.position)
        return d


@dataclass(frozen=True)
class SensorSpec:
    """Sensing apparatus bound to a UDIS device."""

    sensor_id: str
    device_id: str
    label: str
    modality: str  # "radar" | "eo_ir" | "sonar" | "sigint" | "gps"
    position: Tuple[float, float]
    range_km: float = 30.0
    fov_deg: float = 360.0
    noise_sigma_km: float = 0.45
    latency_ticks: int = 0
    ttl_ticks: int = 3
    base_quality: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["position"] = list(self.position)
        return d


@dataclass(frozen=True)
class AgentSpec:
    """An autonomous subsystem participating in the scenario."""

    agent_id: str
    name: str
    role: str  # planner | perception | world_model | evaluator | policy | safety | research
    model_version: str
    capabilities: Tuple[str, ...] = ()
    publishes: Tuple[str, ...] = ()
    subscribes: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["capabilities"] = list(self.capabilities)
        d["subscribes"] = list(self.subscribes)
        return d


@dataclass(frozen=True)
class FaultConfig:
    """Declared fault-injection configuration (point 67 of the UI review).

    Every lever maps onto a *real* subsystem behaviour rather than a UI flag:
    ``telemetry_delay`` pushes frames whose validity horizon is already exceeded,
    which is precisely the mutation SAF-003 exists to kill.
    """

    sensor_dropout: Tuple[str, ...] = ()
    telemetry_delay: Tuple[str, ...] = ()
    sensor_disagreement: Tuple[str, ...] = ()
    device_offline: Tuple[str, ...] = ()
    lease_expiry: bool = False
    latency_injection_ms: float = 0.0
    agent_pause: Tuple[str, ...] = ()

    def is_active(self) -> bool:
        return bool(
            self.sensor_dropout
            or self.telemetry_delay
            or self.sensor_disagreement
            or self.device_offline
            or self.lease_expiry
            or self.latency_injection_ms
            or self.agent_pause
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sensor_dropout": list(self.sensor_dropout),
            "telemetry_delay": list(self.telemetry_delay),
            "sensor_disagreement": list(self.sensor_disagreement),
            "device_offline": list(self.device_offline),
            "lease_expiry": self.lease_expiry,
            "latency_injection_ms": self.latency_injection_ms,
            "agent_pause": list(self.agent_pause),
            "is_active": self.is_active(),
        }


@dataclass(frozen=True)
class ScenarioSpec:
    """Complete, reproducible scenario definition."""

    scenario_id: str
    name: str
    description: str
    seed: int = 12345
    dt_seconds: float = 1.0
    max_ticks: int = 600
    bounds_km: Tuple[float, float, float, float] = (0.0, 0.0, 40.0, 30.0)
    entities: Tuple[EntitySpec, ...] = ()
    sensors: Tuple[SensorSpec, ...] = ()
    agents: Tuple[AgentSpec, ...] = ()
    model_version: str = "vision-v3.2"
    policy_version: str = "policy-v12"
    dataset_version: str = "ds-holdout-v4"
    telemetry_freshness_ms: float = 250.0
    environment: str = "simulation"
    is_simulation_only: bool = True
    tags: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "name": self.name,
            "description": self.description,
            "seed": self.seed,
            "dt_seconds": self.dt_seconds,
            "max_ticks": self.max_ticks,
            "bounds_km": list(self.bounds_km),
            "entities": [e.to_dict() for e in self.entities],
            "sensors": [s.to_dict() for s in self.sensors],
            "agents": [a.to_dict() for a in self.agents],
            "model_version": self.model_version,
            "policy_version": self.policy_version,
            "dataset_version": self.dataset_version,
            "telemetry_freshness_ms": self.telemetry_freshness_ms,
            "environment": self.environment,
            "is_simulation_only": self.is_simulation_only,
            "tags": list(self.tags),
        }


# ── Canonical agent roster ───────────────────────────────────────────────────
# Roles mirror real subsystems under packages/; the cockpit renders them as the
# cognitive pipeline so the architecture itself is visible to the operator.

def default_agents() -> Tuple[AgentSpec, ...]:
    return (
        AgentSpec(
            agent_id="agent-01",
            name="Perception",
            role="perception",
            model_version="vision-v3.2",
            capabilities=("observe.state", "observe.telemetry"),
            publishes=("SensorFusionCompleted", "ObservationReceived"),
            subscribes=("DeviceAcknowledged",),
        ),
        AgentSpec(
            agent_id="agent-02",
            name="World Model",
            role="world_model",
            model_version="world-v2.1",
            capabilities=("observe.state",),
            publishes=("WorldEstimateUpdated",),
            subscribes=("SensorFusionCompleted",),
        ),
        AgentSpec(
            agent_id="agent-03",
            name="Planner",
            role="planner",
            model_version="planner-v3.1",
            capabilities=("observe.state",),
            publishes=("PlanGenerated", "PlanRanked"),
            subscribes=("WorldEstimateUpdated",),
        ),
        AgentSpec(
            agent_id="agent-04",
            name="Policy Engine",
            role="policy",
            model_version="policy-v12",
            capabilities=("observe.state",),
            publishes=("PolicyChecked", "ActionApproved", "ActionRejected"),
            subscribes=("PlanRanked",),
        ),
        AgentSpec(
            agent_id="agent-05",
            name="UDIS Executor",
            role="safety",
            model_version="udis-exec-v1.4",
            capabilities=("simulate.execute", "observe.telemetry"),
            publishes=("ActionProposed", "DeviceCommandIssued"),
            subscribes=("ActionApproved",),
        ),
        AgentSpec(
            agent_id="agent-06",
            name="Evaluator",
            role="evaluator",
            model_version="eval-v2.0",
            capabilities=("observe.state",),
            publishes=("OutcomeObserved", "BenchmarkCompleted"),
            subscribes=("DeviceAcknowledged",),
        ),
        AgentSpec(
            agent_id="agent-07",
            name="Research",
            role="research",
            model_version="research-v1.9",
            capabilities=("simulate.execute",),
            publishes=("ModelUpdated", "PromotionApproved", "PromotionRejected"),
            subscribes=("BenchmarkCompleted",),
        ),
    )


# ── Canonical scenarios ──────────────────────────────────────────────────────

def default_scenarios() -> Tuple[ScenarioSpec, ...]:
    agents = default_agents()
    coastal = ScenarioSpec(
        scenario_id="scn-coastal-patrol",
        name="Coastal Patrol (Simulation)",
        description=(
            "Two surface contacts and one unknown air track inside a 40x30 km coastal box, "
            "observed by a radar, an EO/IR turret and a SIGINT array. Exercises belief-vs-truth "
            "divergence, telemetry freshness gating and lease-scoped simulated execution."
        ),
        seed=12345,
        bounds_km=(0.0, 0.0, 40.0, 30.0),
        entities=(
            EntitySpec("trk-001", "Surface Contact A", "sea", "unknown", (12.0, 18.0), 45.0, 22.0, "linear"),
            EntitySpec("trk-002", "Surface Contact B", "sea", "neutral", (28.0, 9.0), 200.0, 14.0, "patrol"),
            EntitySpec("trk-003", "Air Track", "air", "hostile", (31.0, 24.0), 260.0, 410.0, "orbit", 3.5),
            EntitySpec("trk-004", "Fixed Structure", "structure", "neutral", (20.0, 3.0), 0.0, 0.0, "static"),
        ),
        sensors=(
            SensorSpec("sns-radar-01", "device-001", "Coastal Radar", "radar", (2.0, 26.0), 34.0, 300.0, 0.35, 0, 3),
            SensorSpec("sns-eoir-01", "device-002", "EO/IR Turret", "eo_ir", (6.0, 8.0), 22.0, 120.0, 0.25, 1, 4),
            SensorSpec("sns-sigint-01", "device-003", "SIGINT Array", "sigint", (17.0, 29.0), 28.0, 220.0, 1.10, 2, 6),
        ),
        agents=agents,
        tags=("maritime", "f2t2ea", "belief-divergence"),
    )

    airspace = ScenarioSpec(
        scenario_id="scn-airspace-intercept",
        name="Airspace Intercept (Simulation)",
        description=(
            "High-speed air tracks with a degraded SIGINT feed. Designed to trigger SAF-003 "
            "(stale telemetry cannot authorize action) so the Safety Center's 'Why blocked?' "
            "chain is backed by real evidence."
        ),
        seed=98765,
        dt_seconds=0.5,
        bounds_km=(0.0, 0.0, 60.0, 45.0),
        entities=(
            EntitySpec("trk-101", "Fast Mover 1", "air", "hostile", (45.0, 30.0), 240.0, 880.0, "linear"),
            EntitySpec("trk-102", "Fast Mover 2", "air", "unknown", (52.0, 12.0), 300.0, 640.0, "orbit", 5.0),
            EntitySpec("trk-103", "Support Aircraft", "air", "friendly", (14.0, 36.0), 90.0, 480.0, "patrol"),
        ),
        sensors=(
            SensorSpec("sns-radar-11", "device-011", "Long-Range Radar", "radar", (1.0, 40.0), 58.0, 360.0, 0.55, 0, 2),
            SensorSpec("sns-sigint-11", "device-013", "SIGINT Array", "sigint", (25.0, 41.0), 30.0, 180.0, 1.80, 4, 3, 0.72),
            SensorSpec("sns-eoir-11", "device-012", "EO/IR Turret", "eo_ir", (8.0, 6.0), 26.0, 90.0, 0.30, 1, 4),
        ),
        agents=agents,
        model_version="vision-v3.4",
        telemetry_freshness_ms=200.0,
        tags=("air", "freshness", "degraded-sensor"),
    )
    return (coastal, airspace)


SCENARIOS: Dict[str, ScenarioSpec] = {s.scenario_id: s for s in default_scenarios()}
DEFAULT_SCENARIO_ID = "scn-coastal-patrol"


def get_scenario(scenario_id: Optional[str]) -> ScenarioSpec:
    """Resolve a scenario by id, defaulting to the coastal patrol."""
    if not scenario_id:
        return SCENARIOS[DEFAULT_SCENARIO_ID]
    if scenario_id not in SCENARIOS:
        raise KeyError(f"Unknown scenario '{scenario_id}'. Known: {sorted(SCENARIOS)}")
    return SCENARIOS[scenario_id]


def list_scenarios() -> List[Dict[str, Any]]:
    return [s.to_dict() for s in SCENARIOS.values()]
