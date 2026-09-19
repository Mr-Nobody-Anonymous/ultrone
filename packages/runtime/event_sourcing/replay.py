"""Deterministic Replay Engine for ULTRONE Event Streams."""

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

from .event_store import EventStore
from .events import EventType, ImmutableEvent


class DeterministicReplayEngine:
    """Replays historical execution event streams and verifies state transitions."""

    def __init__(self, store: EventStore):
        self.store = store

    def replay_trace(
        self,
        trace_id: str,
        step_hook: Optional[Callable[[ImmutableEvent, Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        """Step through all events in chronological order, accumulating state."""
        events = self.store.get_trace(trace_id)
        if not events:
            raise ValueError(f"Trace '{trace_id}' has no recorded events")

        ok, err = self.store.verify_chain_integrity(trace_id)
        if not ok:
            raise RuntimeError(f"Cannot replay corrupted trace: {err}")

        state: Dict[str, Any] = {
            "trace_id": trace_id,
            "current_tick": 0,
            "observations": [],
            "world_estimates": [],
            "plans": [],
            "orders": [],
            "verdicts": [],
            "commands": [],
            "outcomes": [],
        }

        for evt in events:
            state["current_tick"] = evt.logical_tick

            if evt.event_type == EventType.ObservationReceived:
                state["observations"].append(evt.payload)
            elif evt.event_type == EventType.WorldEstimateUpdated:
                state["world_estimates"].append(evt.payload)
            elif evt.event_type == EventType.PlanGenerated:
                state["plans"].append(evt.payload)
            elif evt.event_type == EventType.ActionProposed:
                state["orders"].append(evt.payload)
            elif evt.event_type in (EventType.ActionApproved, EventType.ActionRejected):
                state["verdicts"].append(evt.payload)
            elif evt.event_type == EventType.DeviceCommandIssued:
                state["commands"].append(evt.payload)
            elif evt.event_type == EventType.OutcomeObserved:
                state["outcomes"].append(evt.payload)

            if step_hook:
                step_hook(evt, state)

        return state

    def verify_reproducibility(
        self,
        baseline_trace_id: str,
        candidate_trace_id: str,
    ) -> Tuple[bool, List[str]]:
        """Verify that two experiment runs executed identically without divergence."""
        base_events = self.store.get_trace(baseline_trace_id)
        cand_events = self.store.get_trace(candidate_trace_id)

        divergences: List[str] = []

        if len(base_events) != len(cand_events):
            divergences.append(
                f"Event count mismatch: baseline has {len(base_events)}, candidate has {len(cand_events)}"
            )
            return False, divergences

        for i, (b_evt, c_evt) in enumerate(zip(base_events, cand_events)):
            if b_evt.event_type != c_evt.event_type:
                divergences.append(
                    f"Step {i}: Event type mismatch: {b_evt.event_type.value} vs {c_evt.event_type.value}"
                )
            if b_evt.payload_hash != c_evt.payload_hash:
                divergences.append(
                    f"Step {i} ({b_evt.event_type.value}): Payload divergence detected. "
                    f"Baseline hash {b_evt.payload_hash[:8]} vs candidate {c_evt.payload_hash[:8]}"
                )

        return len(divergences) == 0, divergences


# Explicit alias separating historical event playback from computational re-execution
EventReplayEngine = DeterministicReplayEngine


@dataclass(frozen=True)
class ExecutionEnvelope:
    """Complete provenance envelope required for true independent computational re-execution."""
    git_commit_sha: str
    python_version: str
    random_seed: int
    config_hash: str
    model_weights_hash: str
    environment_version: str = "sim-1.0.0"

    def envelope_digest(self) -> str:
        s = f"{self.git_commit_sha}:{self.python_version}:{self.random_seed}:{self.config_hash}:{self.model_weights_hash}:{self.environment_version}"
        import hashlib
        return hashlib.sha256(s.encode("utf-8")).hexdigest()


from enum import Enum
import hashlib
import json


class ReproducibilityMode(str, Enum):
    """Execution reproducibility operational modes."""
    STRICT = "STRICT"          # Exact bit-for-bit identity across environment and outputs
    SCIENTIFIC = "SCIENTIFIC"  # Bounded numerical drift for GPU / BLAS / floating-point operations


def acceptable_drift(actual: float, expected: float, tolerance: float = 1e-4) -> bool:
    """Check if numerical metric drift is bounded within acceptable tolerance."""
    return abs(actual - expected) <= tolerance


class DeterministicReExecutionEngine:
    """Executes computation from genesis with frozen envelope metadata and asserts zero/bounded drift."""

    def __init__(self, store: Optional[EventStore] = None):
        self.store = store or EventStore()

    def execute_and_verify(
        self,
        envelope: ExecutionEnvelope,
        trace_id: str,
        pipeline_fn: Callable[[int], Dict[str, Any]],
        expected_digest: Optional[str] = None,
        expected_metrics: Optional[Dict[str, float]] = None,
        mode: ReproducibilityMode = ReproducibilityMode.STRICT,
        drift_tolerance: float = 1e-4,
    ) -> Tuple[bool, Dict[str, Any], str]:
        """Runs pipeline_fn with envelope's random_seed, computes result hash, and checks match."""
        results = pipeline_fn(envelope.random_seed)
        serialized = json.dumps(results, sort_keys=True)
        res_digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()

        self.store.append(
            trace_id=trace_id,
            event_type=EventType.BenchmarkCompleted,
            logical_tick=1,
            payload={
                "envelope_digest": envelope.envelope_digest(),
                "result_digest": res_digest,
                "git_commit": envelope.git_commit_sha,
                "seed": envelope.random_seed,
                "reproducibility_mode": mode.value,
            },
        )

        if mode == ReproducibilityMode.STRICT:
            match = True if expected_digest is None else (res_digest == expected_digest)
        else:  # SCIENTIFIC mode: bounded numerical drift
            match = True
            if expected_metrics:
                for k, exp_val in expected_metrics.items():
                    act_val = results.get(k)
                    if act_val is None or not isinstance(act_val, (int, float)):
                        match = False
                        break
                    if not acceptable_drift(float(act_val), float(exp_val), tolerance=drift_tolerance):
                        match = False
                        break

        return match, results, res_digest
