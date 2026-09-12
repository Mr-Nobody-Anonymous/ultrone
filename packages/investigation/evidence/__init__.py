"""ULTRONE Investigation - Evidence collection, items, and chain-of-custody tracking."""
from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class EvidenceType(str, Enum):
    ENTITY_RECORD = "entity_record"
    SENSOR_CLIP = "sensor_clip"
    GEO_POLYGON = "geo_polygon"
    AI_REASONING_TRACE = "ai_reasoning_trace"
    DOCUMENT = "document"
    TELEMETRY_SAMPLE = "telemetry_sample"


import uuid

@dataclass
class EvidenceItem:
    """An evidentiary artifact attached to an investigative case."""
    title: str = ""
    description: str = ""
    source_ref: str = ""
    evidence_id: str = field(default_factory=lambda: f"ev_{uuid.uuid4().hex[:6]}")
    case_id: str = ""
    evidence_type: EvidenceType = EvidenceType.ENTITY_RECORD
    item_type: str = "entity"
    payload: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    submitted_by: str = "analyst"
    timestamp: float = field(default_factory=time.time)
    added_at: float = field(default_factory=time.time)
    sha256_hash: str = ""

    def __post_init__(self):
        if not self.sha256_hash:
            raw = f"{self.evidence_id}:{self.case_id}:{self.source_ref}:{self.timestamp}"
            self.sha256_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "case_id": self.case_id,
            "evidence_type": self.evidence_type.value,
            "title": self.title,
            "description": self.description,
            "source_ref": self.source_ref,
            "payload": self.payload,
            "submitted_by": self.submitted_by,
            "timestamp": self.timestamp,
            "sha256_hash": self.sha256_hash,
        }


class EvidenceBoard:
    """Board grouping evidence items for an investigation."""

    def __init__(self, case_id: str):
        self.case_id = case_id
        self._items: Dict[str, EvidenceItem] = {}

    def attach_evidence(self, item: EvidenceItem) -> None:
        self._items[item.evidence_id] = item

    def get_items(self) -> List[EvidenceItem]:
        return list(self._items.values())

    def remove_evidence(self, evidence_id: str) -> None:
        self._items.pop(evidence_id, None)


__all__ = ["EvidenceType", "EvidenceItem", "EvidenceBoard"]
