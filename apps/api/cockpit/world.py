# Copyright (c) Ultrone Contributors. All rights reserved.
"""Deterministic simulated world for the ULTRONE cockpit.

This module is the *only* place in the cockpit backend that invents state, and it
does so deterministically from a scenario seed. Everything downstream of it
(telemetry buffers, leases, policy checks, event sourcing, causal traces) is a
real subsystem call.

Core separation enforced here (see VALIDATION_STATUS.md section 1):

* **GROUND TRUTH** - the simulator's private truth. Tagged ``TaintTag.GROUND_TRUTH``
  and never handed to a pre-action decision context.
* **AGENT BELIEF** - produced *only* by fusing timestamped sensor observations,
  with confidence derived from freshness, agreement and measurement noise.
"""

from __future__ import annotations

import hashlib
import math
import random
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from packages.runtime.device_protocol.telemetry import DeviceTelemetryMeasurement
from packages.runtime.event_sourcing.causal_boundary import (
    CausalBoundaryValidator,
    CausalBoundaryViolationError,
    ConfidenceProvenance,
    TaintTag,
    TaintedValue,
)
from packages.runtime.event_sourcing.event_store import EventStore
from packages.runtime.event_sourcing.events import EventType

from .scenarios import EntitySpec, FaultConfig, ScenarioSpec, SensorSpec

EARTH_KM_PER_DEG = 111.32

#: Sentinel for "no evidence at all" - finite so the JSON contract stays valid.
UNBACKED_UNCERTAINTY_KM = 999.0


def _sha256(*parts: Any) -> str:
    token = "|".join(str(p) for p in parts)
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def pick(value: Optional[float], placeholder: str = "unknown") -> str:
    """Render an optional numeric gate observation for the UI."""
    if value is None:
        return placeholder
    return f"{value:.0f} ms"


def primary_device(entity_belief: "BeliefEntity", scenario: ScenarioSpec) -> Optional[str]:
    """The UDIS device whose telemetry most strongly backs a belief."""
    if not entity_belief.contributing_sensors:
        return None
    by_id = {s.sensor_id: s for s in scenario.sensors}
    for sensor_id in entity_belief.contributing_sensors:
        sensor = by_id.get(sensor_id)
        if sensor is not None:
            return sensor.device_id
    return None


@dataclass(frozen=True)
class Observation:
    """A single sensor measurement of a ground-truth entity (agent-visible)."""

    observation_id: str
    tick: int
    sensor_id: str
    device_id: str
    entity_id: str
    modality: str
    x: float
    y: float
    sigma_km: float
    quality: float
    confidence: float
    latency_ticks: int
    observation_hash: str
    received_mono: float
    ttl_seconds: float

    @property
    def age_ms(self) -> float:
        return max(0.0, (time.monotonic() - self.received_mono) * 1000.0)

    def is_fresh(self, freshness_ms: float, now: Optional[float] = None) -> bool:
        age = (time.monotonic() if now is None else now) - self.received_mono
        return age * 1000.0 <= freshness_ms

    def to_dict(self) -> Dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "tick": self.tick,
            "sensor_id": self.sensor_id,
            "device_id": self.device_id,
            "entity_id": self.entity_id,
            "modality": self.modality,
            "position": [round(self.x, 3), round(self.y, 3)],
            "sigma_km": round(self.sigma_km, 4),
            "quality": round(self.quality, 4),
            "confidence": round(self.confidence, 4),
            "latency_ticks": self.latency_ticks,
            "age_ms": round(self.age_ms, 1),
            "observation_hash": self.observation_hash,
        }


@dataclass
class BeliefEntity:
    """The agent's *estimate* of an entity - derived from observations only."""

    entity_id: str
    label: str
    x: float
    y: float
    uncertainty_km: float
    confidence: float
    supporting_observations: List[str] = field(default_factory=list)
    contributing_sensors: List[str] = field(default_factory=list)
    age_ms: float = 0.0
    freshness_ok: bool = False
    disagreement_km: float = 0.0
    provenance: Dict[str, Any] = field(default_factory=dict)
    ground_truth_error_km: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "label": self.label,
            "position": [round(self.x, 3), round(self.y, 3)],
            "uncertainty_km": round(self.uncertainty_km, 4),
            "confidence": round(self.confidence, 4),
            "supporting_observations": list(self.supporting_observations),
            "contributing_sensors": list(self.contributing_sensors),
            "age_ms": round(self.age_ms, 1),
            "freshness_ok": self.freshness_ok,
            "disagreement_km": round(self.disagreement_km, 4),
            "provenance": dict(self.provenance),
            "ground_truth_error_km": (
                None if self.ground_truth_error_km is None else round(self.ground_truth_error_km, 4)
            ),
        }


@dataclass(frozen=True)
class PolicyCheck:
    """One machine-checkable gate applied before an action may execute."""

    check_id: str
    invariant: str
    policy: str
    passed: bool
    detail: str
    required: str = ""
    observed: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "check_id": self.check_id,
            "invariant": self.invariant,
            "policy": self.policy,
            "passed": self.passed,
            "detail": self.detail,
            "required": self.required,
            "observed": self.observed,
        }


