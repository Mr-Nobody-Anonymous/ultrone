"""ULTRONE Investigation - Cases and operational dossier management."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class CaseStatus(str, Enum):
    OPEN = "open"
    ACTIVE = "active"
    PENDING_REVIEW = "pending_review"
    CLOSED = "closed"
    ARCHIVED = "archived"


class ClassificationLevel(str, Enum):
    UNCLASSIFIED = "UNCLASSIFIED"
    RESTRICTED = "RESTRICTED"
    CONFIDENTIAL = "CONFIDENTIAL"
    SECRET = "SECRET"


@dataclass
class Case:
    """Operational case container holding correlated entities, evidence, and notes."""
    case_id: str
    title: str
    lead_analyst: str = "Lead Analyst"
    classification: ClassificationLevel = ClassificationLevel.UNCLASSIFIED
    status: CaseStatus = CaseStatus.OPEN
    summary: str = ""
    pinned_entity_ids: List[str] = field(default_factory=list)
    pinned_event_ids: List[str] = field(default_factory=list)
    evidence: List[Any] = field(default_factory=list)
    hypotheses: List[str] = field(default_factory=list)
    annotations: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    @property
    def pinned_entities(self) -> List[str]:
        return self.pinned_entity_ids

    def pin_entity(self, entity_id: str) -> None:
        if entity_id not in self.pinned_entity_ids:
            self.pinned_entity_ids.append(entity_id)
            self.updated_at = time.time()

    def add_evidence(self, item: Any) -> None:
        self.evidence.append(item)
        self.updated_at = time.time()

    def generate_dossier(self) -> str:
        cls_val = self.classification.value if hasattr(self.classification, "value") else str(self.classification)
        st_val = self.status.value if hasattr(self.status, "value") else str(self.status)
        lines = [
            f"# INVESTIGATION DOSSIER: {self.case_id} — {self.title}",
            f"**Classification**: {cls_val} | **Status**: {st_val.upper()} | **Lead**: {self.lead_analyst}",
            f"**Last Updated**: {time.ctime(self.updated_at)}",
            "",
            "## Hypotheses & Operational Context",
        ]
        if self.hypotheses:
            for h in self.hypotheses:
                lines.append(f"- {h}")
        else:
            lines.append("No active hypotheses recorded.")

        lines.extend(["", "## Pinned Entities"])
        for e in self.pinned_entity_ids:
            lines.append(f"- `{e}`")

        lines.extend(["", "## Evidentiary Items"])
        for ev in self.evidence:
            ev_title = getattr(ev, "title", "Evidence")
            ev_type = getattr(ev, "item_type", getattr(ev, "evidence_type", "item"))
            ev_desc = getattr(ev, "description", "")
            lines.append(f"### {ev_title} ({ev_type})")
            lines.append(f"{ev_desc}")
        return "\n".join(lines)

    def pin_event(self, event_id: str) -> None:
        if event_id not in self.pinned_event_ids:
            self.pinned_event_ids.append(event_id)
            self.updated_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "title": self.title,
            "lead_analyst": self.lead_analyst,
            "classification": self.classification.value,
            "status": self.status.value,
            "summary": self.summary,
            "pinned_entity_ids": self.pinned_entity_ids,
            "pinned_event_ids": self.pinned_event_ids,
            "tags": self.tags,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class CaseManager:
    """In-memory and persistent case management index."""

    def __init__(self):
        self._cases: Dict[str, Case] = {}

    def create_case(
        self,
        case_id: str,
        title: str,
        lead_analyst: str,
        summary: str = "",
        classification: ClassificationLevel = ClassificationLevel.UNCLASSIFIED,
    ) -> Case:
        case = Case(
            case_id=case_id,
            title=title,
            lead_analyst=lead_analyst,
            summary=summary,
            classification=classification,
        )
        self._cases[case_id] = case
        return case

    def get_case(self, case_id: str) -> Optional[Case]:
        return self._cases.get(case_id)

    def list_cases(self, status: Optional[CaseStatus] = None) -> List[Case]:
        if status:
            return [c for c in self._cases.values() if c.status == status]
        return list(self._cases.values())


__all__ = ["CaseStatus", "ClassificationLevel", "Case", "CaseManager"]
