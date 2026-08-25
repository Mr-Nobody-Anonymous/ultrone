# Copyright (c) Ultrone Contributors. All rights reserved.
"""Deterministic benchmark runner over the canonical pipeline.

Runs each :class:`ScenarioSpec` through the real ``DecisionPipeline``
(plus the real HITL bridge/audit layer when a human policy applies), and
records one canonical JSON result containing observations, world estimates,
candidate plans, safety decisions, human decisions, outcomes, reward /
latency / compute metrics, and any failures or constraint violations.
"""

from __future__ import annotations

import hashlib
import json
import random
import time
import traceback
from typing import Any, Dict, List, Optional

from benchmarks.canonical.scenarios import SCENARIO_SUITE_VERSION, ScenarioSpec
from core.pipeline import DecisionPipeline, SensorSuite
from core.safety_gate import SafetyConfig, SafetyGate
from sim.battlefield_env import BattlefieldEnv
from sim.fault_injection import (
    FaultType,
    FaultyEnv,
    FaultySensorSuite,
)
from ultrone_hitl.audit_store import InMemoryAuditStore
from ultrone_hitl.pipeline_bridge import HITLBridge

_SENSOR_FAULTS = {
    FaultType.SENSOR_DROPOUT,
    FaultType.NOISY_OBSERVATION,
    FaultType.COMMS_LOSS,
}


def _canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def content_fingerprint(record: Dict[str, Any]) -> str:
    """Stable hash over deterministic decision content.

    Excludes ids, timestamps, and latency so two seeded replays of the same
    configuration produce identical fingerprints.
    """
    payload = []
    for step in record["steps"]:
        payload.append({
            "tick": step["tick"],
            "confidence": round(
                float(step["world_estimate"].get("primary_target_confidence", 0.0)), 6,
            ),
            "target": step["world_estimate"].get("primary_target_position"),
            "safety_reason": step["safety_verdict"]["reason"],
            "human_state": step["human_state"],
            "executed": step["executed_action"],
            "reward": round(float(step["reward"]), 6),
        })
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def build_pipeline(spec: ScenarioSpec):
    """Construct a fully-pinned pipeline (+ optional fault wrappers)."""
    rng = random.Random(spec.fault_seed)

    sensor_faults = tuple(f for f in spec.faults if f.fault_type in _SENSOR_FAULTS)
    env_faults = tuple(f for f in spec.faults if f.fault_type not in _SENSOR_FAULTS)

    env = BattlefieldEnv()
    if env_faults:
        env = FaultyEnv(env, env_faults, rng)

    suite = SensorSuite(
        random.Random(spec.seed),
        position_noise_sigma=spec.sensor_noise_sigma,
        confidence_jitter=spec.confidence_jitter,
        dropout_probability=spec.sensor_dropout,
    )
    if sensor_faults:
        suite = FaultySensorSuite(suite, spec.faults, rng)

    bridge = HITLBridge(store=InMemoryAuditStore())
    pipeline = DecisionPipeline(
        env=env,
        seed=spec.seed,
        n_candidates=spec.n_candidates,
        safety_gate=SafetyGate(SafetyConfig(
            min_engagement_confidence=spec.min_engagement_confidence,
            blacklisted_actions=spec.blacklisted_actions,
        )),
        hitl_bridge=bridge,
        require_human_approval=(spec.human_policy != "none"),
        scenario_id=spec.scenario_id,
        sensor_suite=suite,
    )
    return pipeline, bridge


def _resolve_human(pipeline, bridge, spec: ScenarioSpec, result) -> str:
    """Apply the scripted human policy through the REAL workflow. Returns state."""
    decision_id = result.info["deferred_decision"]
    if spec.human_policy == "reject":
        pipeline.reject_pending(decision_id, actor="alice", reason="benchmark rejection")
        return "REJECTED"

    if spec.human_policy == "override" and not getattr(
        pipeline, "_bench_override_used", False,
    ):
        # Sprint C fix: overrides flow through the pipeline's canonical
        # machinery -- no direct environment access from the runner.
        pipeline._bench_override_used = True
        target = {"action": "move", "asset_type": "drones", "target": [50, 50]}
        child_id = pipeline.override_pending(
            decision_id, actor="carol", target_order=target,
            note="benchmark supervisor override",
        )
        resolved = pipeline.execute_approved(child_id, actor="bob")
        # The effective action/outcome of this tick is the child's; the
        # parent step record references the superseding decision.
        result.trace.execution["env_action"] = (
            resolved.trace.execution.get("env_action")
        )
        result.trace.outcome = dict(resolved.trace.outcome)
        result.trace.execution["superseded_by"] = child_id
        return f"OVERRIDDEN->{child_id}"

    pipeline.execute_approved(decision_id, actor="bob")  # approve (also post-override)
    return "APPROVED"


