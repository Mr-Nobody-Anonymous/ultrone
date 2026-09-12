"""ULTRONE Investigation - Intelligence briefing dossier and report generation."""
from __future__ import annotations

import time
from typing import Any, Dict, List
from packages.investigation.cases import Case
from packages.investigation.evidence import EvidenceItem


class ReportGenerator:
    """Generates structured intelligence dossiers in Markdown, HTML, or JSON format."""

    @staticmethod
    def generate_markdown(
        case: Case,
        evidence: List[EvidenceItem],
        findings_summary: str = "",
        ai_assessments: str = "",
    ) -> str:
        date_str = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(case.created_at))
        lines = [
            f"# OPERATIONAL DOSSIER: {case.title.upper()}",
            f"**Case ID**: `{case.case_id}`  ",
            f"**Classification**: `{case.classification.value}`  ",
            f"**Status**: `{case.status.value.upper()}`  ",
            f"**Lead Analyst**: `{case.lead_analyst}`  ",
            f"**Generated**: `{date_str}`  ",
            "",
            "## 1. Executive Summary",
            case.summary or "No executive summary provided.",
            "",
            "## 2. Key Findings",
            findings_summary or "Preliminary investigative analysis ongoing.",
            "",
            "## 3. Pinned Operational Entities",
            f"Total Pinned Assets: {len(case.pinned_entity_ids)}",
        ]
        for eid in case.pinned_entity_ids:
            lines.append(f"- **Asset**: `{eid}`")

        lines.extend([
            "",
            "## 4. Evidentiary Record",
            f"Total Evidence Items: {len(evidence)}",
        ])
        for idx, ev in enumerate(evidence, 1):
            lines.append(f"### 4.{idx}. {ev.title} (`{ev.evidence_type.value}`)")
            lines.append(f"- **Source Reference**: `{ev.source_ref}`")
            lines.append(f"- **Description**: {ev.description}")
            lines.append(f"- **Integrity Hash**: `{ev.sha256_hash}`")
            lines.append("")

        if ai_assessments:
            lines.extend([
                "## 5. Cognitive AI Tactical Appraisal",
                ai_assessments,
                "",
            ])

        lines.append("---")
        lines.append("*CONFIDENTIAL - ULTRONE Common Operating Platform Investigation Subsystem*")
        return "\n".join(lines)


__all__ = ["ReportGenerator"]
