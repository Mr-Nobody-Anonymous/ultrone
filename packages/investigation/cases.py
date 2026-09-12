# Copyright (c) Ultrone Contributors. All rights reserved.
"""Investigation and Case Management Primitives.

Supports intelligence dossiers, evidence collections, annotations,
and investigative reporting.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class EvidenceItem:
    """An item of evidence linked to an investigation."""
    evidence_id: str = field(default_factory=lambda: f"ev_{uuid.uuid4().hex[:6]}")
    item_type: str = "entity"       # 'entity', 'event', 'telemetry', 'ai_trace', 'note'
    title: str = ""
    description: str = ""
    source_ref: str = ""           # Entity ID or Event ID
    confidence: float = 1.0
    payload: Dict[str, Any] = field(default_factory=dict)
    added_at: float = field(default_factory=time.time)


@dataclass
class Case:
    """An investigation case file."""
    case_id: str = field(default_factory=lambda: f"INV-{uuid.uuid4().hex[:4].upper()}")
    title: str = ""
    classification: str = "CONFIDENTIAL"
    status: str = "active"         # 'active', 'pending_review', 'closed'
    lead_analyst: str = "Operator_Alpha"
    hypotheses: List[str] = field(default_factory=list)
    evidence: List[EvidenceItem] = field(default_factory=list)
    pinned_entities: List[str] = field(default_factory=list)
    annotations: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def add_evidence(self, item: EvidenceItem) -> None:
        self.evidence.append(item)
        self.updated_at = time.time()

    def pin_entity(self, entity_id: str) -> None:
        if entity_id not in self.pinned_entities:
            self.pinned_entities.append(entity_id)
            self.updated_at = time.time()

    def generate_dossier(self) -> str:
        """Generate structured markdown report."""
        lines = [
            f"# INVESTIGATION DOSSIER: {self.case_id} — {self.title}",
            f"**Classification**: {self.classification} | **Status**: {self.status.upper()} | **Lead**: {self.lead_analyst}",
            f"**Last Updated**: {time.ctime(self.updated_at)}",
            "",
            "## Hypotheses & Operational Context",
        ]
        for h in self.hypotheses:
            lines.append(f"- {h}")
        lines.append("")
        lines.append(f"## Pinned Entity Contacts ({len(self.pinned_entities)})")
        for ent in self.pinned_entities:
            lines.append(f"- Contact ID: `{ent}`")
        lines.append("")
        lines.append(f"## Collected Evidence ({len(self.evidence)} items)")
        for ev in self.evidence:
            lines.append(f"- [{ev.item_type.upper()}] **{ev.title}**: {ev.description} (Ref: `{ev.source_ref}`)")
        return "\n".join(lines)
