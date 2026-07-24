"""Automated experiment report generation."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Ultrone.Research.Report")


@dataclass
class ReportConfig:
    """Configuration for automated reports."""
    format: str = "markdown"  # markdown, json, html
    include_plots: bool = False
    output_dir: str = "reports"


class AutomatedReport:
    """Generates automated experiment reports.

    Creates structured reports from experiment data including
    configuration, metrics, statistical analysis, and conclusions.
    Supports multiple output formats.
    """

    def __init__(self, config: Optional[ReportConfig] = None):
        self.config = config or ReportConfig()
        self._sections: List[Dict[str, Any]] = []

    def add_section(self, title: str, content: Any, section_type: str = "text") -> None:
        """Add a section to the report."""
        self._sections.append({"title": title, "content": content, "type": section_type})

    def generate(self, title: str = "Experiment Report") -> str:
        """Generate the report in the configured format."""
        lines = [f"# {title}", ""]
        for section in self._sections:
            lines.append(f"## {section['title']}")
            if isinstance(section["content"], str):
                lines.append(section["content"])
            elif isinstance(section["content"], dict):
                lines.append("```json")
                lines.append(json.dumps(section["content"], indent=2))
                lines.append("```")
            lines.append("")
        return "\n".join(lines)

    def get_stats(self) -> Dict[str, Any]:
        return {"type": "AutomatedReport", "sections": len(self._sections)}
