"""ULTRONE Core Provenance - Cryptographic audit and verification."""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AuditRecord:
    """Tamper-evident record secured by a hash link to the previous record."""
    record_id: str
    event_type: str
    actor_id: str  # human operator or AI agent id
    payload: Dict[str, Any]
    prev_hash: str
    timestamp: float = field(default_factory=time.time)
    record_hash: str = ""

    def __post_init__(self):
        if not self.record_hash:
            canonical = json.dumps(
                {
                    "record_id": self.record_id,
                    "event_type": self.event_type,
                    "actor_id": self.actor_id,
                    "payload": self.payload,
                    "prev_hash": self.prev_hash,
                    "timestamp": self.timestamp,
                },
                sort_keys=True,
            )
            self.record_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "event_type": self.event_type,
            "actor_id": self.actor_id,
            "payload": self.payload,
            "prev_hash": self.prev_hash,
            "timestamp": self.timestamp,
            "record_hash": self.record_hash,
        }


class AuditVerifier:
    """Maintains and verifies an append-only cryptographic ledger of system state transitions."""

    def __init__(self, genesis_prev_hash: str = "0" * 64):
        self._records: List[AuditRecord] = []
        self._latest_hash: str = genesis_prev_hash

    def append(self, record_id: str, event_type: str, actor_id: str, payload: Dict[str, Any]) -> AuditRecord:
        record = AuditRecord(
            record_id=record_id,
            event_type=event_type,
            actor_id=actor_id,
            payload=payload,
            prev_hash=self._latest_hash,
        )
        self._records.append(record)
        self._latest_hash = record.record_hash
        return record

    def verify_integrity(self) -> bool:
        """Verify hash chain integrity across all records."""
        expected_prev = "0" * 64
        for r in self._records:
            if r.prev_hash != expected_prev:
                return False
            canonical = json.dumps(
                {
                    "record_id": r.record_id,
                    "event_type": r.event_type,
                    "actor_id": r.actor_id,
                    "payload": r.payload,
                    "prev_hash": r.prev_hash,
                    "timestamp": r.timestamp,
                },
                sort_keys=True,
            )
            computed = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            if computed != r.record_hash:
                return False
            expected_prev = r.record_hash
        return True

    def get_records(self) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in self._records]
