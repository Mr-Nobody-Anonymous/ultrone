"""ULTRONE Investigation - Operator notes, analyst hypotheses, and tactical markup."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Hypothesis:
    """An analytical hypothesis tested against evidentiary facts."""
    hypothesis_id: str
    case_id: str
    statement: str
    status: str = "open"  # 'open', 'supported', 'refuted', 'inconclusive'
    supporting_evidence_ids: List[str] = field(default_factory=list)
    refuting_evidence_ids: List[str] = field(default_factory=list)
    analyst_confidence: float = 0.5
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hypothesis_id": self.hypothesis_id,
            "case_id": self.case_id,
            "statement": self.statement,
            "status": self.status,
            "supporting_evidence_ids": self.supporting_evidence_ids,
            "refuting_evidence_ids": self.refuting_evidence_ids,
            "analyst_confidence": self.analyst_confidence,
            "created_at": self.created_at,
        }


@dataclass
class Annotation:
    """An analyst markup note attached to a coordinate, entity, or timestamp."""
    annotation_id: str
    case_id: str
    author: str
    text: str
    target_type: str  # 'entity', 'coordinate', 'time_interval', 'polygon'
    target_id: Optional[str] = None
    coordinates: Optional[List[float]] = None
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "annotation_id": self.annotation_id,
            "case_id": self.case_id,
            "author": self.author,
            "text": self.text,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "coordinates": self.coordinates,
            "created_at": self.created_at,
        }


__all__ = ["Hypothesis", "Annotation"]
