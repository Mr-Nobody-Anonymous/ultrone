"""
Argus — CSV Exporter
====================
Exports records to CSV files with proper escaping and batching.
"""

from __future__ import annotations

import csv
import os
from typing import Any, Dict, Iterable, List, Optional

from .base import ExportConfig, ExportResult, Exporter


class CSVExporter(Exporter):
    """Exports records to CSV format."""

    name = "csv"

    def __init__(self, config: Optional[ExportConfig] = None) -> None:
        super().__init__(config)
        self._fieldnames: Optional[List[str]] = None

    def export(
        self,
        records: Iterable[Dict[str, Any]],
        *,
        destination: Optional[str] = None,
    ) -> ExportResult:
        """Export records to a CSV file."""
        dest = destination or self.config.destination
        if not dest:
            raise ValueError("CSV exporter requires a destination path")

        normalized = self.validate_records(records)
        if not normalized:
            return ExportResult(
                exporter=self.name,
                records_written=0,
                destination=dest,
            ).complete()

        # Collect all field names.
        fieldnames: List[str] = []
        for record in normalized:
            for key in record:
                if key not in fieldnames:
                    fieldnames.append(key)

        mode = "w" if self.config.overwrite else "a"
        write_header = self.config.overwrite or not os.path.exists(dest)

        with open(dest, mode, newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            if write_header:
                writer.writeheader()
            for record in normalized:
                writer.writerow(record)

        return ExportResult(
            exporter=self.name,
            records_written=len(normalized),
            destination=dest,
        ).complete()

    def export_one(self, record: Dict[str, Any]) -> ExportResult:
        return self.export([record])