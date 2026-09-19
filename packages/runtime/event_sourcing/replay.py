"""Deterministic Replay Engine for ULTRONE Event Streams."""

from __future__ import annotations

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
