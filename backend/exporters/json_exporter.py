"""
Argus — JSON Exporter
=====================
Exports records to JSON files (single object or JSONL streaming).
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Iterable, List, Optional

from .base import ExportConfig, ExportResult, Exporter


class JSONExporter(Exporter):
    """Exports records to JSON or JSONL format."""

    name = "json"

    def __init__(
        self,
        config: Optional[ExportConfig] = None,
        *,
        lines: bool = False,
        indent: Optional[int] = 2,
    ) -> None:
        super().__init__(config)
        self._lines = lines
        self._indent = indent

    def export(
        self,
        records: Iterable[Dict[str, Any]],
        *,
        destination: Optional[str] = None,
    ) -> ExportResult:
        """Export records to a JSON file."""
        dest = destination or self.config.destination
        if not dest:
            raise ValueError("JSON exporter requires a destination path")

        normalized = self.validate_records(records)
        if not normalized:
            return ExportResult(
                exporter=self.name,
                records_written=0,
                destination=dest,
            ).complete()

        mode = "w" if self.config.overwrite else "a"
        with open(dest, mode, encoding="utf-8") as f:
            if self._lines:
                # JSONL: one record per line.
                for record in normalized:
                    f.write(json.dumps(record, default=str) + "\n")
            else:
                # Single JSON array.
                if self.config.overwrite or not os.path.exists(dest):
                    json.dump(normalized, f, indent=self._indent, default=str)
                else:
                    # Append mode: read existing, extend, rewrite.
                    f.close()
                    with open(dest, "r", encoding="utf-8") as rf:
                        try:
                            existing = json.load(rf)
                        except (json.JSONDecodeError, ValueError):
                            existing = []
                    if not isinstance(existing, list):
                        existing = [existing]
                    existing.extend(normalized)
                    with open(dest, "w", encoding="utf-8") as wf:
                        json.dump(existing, wf, indent=self._indent, default=str)

        return ExportResult(
            exporter=self.name,
            records_written=len(normalized),
            destination=dest,
        ).complete()

    def export_one(self, record: Dict[str, Any]) -> ExportResult:
        return self.export([record])