"""Append-only, cryptographically verifiable Event Store for ULTRONE."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .events import EventType, ImmutableEvent


class IntegrityViolationError(Exception):
    """Raised when tamper detection or chain broken in event log."""
    pass


class EventStore:
    """In-memory and file-backed append-only event store with hash-chain integrity verification."""

    def __init__(self):
        self._traces: Dict[str, List[ImmutableEvent]] = {}
        self._last_event_hash: Dict[str, Optional[str]] = {}

    def append(
        self,
        trace_id: str,
        event_type: EventType,
        logical_tick: int,
        payload: Dict,
    ) -> ImmutableEvent:
        """Append an event to the trace, chaining hash to the previous event."""
        prev_hash = self._last_event_hash.get(trace_id)
        evt = ImmutableEvent.create(
            event_type=event_type,
            trace_id=trace_id,
            logical_tick=logical_tick,
            payload=payload,
            previous_event_hash=prev_hash,
        )
        if trace_id not in self._traces:
            self._traces[trace_id] = []
        self._traces[trace_id].append(evt)
        self._last_event_hash[trace_id] = evt.compute_event_hash()
        return evt

    def get_trace(self, trace_id: str) -> List[ImmutableEvent]:
        """Fetch chronological event list for trace."""
        return list(self._traces.get(trace_id, []))

    def verify_chain_integrity(self, trace_id: str) -> Tuple[bool, Optional[str]]:
        """Verify SHA256 cryptographic chain integrity across all events in a trace."""
        events = self._traces.get(trace_id, [])
        if not events:
            return True, None

        expected_prev_hash: Optional[str] = None
        for idx, evt in enumerate(events):
            if evt.previous_event_hash != expected_prev_hash:
                return False, (
                    f"Integrity check failed at index {idx} (event {evt.event_id}): "
                    f"expected prev_hash {expected_prev_hash}, got {evt.previous_event_hash}"
                )
            expected_prev_hash = evt.compute_event_hash()

        return True, None

    def save_to_jsonl(self, trace_id: str, path: Path | str) -> int:
        """Persist trace to JSONL file."""
        events = self.get_trace(trace_id)
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            for evt in events:
                f.write(json.dumps(evt.to_dict()) + "\n")
        return len(events)

    def load_from_jsonl(self, path: Path | str) -> str:
        """Load trace from JSONL file and register in memory."""
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Trace file not found: {p}")

        loaded_trace_id: Optional[str] = None
        events: List[ImmutableEvent] = []

        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                d = json.loads(line)
                evt = ImmutableEvent(
                    event_id=d["event_id"],
                    event_type=EventType(d["event_type"]),
                    trace_id=d["trace_id"],
                    logical_tick=d["logical_tick"],
                    timestamp=d["timestamp"],
                    payload=d["payload"],
                    payload_hash=d["payload_hash"],
                    previous_event_hash=d.get("previous_event_hash"),
                )
                if loaded_trace_id is None:
                    loaded_trace_id = evt.trace_id
                events.append(evt)

        if not loaded_trace_id:
            raise ValueError("No events found in file")

        self._traces[loaded_trace_id] = events
        self._last_event_hash[loaded_trace_id] = events[-1].compute_event_hash() if events else None

        ok, err = self.verify_chain_integrity(loaded_trace_id)
        if not ok:
            raise IntegrityViolationError(f"Loaded trace corrupted: {err}")

        return loaded_trace_id