@dataclass
class DecisionRecord:
    """A complete, inspectable decision trace (the Cognition screen's unit)."""

    decision_id: str
    tick: int
    agent_id: str
    entity_id: str
    observations: List[str] = field(default_factory=list)
    belief_state_id: str = ""
    memory_refs: List[str] = field(default_factory=list)
    plan_id: str = ""
    plan_rank: int = 1
    alternatives: List[Dict[str, Any]] = field(default_factory=list)
    policy_checks: List[PolicyCheck] = field(default_factory=list)
    policy_version: str = "policy-v12"
    model_version: str = "vision-v3.2"
    approved: bool = False
    blocked_reason: Optional[str] = None
    action: Optional[Dict[str, Any]] = None
    outcome: Optional[Dict[str, Any]] = None
    outcome_tick: Optional[int] = None
    latency_ms: float = 0.0
    causal_boundary_ok: bool = True
    causal_boundary_detail: Optional[str] = None
    lease_id: Optional[str] = None
    confidence: float = 0.0
    evidence_freshness: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "tick": self.tick,
            "agent_id": self.agent_id,
            "entity_id": self.entity_id,
            "observations": list(self.observations),
            "belief_state_id": self.belief_state_id,
            "memory_refs": list(self.memory_refs),
            "plan_id": self.plan_id,
            "plan_rank": self.plan_rank,
            "alternatives": list(self.alternatives),
            "policy_checks": [c.to_dict() for c in self.policy_checks],
            "policy_version": self.policy_version,
            "model_version": self.model_version,
            "approved": self.approved,
            "blocked_reason": self.blocked_reason,
            "action": self.action,
            "outcome": self.outcome,
            "outcome_tick": self.outcome_tick,
            "latency_ms": round(self.latency_ms, 2),
            "causal_boundary_ok": self.causal_boundary_ok,
            "causal_boundary_detail": self.causal_boundary_detail,
            "lease_id": self.lease_id,
            "confidence": round(self.confidence, 4),
            "evidence_freshness": round(self.evidence_freshness, 4),
        }


@dataclass
class WorldHooks:
    """Optional bindings from the world engine to real UDIS subsystems.

    The world engine never imports the registry directly: the runtime injects
    these callables so that every lease check, telemetry push and command
    execution flows through the genuine UDIS objects.
    """

    telemetry_publish: Optional[Any] = None
    lease_validate: Optional[Any] = None
    lease_issue: Optional[Any] = None
    device_state: Optional[Any] = None
    execute_command: Optional[Any] = None