def run_scenario(spec: ScenarioSpec) -> Dict[str, Any]:
    """Run one scenario to completion; returns its canonical result record."""
    pipeline, bridge = build_pipeline(spec)
    pipeline.reset_episode()

    steps: List[Dict[str, Any]] = []
    failures: List[str] = []
    total_reward = 0.0

    for _ in range(spec.n_steps):
        t0 = time.perf_counter()
        try:
            result = pipeline.step()
            if result.info.get("deferred_decision"):
                _resolve_human(pipeline, bridge, spec, result)
        except Exception as exc:  # record, never crash the whole suite
            failures.append(f"{type(exc).__name__}: {exc}")
            traceback.print_exc()
            break
        latency_ms = round((time.perf_counter() - t0) * 1000.0, 3)

        trace = result.trace
        reward = float(trace.outcome.get("reward", 0.0))
        total_reward += reward
        steps.append({
            "tick": trace.tick,
            "decision_id": trace.decision_id,
            "observation": trace.sensing.get("observation"),
            "world_estimate": trace.world_state,
            "candidate_plan_ids": list(trace.planning.get("candidate_ids") or []),
            "proposed_orders": trace.planning.get("proposed_orders"),
            "safety_verdict": trace.safety.get("verdict"),
            "human_state": bridge.state_of(trace.decision_id),
            "executed_action": trace.execution.get("env_action"),
            "reward": reward,
            "lifecycle": trace.execution.get("lifecycle"),
            "latency_ms": latency_ms,
        })

    metrics = {
        "total_reward": round(total_reward, 6),
        "steps": len(steps),
        "n_decisions": len(pipeline.traces),
        "safety_rejections": sum(
            1 for s in steps if not s["safety_verdict"]["approved"]
        ),
        # True human refusals only happen under a scripted reject policy;
        # autonomous safety refusals are counted separately.
        "human_rejections": sum(
            1 for s in steps
            if s["human_state"] == "REJECTED"
            and spec.human_policy == "reject"
        ),
        "system_refusals": sum(
            1 for s in steps
            if s["human_state"] == "REJECTED"
            and spec.human_policy != "reject"
        ),
        "overrides": sum(
            1 for s in steps
            if str(s["human_state"]).startswith("OVERRIDDEN")
        ),
        "noop_steps": sum(1 for s in steps if s["executed_action"] is None),
        "mean_step_latency_ms": round(
            sum(s["latency_ms"] for s in steps) / max(1, len(steps)), 3,
        ),
        "max_step_latency_ms": max((s["latency_ms"] for s in steps), default=0.0),
        "feeds_generated": sum(
            int(s["world_estimate"].get("n_feeds_generated", 0)) for s in steps
        ),
        "feeds_received": sum(
            int(s["world_estimate"].get("n_feeds_received", 0)) for s in steps
        ),
        "candidates_evaluated": sum(len(s["candidate_plan_ids"]) for s in steps),
    }
    # Constraint violations come straight from the audited environment outcomes.
    metrics["roe_violations"] = sum(
        1 for ev in bridge.replay()
        if ev["type"] == "outcome"
        and ev["payload"].get("outcome", {}).get("roe_violation")
    )

    record = {
        "scenario_suite_version": SCENARIO_SUITE_VERSION,
        "scenario_id": spec.scenario_id,
        "config": spec.to_dict(),
        "metrics": metrics,
        "steps": steps,
        "failures": failures,
        "constraint_violations": metrics["roe_violations"],
        "fingerprint": content_fingerprint({"steps": steps}),
    }

    # Deterministic-replay scenario: run a second, independent replica and
    # require identical fingerprints.
    if spec.scenario_id == "deterministic_replay":
        replica = _replay_replica(spec)
        record["replay_fingerprint"] = replica
        record["replay_matches"] = (replica == record["fingerprint"])

    audit_counts: Dict[str, int] = {}
    for ev in bridge.replay():
        audit_counts[ev["type"]] = audit_counts.get(ev["type"], 0) + 1
    record["audit_events"] = audit_counts
    record["audit_chain_verified"] = bridge.verify_chain()
    return record


def _replay_replica(spec: ScenarioSpec) -> str:
    """Independent second run of a scenario; returns its content fingerprint."""
    pipeline2, _bridge2 = build_pipeline(spec)
    pipeline2.reset_episode()
    steps: List[Dict[str, Any]] = []
    for _ in range(spec.n_steps):
        result = pipeline2.step()
        if result.info.get("deferred_decision"):
            _resolve_human(pipeline2, _bridge2, spec, result)
        trace = result.trace
        steps.append({
            "tick": trace.tick,
            "decision_id": trace.decision_id,
            "observation": trace.sensing.get("observation"),
            "world_estimate": trace.world_state,
            "candidate_plan_ids": list(trace.planning.get("candidate_ids") or []),
            "proposed_orders": trace.planning.get("proposed_orders"),
            "safety_verdict": trace.safety.get("verdict"),
            "human_state": _bridge2.state_of(trace.decision_id),
            "executed_action": trace.execution.get("env_action"),
            "reward": float(trace.outcome.get("reward", 0.0)),
            "lifecycle": trace.execution.get("lifecycle"),
            "latency_ms": 0.0,
        })
    return content_fingerprint({"steps": steps})


def run_all(scenario_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    from benchmarks.canonical.scenarios import SCENARIOS

    ids = scenario_ids or list(SCENARIOS.keys())
    return [run_scenario(SCENARIOS[sid]) for sid in ids]

