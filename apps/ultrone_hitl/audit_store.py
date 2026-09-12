# Copyright (c) Ultrone Contributors. All rights reserved.
"""Append-only, tamper-evident audit store for DecisionTrace.

Records are stored in append-only order, each linked to its predecessor by a
SHA-256 hash chain so that a prior record cannot be silently mutated.
Every transition appends a new line rather than rewriting old ones.

Two backends share one interface:
  InMemoryAuditStore -- a Python list (tests / short-lived).
  JSONLAuditStore    -- persistent JSON Lines file (production).
"""

from __future__ import annotations

import copy
import hashlib
import json
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


class AuditStoreError(Exception):
    """Base error for the audit store."""


class DuplicateDecisionError(AuditStoreError):
    """A decision's original proposal may only be recorded once."""

    def __init__(self, decision_id: str) -> None:
        super().__init__(f"proposal decision already recorded: {decision_id}")
        self.decision_id = decision_id


class TamperDetectedError(AuditStoreError):
    """Hash-chain validation failed; a prior record was altered."""


_PROPOSAL_TYPES = frozenset({"submit"})


def _new_event_id() -> str:
    return f"EVT-{uuid.uuid4().hex[:16]}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _canonical(obj: Any) -> str:
    """Stable, sorted JSON serialization used for hashing."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _hash_chain_digest(event: Dict[str, Any], prev: str) -> str:
    body = {k: v for k, v in event.items() if k != "hash"}
    body["prev_chain"] = prev
    return _sha256(_canonical(body))


def _build_event(
    event_type: str,
    decision_id: str,
    state: str,
    actor: str,
    payload: Dict[str, Any],
    prev: str,
) -> Dict[str, Any]:
    event: Dict[str, Any] = {
        "event_id": _new_event_id(),
        "type": event_type,
        "decision_id": decision_id,
        "state": state,
        "actor": actor,
        "timestamp": _now_iso(),
        "payload": copy.deepcopy(payload),
        "prev_hash": prev,
        "hash": "",
    }
    event["hash"] = _hash_chain_digest(event, prev)
    return event


class AuditStore(ABC):
    """Immutable-memory, tamper-evident log of decision events.

    One decision gets exactly one proposal record under its decision_id; every
    transition (approve / reject / override / execute) appends a new record.
    """

    @abstractmethod
    def _snapshot(self) -> List[Dict[str, Any]]:
        """Return the authoritative list of raw events (no copies)."""

    @abstractmethod
    def _persist(self, event: Dict[str, Any]) -> None:
        """Append one new event to the durable backing store."""

    def append_event(
        self, event_type, decision_id, state, actor, payload
    ) -> str:
        """Append one immutable event; returns its event_id."""
        snap = self._snapshot()
        if event_type in _PROPOSAL_TYPES and any(
            d.get("type") in _PROPOSAL_TYPES and d.get("decision_id") == decision_id
            for d in snap
        ):
            raise DuplicateDecisionError(decision_id)
        prev = snap[-1]["hash"] if snap else ""
        event = _build_event(event_type, decision_id, state, actor, payload, prev)
        self._persist(event)
        return event["event_id"]

    def events(self) -> List[Dict[str, Any]]:
        """All events ordered, hash-chain verified, deep-copied."""
        snap = self._snapshot()
        self.verify(snap)
        return copy.deepcopy(snap)

    def replay(self) -> List[Dict[str, Any]]:
        """Chronological read/replay of the entire log."""
        return self.events()

    def decision_events(self, decision_id: str) -> List[Dict[str, Any]]:
        """Ordered history of one decision (verified, deep-copied)."""
        snap = self._snapshot()
        self.verify(snap)
        return copy.deepcopy([e for e in snap if e["decision_id"] == decision_id])

    def decision_exists(self, decision_id: str) -> bool:
        return any(e.get("decision_id") == decision_id for e in self._snapshot())

    def current_state(self, decision_id: str) -> Optional[str]:
        events = self.decision_events(decision_id)
        return events[-1]["state"] if events else None

    def verify(self, snap: Optional[List[Dict[str, Any]]] = None) -> bool:
        """Recompute the full hash chain; raise if any event was altered."""
        events = snap if snap is not None else self._snapshot()
        prev_stored: Optional[str] = None
        for idx, ev in enumerate(events):
            expected_prev = prev_stored if prev_stored is not None else ""
            if ev.get("prev_hash", "") != expected_prev:
                raise TamperDetectedError(
                    f"broken hash chain at record {idx} ({ev.get('event_id')})"
                )
            if _hash_chain_digest(ev, expected_prev) != ev.get("hash"):
                raise TamperDetectedError(
                    f"record {idx} ({ev.get('event_id')}) mutated (hash mismatch)"
                )
            prev_stored = ev.get("hash")
        return True


class InMemoryAuditStore(AuditStore):
    """Non-persistent audit store backed by a Python list."""

    def __init__(self) -> None:
        self._events: List[Dict[str, Any]] = []

    def _snapshot(self) -> List[Dict[str, Any]]:
        return self._events

    def _persist(self, event: Dict[str, Any]) -> None:
        self._events.append(event)


class JSONLAuditStore(AuditStore):
    """Persistent append-only JSON Lines audit store."""

    def __init__(self, path: "Path | str") -> None:
        self.path = Path(path)

    def _snapshot(self) -> List[Dict[str, Any]]:
        if not self.path.exists():
            return []
        events: List[Dict[str, Any]] = []
        with self.path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    events.append(json.loads(line))
        return events

    def _persist(self, event: Dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=False) + "\n")
            fh.flush()
            try:
                import os

                os.fsync(fh.fileno())
            except OSError:  # pragma: no cover - platform specific
                pass