class WorldEngine:
    """Deterministic ticking world producing ground truth, belief and traces."""

    def __init__(
        self,
        scenario: ScenarioSpec,
        event_store: EventStore,
        trace_id: str,
        faults: Optional[FaultConfig] = None,
        hooks: Optional[WorldHooks] = None,
        freshness_ms: Optional[float] = None,
    ):
        self.scenario = scenario
        self.events = event_store
        self.trace_id = trace_id
        self.faults = faults or FaultConfig()
        self.hooks = hooks or WorldHooks()
        self.freshness_ms = float(freshness_ms or scenario.telemetry_freshness_ms)
        self.reset()

    # ── lifecycle ────────────────────────────────────────────────────────────
    def reset(self, faults: Optional[FaultConfig] = None) -> None:
        if faults is not None:
            self.faults = faults
        self.tick = 0
        self._rng = random.Random(self.scenario.seed)
        self._truth: Dict[str, List[float]] = {
            e.entity_id: [e.position[0], e.position[1], e.heading_deg] for e in self.scenario.entities
        }
        self._visible: List[Observation] = []
        self._pending: List[Tuple[int, Observation]] = []
        self._belief: Dict[str, BeliefEntity] = {}
        self._belief_states: Dict[str, Dict[str, Any]] = {}
        self._decisions: List[DecisionRecord] = []
        self._pending_outcomes: List[Tuple[int, str]] = []
        self._gate_frames: Dict[str, DeviceTelemetryMeasurement] = {}
        self._entity_seq = 0
        self._obs_seq = 0
        self._decision_seq = 0
        self._lease_ids: List[str] = []
        self._blocked_count = 0
        self._approved_count = 0
        self._causal_violations = 0
        self._last_step_ms = 0.0

    @property
    def entities(self) -> Tuple[EntitySpec, ...]:
        return self.scenario.entities

    def _entity(self, entity_id: str) -> EntitySpec:
        for e in self.scenario.entities:
            if e.entity_id == entity_id:
                return e
        raise KeyError(entity_id)

    # ─ ground truth (PRIVATE) ───────────────────────────────────────────────
    def _advance_truth(self) -> None:
        dt_h = self.scenario.dt_seconds / 3600.0
        x0, y0, x1, y1 = self.scenario.bounds_km
        for spec in self.scenario.entities:
            state = self._truth[spec.entity_id]
            if spec.pattern == "static" or spec.speed_kmh <= 0:
                continue
            if spec.pattern == "orbit":
                state[2] = (state[2] + 6.0) % 360.0
                cx, cy = spec.position
                rad = math.radians(state[2])
                state[0] = cx + spec.orbit_radius_km * math.cos(rad)
                state[1] = cy + spec.orbit_radius_km * math.sin(rad)
                continue
            step_km = spec.speed_kmh * dt_h
            rad = math.radians(state[2])
            nx = state[0] + step_km * math.sin(rad)
            ny = state[1] + step_km * math.cos(rad)
            if nx < x0 or nx > x1:
                state[2] = (180.0 - state[2]) % 360.0
                nx = min(max(nx, x0), x1)
            if ny < y0 or ny > y1:
                state[2] = (-state[2]) % 360.0
                ny = min(max(ny, y0), y1)
            state[0], state[1] = nx, ny

    def ground_truth(self) -> List[Dict[str, Any]]:
        """Ground truth for the evaluator/dual-view screen only."""
        out = []
        for spec in self.scenario.entities:
            x, y, heading = self._truth[spec.entity_id]
            out.append(
                {
                    "entity_id": spec.entity_id,
                    "label": spec.label,
                    "domain": spec.domain,
                    "kind": spec.kind,
                    "position": [round(x, 3), round(y, 3)],
                    "heading_deg": round(heading, 2),
                    "speed_kmh": spec.speed_kmh,
                    "pattern": spec.pattern,
                    "taint": "GROUND_TRUTH",
                    "evaluator_only": True,
                }
            )
        return out

    # ── sensing (the only channel through which belief may be formed) ───────
    def _sample_sensors(self) -> None:
        x0, y0, x1, y1 = self.scenario.bounds_km
        diag = math.hypot(x1 - x0, y1 - y0)
        for sensor in self.scenario.sensors:
            if sensor.sensor_id in self.faults.sensor_dropout:
                continue
            if sensor.device_id in self.faults.device_offline:
                continue
            sx, sy = sensor.position
            for spec in self.scenario.entities:
                tx, ty, _heading = self._truth[spec.entity_id]
                dist = math.hypot(tx - sx, ty - sy)
                if dist > sensor.range_km:
                    continue
                if sensor.fov_deg < 360.0:
                    bearing = (math.degrees(math.atan2(tx - sx, ty - sy)) + 360.0) % 360.0
                    if abs(((bearing - 0.0 + 180.0) % 360.0) - 180.0) > sensor.fov_deg / 2.0:
                        continue

                sigma = sensor.noise_sigma_km
                if sensor.sensor_id in self.faults.sensor_disagreement:
                    sigma *= 4.0
                # SNR degrades with range; this is what makes confidence honest.
                snr = max(0.05, 1.0 - (dist / max(sensor.range_km, 1e-6)))
                quality = sensor.base_quality * (0.55 + 0.45 * snr)

                self._obs_seq += 1
                obs_id = f"obs-{self._obs_seq:05d}"
                mx = tx + self._rng.gauss(0.0, sigma)
                my = ty + self._rng.gauss(0.0, sigma)
                obs_hash = _sha256(
                    obs_id, sensor.sensor_id, spec.entity_id, self.tick, round(mx, 6), round(my, 6)
                )
                confidence = max(
                    0.0,
                    min(1.0, quality * snr * math.exp(-sigma / max(2.0 * diag, 1e-6) * 12.0)),
                )
                # Frames pushed to a degraded feed carry an already-expired horizon.
                ttl_seconds = (
                    0.0005 if sensor.sensor_id in self.faults.telemetry_delay else max(2.0, self.freshness_ms / 1000.0 * 3.0)
                )
                observation = Observation(
                    observation_id=obs_id,
                    tick=self.tick,
                    sensor_id=sensor.sensor_id,
                    device_id=sensor.device_id,
                    entity_id=spec.entity_id,
                    modality=sensor.modality,
                    x=mx,
                    y=my,
                    sigma_km=sigma,
                    quality=quality,
                    confidence=confidence,
                    latency_ticks=sensor.latency_ticks,
                    observation_hash=obs_hash,
                    received_mono=time.monotonic(),
                    ttl_seconds=ttl_seconds,
                )
                if sensor.latency_ticks > 0:
                    self._pending.append((self.tick + sensor.latency_ticks, observation))
                else:
                    self._deliver(observation, sensor)

    def _deliver(self, observation: Observation, sensor: SensorSpec) -> None:
        """Make an observation agent-visible and push its telemetry frame."""
        self._visible.append(observation)
        if len(self._visible) > 4000:
            self._visible = self._visible[-2000:]

        if self.hooks.telemetry_publish is not None:
            try:
                frame = self.hooks.telemetry_publish(sensor, observation)
            except Exception:  # pragma: no cover - defensive: telemetry must not kill the tick
                frame = None
            if frame is not None:
                self._gate_frames[sensor.sensor_id] = frame

    def _drain_pending(self) -> None:
        due = [p for p in self._pending if p[0] <= self.tick]
        self._pending = [p for p in self._pending if p[0] > self.tick]
        sensors = {s.sensor_id: s for s in self.scenario.sensors}
        for _tick, observation in due:
            sensor = sensors.get(observation.sensor_id)
            if sensor is not None:
                self._deliver(observation, sensor)

    def observations(self, since_tick: Optional[int] = None, limit: int = 200) -> List[Dict[str, Any]]:
        pool = self._visible
        if since_tick is not None:
            pool = [o for o in pool if o.tick >= since_tick]
        return [o.to_dict() for o in pool[-limit:]]

    def gate_frame(self, sensor_id: str) -> Optional[DeviceTelemetryMeasurement]:
        """The exact frame SAF-003 will judge for this sensor."""
        return self._gate_frames.get(sensor_id)

    # ── belief fusion (observations only; ground truth never enters) ────────
    def _fuse_belief(self) -> None:
        window = [o for o in self._visible if o.tick >= self.tick - 8]
        grouped: Dict[str, List[Observation]] = {}
        for obs in window:
            grouped.setdefault(obs.entity_id, []).append(obs)

        now_mono = time.monotonic()
        belief: Dict[str, BeliefEntity] = {}

        for spec in self.scenario.entities:
            observations = grouped.get(spec.entity_id, [])
            if not observations:
                belief[spec.entity_id] = BeliefEntity(
                    entity_id=spec.entity_id,
                    label=spec.label,
                    x=spec.position[0],
                    y=spec.position[1],
                    uncertainty_km=UNBACKED_UNCERTAINTY_KM,
                    confidence=0.0,
                    freshness_ok=False,
                    provenance={
                        "unbacked": True,
                        "note": "no observation available; belief unbacked (confidence clamped to 0.0)",
                    },
                )
                continue

            weights: List[float] = []
            for obs in observations:
                age_s = now_mono - obs.received_mono
                fresh = age_s * 1000.0 <= self.freshness_ms
                w = obs.quality * max(obs.confidence, 1e-3) / max(obs.sigma_km ** 2, 1e-6)
                if not fresh:
                    # Stale evidence may contribute as a weak prior, never as authority.
                    w *= 0.05
                weights.append(w)

            total_w = sum(weights)
            if total_w <= 1e-9:
                belief[spec.entity_id] = BeliefEntity(
                    entity_id=spec.entity_id,
                    label=spec.label,
                    x=observations[-1].x,
                    y=observations[-1].y,
                    uncertainty_km=UNBACKED_UNCERTAINTY_KM,
                    confidence=0.0,
                    supporting_observations=[o.observation_id for o in observations],
                    freshness_ok=False,
                    provenance={"unbacked": True, "note": "all evidence stale; belief unbacked"},
                )
                continue

            ex = sum(w * o.x for w, o in zip(weights, observations)) / total_w
            ey = sum(w * o.y for w, o in zip(weights, observations)) / total_w
            uncertainty = math.sqrt(1.0 / total_w)

            pairwise = 0.0
            for i, a in enumerate(observations):
                for b in observations[i + 1:]:
                    pairwise = max(pairwise, math.hypot(a.x - b.x, a.y - b.y))

            fresh_flags = [o.is_fresh(self.freshness_ms, now_mono) for o in observations]
            freshness_ratio = sum(1.0 for f in fresh_flags if f) / len(fresh_flags)
            agreement = 1.0 / (1.0 + pairwise / max(2.0 * uncertainty, 0.25))
            mean_quality = sum(o.quality for o in observations) / len(observations)
            mean_conf = sum(o.confidence for o in observations) / len(observations)
            confidence = max(0.0, min(1.0, freshness_ratio * agreement * mean_quality * mean_conf))
            age_ms = min((now_mono - o.received_mono) * 1000.0 for o in observations)

            primary = max(observations, key=lambda o: o.confidence)
            tx, ty, _h = self._truth[spec.entity_id]
            belief[spec.entity_id] = BeliefEntity(
                entity_id=spec.entity_id,
                label=spec.label,
                x=ex,
                y=ey,
                uncertainty_km=uncertainty,
                confidence=confidence,
                supporting_observations=[o.observation_id for o in observations],
                contributing_sensors=sorted({o.sensor_id for o in observations}),
                age_ms=age_ms,
                freshness_ok=bool(any(fresh_flags)),
                disagreement_km=pairwise,
                provenance={
                    "confidence": round(confidence, 4),
                    "confidence_source": "fused_sensor_observations",
                    "observation_hash": primary.observation_hash,
                    "model_version": self.scenario.model_version,
                    "model_artifact_hash": _sha256("model", self.scenario.model_version),
                    "calibration_version": "cal-v8",
                    "calibration_artifact_hash": _sha256("calibration", "cal-v8", primary.sensor_id),
                    "sensor_id": primary.sensor_id,
                    "sensor_calibration_version": f"{primary.modality}-cal-3.1",
                    "freshness_ms": round(age_ms, 1),
                    "freshness_horizon_ms": self.freshness_ms,
                    "observations_used": len(observations),
                    "taint": "OBSERVATION_ONLY",
                },
                ground_truth_error_km=math.hypot(ex - tx, ey - ty),
            )

        self._belief = belief
        self._belief_states[f"bs-{self.tick:05d}"] = {
            "belief_state_id": f"bs-{self.tick:05d}",
            "tick": self.tick,
            "created_mono": now_mono,
            "entities": [b.to_dict() for b in belief.values()],
        }
        if len(self._belief_states) > 600:
            for stale_key in list(self._belief_states)[:200]:
                self._belief_states.pop(stale_key, None)

    def belief(self) -> List[Dict[str, Any]]:
        return [b.to_dict() for b in self._belief.values()]

    def belief_state(self, belief_state_id: str) -> Optional[Dict[str, Any]]:
        return self._belief_states.get(belief_state_id)

    # ── planning (cognition stage) ──────────────────────────────────────────
    def _plan_for(self, spec: EntitySpec, entity_belief: BeliefEntity) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        urgency = {"hostile": 1.0, "unknown": 0.6, "neutral": 0.25, "friendly": 0.0}.get(spec.kind, 0.3)
        conf = entity_belief.confidence
        proximity = max(0.0, 1.0 - entity_belief.uncertainty_km / 20.0)

        candidates = [
            {
                "intent": "simulate.intercept",
                "score": round(urgency * conf * (0.5 + 0.5 * proximity), 4),
                "rationale": "highest-urgency geometry inside the simulation boundary",
                "risk": "high",
            },
            {
                "intent": "simulate.observe",
                "score": round((0.55 + 0.45 * proximity) * conf, 4),
                "rationale": "passive track refinement; no state change on the device",
                "risk": "low",
            },
            {
                "intent": "hold",
                "score": round((1.0 - conf) * 0.8, 4),
                "rationale": "insufficient epistemic support to justify action",
                "risk": "none",
            },
        ]
        candidates.sort(key=lambda c: c["score"], reverse=True)
        for rank, candidate in enumerate(candidates, start=1):
            candidate["rank"] = rank

        plan_id = f"plan-{self.tick:05d}-{spec.entity_id}"
        best = dict(candidates[0])
        best["plan_id"] = plan_id
        best["entity_id"] = spec.entity_id
        best["expected_gain"] = round(best["score"], 4)
        return best, candidates[1:]

    def _ensure_lease(self, agent_id: str, device_id: str, capability: str) -> Optional[str]:
        if self.hooks.lease_issue is None:
            return None
        try:
            lease_id = self.hooks.lease_issue(agent_id, device_id, (capability,))
        except Exception:
            return None
        if lease_id:
            self._lease_ids.append(lease_id)
        return lease_id

    # ── the exact pre-action context SAF-001 will judge ──────────────────────
    def build_pre_action_context(
        self,
        spec: EntitySpec,
        entity_belief: BeliefEntity,
        plan: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Pre-action decision inputs.

        Ground truth and the ``ground_truth_error_km`` derived from it are
        deliberately excluded: this dict is what the causal validator inspects.
        """
        return {
            "tick": self.tick,
            "agent_id": "agent-03",
            "entity_id": spec.entity_id,
            "observations": list(entity_belief.supporting_observations),
            "belief": {
                "belief_state_id": f"bs-{self.tick:05d}",
                "position": [round(entity_belief.x, 3), round(entity_belief.y, 3)],
                "uncertainty_km": round(entity_belief.uncertainty_km, 4),
                "confidence": round(entity_belief.confidence, 4),
                "freshness_ok": entity_belief.freshness_ok,
                "disagreement_km": round(entity_belief.disagreement_km, 4),
            },
            "plan": {
                "plan_id": plan["plan_id"],
                "intent": plan["intent"],
                "rank": plan["rank"],
                "expected_gain": plan["expected_gain"],
            },
            "policy_version": self.scenario.policy_version,
            "model_version": self.scenario.model_version,
        }

    # ── policy gate: the "why allowed / why blocked" evidence chain ─────────
    def _policy_gate(
        self,
        spec: EntitySpec,
        entity_belief: BeliefEntity,
        plan: Dict[str, Any],
        capability: str,
        lease_id: Optional[str],
    ) -> List[PolicyCheck]:
        checks: List[PolicyCheck] = []

        # SAF-001 - causal boundary over the exact pre-action context.
        context = self.build_pre_action_context(spec, entity_belief, plan)
        try:
            CausalBoundaryValidator.inspect_decision_inputs(context, "decision_context")
            checks.append(
                PolicyCheck(
                    "POL-001",
                    "SAF-001",
                    "causal-boundary-v3",
                    True,
                    "Pre-action context holds only observations, belief, plan and version pins.",
                    required="0 post-action fields",
                    observed="0",
                )
            )
        except CausalBoundaryViolationError as exc:
            self._causal_violations += 1
            checks.append(
                PolicyCheck(
                    "POL-001",
                    "SAF-001",
                    "causal-boundary-v3",
                    False,
                    str(exc),
                    required="0 post-action fields",
                    observed="violation",
                )
            )

        # SAF-002 - capability lease must be valid and cover the capability.
        if self.hooks.lease_validate is not None:
            lease_ok, lease_err = self.hooks.lease_validate(lease_id, capability)
        else:  # pragma: no cover - hooks are always injected by the runtime
            lease_ok, lease_err = (False, "no lease manager bound")
        checks.append(
            PolicyCheck(
                "POL-002",
                "SAF-002",
                "expired-lease-cannot-execute",
                bool(lease_ok),
                lease_err or f"Lease '{lease_id}' authorizes '{capability}'.",
                required=f"active lease for {capability}",
                observed=lease_id or "none",
            )
        )

        # SAF-003 - telemetry freshness across every contributing sensor.
        stale: List[str] = []
        ages: List[float] = []
        for sensor_id in entity_belief.contributing_sensors:
            frame = self.gate_frame(sensor_id)
            if frame is None:
                stale.append(f"{sensor_id}:no-frame")
                continue
            age_ms = max(0.0, (time.monotonic() - frame.monotonic_timestamp) * 1000.0)
            ages.append(age_ms)
            if not frame.is_fresh():
                stale.append(f"{sensor_id}:{age_ms:.0f}ms")
        freshest = min(ages) if ages else None
        freshness_ok = not stale and bool(ages)
        checks.append(
            PolicyCheck(
                "POL-003",
                "SAF-003",
                "stale-telemetry-cannot-authorize-action",
                freshness_ok,
                (
                    f"All contributing telemetry inside the {self.freshness_ms:.0f} ms horizon."
                    if freshness_ok
                    else "Stale or missing telemetry: " + ", ".join(stale)
                ),
                required=f"< {self.freshness_ms:.0f} ms",
                observed=pick(freshest, "unknown"),
            )
        )

        # SAF-004 - device must be in an operational state.
        device_id = primary_device(entity_belief, self.scenario)
        device_state: Optional[str] = None
        if device_id and self.hooks.device_state is not None:
            try:
                device_state = self.hooks.device_state(device_id)
            except Exception:
                device_state = None
        operational = device_state in ("READY", "SIMULATION")
        checks.append(
            PolicyCheck(
                "POL-004",
                "SAF-004",
                "emergency-stop-is-terminal-until-reset",
                operational,
                (
                    f"Device '{device_id}' operational ({device_state})."
                    if operational
                    else f"Device '{device_id}' not operational (state={device_state})."
                ),
                required="READY or SIMULATION",
                observed=str(device_state),
            )
        )

        # ROE-007 - rules of engagement: never engage a declared friendly.
        roe_ok = spec.kind != "friendly"
        checks.append(
            PolicyCheck(
                "POL-005",
                "ROE-007",
                "roe-no-engagement-on-friendly",
                roe_ok,
                (
                    "Target is a declared friendly; engagement prohibited."
                    if not roe_ok
                    else "No friendly-engagement conflict."
                ),
                required="target not friendly",
                observed=spec.kind,
            )
        )

        # CONF-001 - confidence must carry a cryptographic provenance chain.
        provenance = ConfidenceProvenance(
            confidence=entity_belief.confidence,
            confidence_source=str(entity_belief.provenance.get("confidence_source", "")),
            observation_ids=list(entity_belief.supporting_observations),
            model_version=str(entity_belief.provenance.get("model_version", "")),
            calibration_version=str(entity_belief.provenance.get("calibration_version", "")),
            observation_hash=entity_belief.provenance.get("observation_hash"),
            model_artifact_hash=entity_belief.provenance.get("model_artifact_hash"),
            calibration_artifact_hash=entity_belief.provenance.get("calibration_artifact_hash"),
            sensor_id=entity_belief.provenance.get("sensor_id"),
            sensor_calibration_version=entity_belief.provenance.get("sensor_calibration_version"),
            ttl_seconds=max(5.0, self.freshness_ms / 1000.0 * 4.0),
        )
        conf_ok = provenance.is_valid(require_crypto=True) and entity_belief.confidence >= 0.35
        checks.append(
            PolicyCheck(
                "POL-006",
                "CONF-001",
                "confidence-requires-provenance",
                conf_ok,
                (
                    "Confidence chain verified (observation -> model -> calibration -> sensor)."
                    if conf_ok
                    else (
                        f"Confidence {entity_belief.confidence:.2f} below the 0.35 floor "
                        "or provenance chain incomplete."
                    )
                ),
                required=">= 0.35 with cryptographic chain",
                observed=f"{entity_belief.confidence:.2f}",
            )
        )
        return checks

    # ── decision stage ──────────────────────────────────────────────────────
    def _decide(self) -> None:
        for spec in self.scenario.entities:
            entity_belief = self._belief.get(spec.entity_id)
            if entity_belief is None:
                continue

            plan, alternatives = self._plan_for(spec, entity_belief)
            capability = "simulate.execute"
            device_id = primary_device(entity_belief, self.scenario)

            # A lease is requested for every action, then revoked when the fault
            # lever is armed: SAF-002 must be the thing that catches it.
            lease_id = None if self.faults.lease_expiry else self._ensure_lease("agent-03", device_id or "", capability)

            self._decision_seq += 1
            decision = DecisionRecord(
                decision_id=f"DEC-{self._decision_seq:05d}",
                tick=self.tick,
                agent_id="agent-03",
                entity_id=spec.entity_id,
                observations=list(entity_belief.supporting_observations),
                belief_state_id=f"bs-{self.tick:05d}",
                memory_refs=[f"memory-{100 + (self.tick % 7)}", f"memory-{109 + (self.tick % 5)}"],
                plan_id=plan["plan_id"],
                plan_rank=plan["rank"],
                alternatives=alternatives,
                policy_version=self.scenario.policy_version,
                model_version=self.scenario.model_version,
                confidence=entity_belief.confidence,
                evidence_freshness=(0.0 if not entity_belief.freshness_ok else round(max(0.0, 1.0 - entity_belief.age_ms / max(self.freshness_ms, 1.0)), 4)),
                lease_id=lease_id,
            )

            decision.policy_checks = self._policy_gate(spec, entity_belief, plan, capability, lease_id)
            failed = [c for c in decision.policy_checks if not c.passed]
            decision.causal_boundary_ok = all(c.passed for c in decision.policy_checks if c.invariant == "SAF-001")
            if failed:
                decision.causal_boundary_detail = failed[0].detail

            actionable = plan["intent"] != "hold"
            if failed or not actionable:
                decision.approved = False
                decision.blocked_reason = (
                    failed[0].invariant if failed else "PLAN-NO-ACTION"
                )
                self._blocked_count += 1
                self._emit(EventType.ActionRejected, decision.tick, {
                    "decision_id": decision.decision_id,
                    "entity_id": spec.entity_id,
                    "reason": decision.blocked_reason,
                    "failed_checks": [c.check_id for c in failed],
                })
            else:
                decision.approved = True
                self._approved_count += 1
                latency_ms = abs(self._rng.gauss(30.0, 9.0)) + (18.0 if spec.domain == "air" else 0.0)
                decision.latency_ms = latency_ms + self.faults.latency_injection_ms
                action = {
                    "action_id": f"action-{self._decision_seq:05d}",
                    "intent": plan["intent"],
                    "device_id": device_id,
                    "capability": capability,
                    "parameters": {
                        "entity_id": spec.entity_id,
                        "aimpoint": [round(entity_belief.x, 3), round(entity_belief.y, 3)],
                        "confidence": round(entity_belief.confidence, 4),
                    },
                    "environment": "simulation",
                    "lease_id": lease_id,
                }
                decision.action = action
                self._emit(EventType.ActionApproved, decision.tick, {
                    "decision_id": decision.decision_id,
                    "action_id": action["action_id"],
                    "entity_id": spec.entity_id,
                    "checks_passed": len(decision.policy_checks),
                })
                if device_id and self.hooks.execute_command is not None:
                    try:
                        result = self.hooks.execute_command(device_id, plan["intent"], action["parameters"], lease_id)
                        decision.action["result"] = result
                    except Exception as exc:
                        decision.approved = False
                        decision.blocked_reason = f"UDIS-EXECUTION-{type(exc).__name__}"
                        decision.action["error"] = str(exc)
                self._emit(EventType.DeviceCommandIssued, decision.tick, {
                    "decision_id": decision.decision_id,
                    "device_id": device_id,
                    "intent": plan["intent"],
                })
                self._pending_outcomes.append((self.tick + 2, decision.decision_id))

            self._emit(EventType.PlanGenerated, decision.tick, {
                "plan_id": plan["plan_id"],
                "intent": plan["intent"],
                "alternatives": len(alternatives),
            })
            self._emit(EventType.PolicyChecked, decision.tick, {
                "decision_id": decision.decision_id,
                "checks": len(decision.policy_checks),
                "failed": [c.check_id for c in failed],
            })
            self._decisions.append(decision)
            if len(self._decisions) > 400:
                self._decisions = self._decisions[-200:]

    # ── outcomes (POST-ACTION: the only place ground truth may be used) ──────
    def _resolve_outcomes(self) -> None:
        due = [p for p in self._pending_outcomes if p[0] <= self.tick]
        self._pending_outcomes = [p for p in self._pending_outcomes if p[0] > self.tick]
        by_id = {d.decision_id: d for d in self._decisions}
        for tick_due, decision_id in due:
            decision = by_id.get(decision_id)
            if decision is None or decision.action is None:
                continue
            entity_belief = self._belief.get(decision.entity_id)
            truth = self._truth.get(decision.entity_id)
            if entity_belief is None or truth is None:
                continue
            error_km = math.hypot(entity_belief.x - truth[0], entity_belief.y - truth[1])
            predicted = float(decision.action["parameters"]["confidence"])
            realized = 1.0 / (1.0 + error_km)
            decision.outcome = {
                "outcome_id": f"outcome-{decision.decision_id}",
                "observed_tick": tick_due,
                "prediction_error": round(abs(predicted - realized), 4),
                "realized_quality": round(realized, 4),
                "belief_error_km": round(error_km, 4),
                "success": realized >= 0.5,
                "taint": "POST_ACTION_OUTCOME",
                "evaluator_only": True,
                "note": "Post-action outcome. Legally uses ground truth; never enters a pre-action context.",
            }
            decision.outcome_tick = tick_due
            self._emit(EventType.OutcomeObserved, tick_due, {
                "decision_id": decision.decision_id,
                "success": decision.outcome["success"],
                "belief_error_km": decision.outcome["belief_error_km"],
            })

    # ── event emission (real event-sourced store, hash-chained) ─────────────
    def _emit(self, event_type: EventType, tick: int, payload: Dict[str, Any]) -> None:
        self.events.append(self.trace_id, event_type, tick, payload)

    # ── tick ────────────────────────────────────────────────────────────────
    def step(self) -> Dict[str, Any]:
        """Advance the world exactly one deterministic tick."""
        started = time.perf_counter()
        self.tick += 1
        self._advance_truth()
        self._drain_pending()
        self._sample_sensors()
        self._fuse_belief()
        self._resolve_outcomes()
        self._decide()

        fresh = sum(1 for o in self._visible if o.tick == self.tick and o.is_fresh(self.freshness_ms))
        self._emit(
            EventType.SensorFusionCompleted,
            self.tick,
            {"observations": sum(1 for o in self._visible if o.tick == self.tick), "fresh": fresh},
        )
        self._emit(
            EventType.WorldEstimateUpdated,
            self.tick,
            {"belief_state_id": f"bs-{self.tick:05d}", "entities": len(self._belief)},
        )
        self._last_step_ms = (time.perf_counter() - started) * 1000.0
        return self.snapshot()

    @property
    def last_step_ms(self) -> float:
        return self._last_step_ms

    # ── read models for the cockpit ─────────────────────────────────────────
    def decisions(self, limit: int = 50, approved_only: Optional[bool] = None) -> List[Dict[str, Any]]:
        pool = self._decisions
        if approved_only is not None:
            pool = [d for d in pool if d.approved is approved_only]
        return [d.to_dict() for d in pool[-limit:]]

    def decision(self, decision_id: str) -> Optional[Dict[str, Any]]:
        for d in self._decisions:
            if d.decision_id == decision_id:
                payload = d.to_dict()
                payload["pre_action_context"] = self._decision_context_for(d)
                return payload
        return None

    def _decision_context_for(self, decision: DecisionRecord) -> Dict[str, Any]:
        entity_belief = self._belief.get(decision.entity_id)
        if entity_belief is None:
            return {}
        spec = self._entity(decision.entity_id)
        plan = {
            "plan_id": decision.plan_id,
            "intent": decision.action["intent"] if decision.action else "hold",
            "rank": decision.plan_rank,
            "expected_gain": 0.0,
        }
        return self.build_pre_action_context(spec, entity_belief, plan)

    def trace_chain(self, decision_id: str) -> Optional[Dict[str, Any]]:
        """Ordered provenance chain for the cognitive-trace viewer."""
        for d in self._decisions:
            if d.decision_id != decision_id:
                continue
            return {
                "decision_id": d.decision_id,
                "stages": [
                    {"stage": "OBSERVATIONS", "kind": "observation", "ids": d.observations},
                    {"stage": "BELIEF", "kind": "belief", "ids": [d.belief_state_id]},
                    {"stage": "MEMORY", "kind": "memory", "ids": d.memory_refs},
                    {"stage": "PLAN", "kind": "plan", "ids": [d.plan_id]},
                    {"stage": "POLICY", "kind": "policy", "ids": [c.check_id for c in d.policy_checks]},
                    {"stage": "DECISION", "kind": "decision", "ids": [d.decision_id]},
                    {"stage": "ACTION", "kind": "action", "ids": [d.action["action_id"]] if d.action else []},
                    {"stage": "OUTCOME", "kind": "outcome", "ids": [d.outcome["outcome_id"]] if d.outcome else []},
                ],
                "authorized": d.approved,
                "blocked_reason": d.blocked_reason,
            }
        return None

    def stats(self) -> Dict[str, Any]:
        return {
            "tick": self.tick,
            "scenario_id": self.scenario.scenario_id,
            "entities": len(self.scenario.entities),
            "sensors": len(self.scenario.sensors),
            "observations": len(self._visible),
            "pending_observations": len(self._pending),
            "decisions": len(self._decisions),
            "approved": self._approved_count,
            "blocked": self._blocked_count,
            "causal_violations": self._causal_violations,
            "leased": len(set(self._lease_ids)),
            "freshness_horizon_ms": self.freshness_ms,
            "step_ms": round(self._last_step_ms, 3),
            "faults": self.faults.to_dict(),
        }

    def snapshot(self) -> Dict[str, Any]:
        """Full cockpit snapshot: truth, belief, and the divergence between them."""
        truth = {t["entity_id"]: t for t in self.ground_truth()}
        belief = {b["entity_id"]: b for b in self.belief()}
        comparison = []
        for entity_id, truth_entity in truth.items():
            estimate = belief.get(entity_id, {})
            comparison.append({
                "entity_id": entity_id,
                "label": truth_entity["label"],
                "kind": truth_entity["kind"],
                "ground_truth": truth_entity["position"],
                "belief": estimate.get("position"),
                "error_km": estimate.get("ground_truth_error_km"),
                "uncertainty_km": estimate.get("uncertainty_km"),
                "confidence": estimate.get("confidence"),
                "age_ms": estimate.get("age_ms"),
                "freshness_ok": estimate.get("freshness_ok"),
                "disagreement_km": estimate.get("disagreement_km"),
                "confidence_provenance": estimate.get("provenance", {}),
            })
        return {
            "tick": self.tick,
            "scenario_id": self.scenario.scenario_id,
            "environment": self.scenario.environment,
            "simulation_only": self.scenario.is_simulation_only,
            "bounds_km": list(self.scenario.bounds_km),
            "model_version": self.scenario.model_version,
            "policy_version": self.scenario.policy_version,
            "freshness_horizon_ms": self.freshness_ms,
            "ground_truth": self.ground_truth(),
            "belief": self.belief(),
            "comparison": comparison,
            "sensors": [s.to_dict() for s in self.scenario.sensors],
            "observations": self.observations(limit=120),
            "stats": self.stats(),
        }

    # ── causal-boundary self-test (backs the boundary-violation UI) ──────────
    def boundary_self_test(self) -> Dict[str, Any]:
        """Prove live that the validator accepts clean context and rejects
        post-action contamination. Returns the exact evidence the UI renders."""
        spec = self.scenario.entities[0]
        entity_belief = self._belief.get(spec.entity_id) or BeliefEntity(
            entity_id=spec.entity_id,
            label=spec.label,
            x=spec.position[0],
            y=spec.position[1],
            uncertainty_km=1.0,
            confidence=0.5,
            supporting_observations=["obs-selftest"],
            provenance={
                "confidence_source": "fused_sensor_observations",
                "model_version": self.scenario.model_version,
            },
        )
        plan, _alternatives = self._plan_for(spec, entity_belief)
        clean = self.build_pre_action_context(spec, entity_belief, plan)

        clean_ok = True
        clean_detail: Optional[str] = None
        try:
            CausalBoundaryValidator.inspect_decision_inputs(clean, "decision_context")
        except CausalBoundaryViolationError as exc:
            clean_ok = False
            clean_detail = str(exc)

        contaminated = dict(clean)
        contaminated["plan"] = dict(clean["plan"])
        contaminated["plan"]["metadata"] = {"actual_outcome": {"success": True}}

        tainted = dict(clean)
        tainted["belief"] = dict(clean["belief"])
        tainted["belief"]["hidden_truth"] = TaintedValue(
            value=[0.0, 0.0], tag=TaintTag.GROUND_TRUTH, source="simulator_oracle"
        )

        def probe(context: Dict[str, Any], field: str) -> Dict[str, Any]:
            try:
                CausalBoundaryValidator.inspect_decision_inputs(context, "decision_context")
                return {"probe": field, "rejected": False, "detail": None}
            except CausalBoundaryViolationError as exc:
                return {"probe": field, "rejected": True, "detail": str(exc)}

        return {
            "invariant": "SAF-001",
            "clean_context_accepted": clean_ok,
            "clean_detail": clean_detail,
            "probes": [
                probe(contaminated, "decision_context.plan.metadata.actual_outcome"),
                probe(tainted, "decision_context.belief.hidden_truth"),
            ],
            "evaluated_at_tick": self.tick,
        }