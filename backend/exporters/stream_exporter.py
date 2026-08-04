"""
Argus — Stream Exporter
=======================
Exports records to streaming destinations (stdout, sockets, message queues).
"""

from __future__ import annotations

import json
import sys
from typing import Any, Dict, Iterable, List, Optional, TextIO

from .base import ExportConfig, ExportResult, Exporter


class StreamExporter(Exporter):
    """Exports records to a text stream (default: stdout)."""

    name = "stream"

    def __init__(
        self,
        config: Optional[ExportConfig] = None,
        *,
        stream: Optional[TextIO] = None,
        format: str = "json",
    ) -> None:
        super().__init__(config)
        self._stream = stream or sys.stdout
        self._format = format

    def export(
        self,
        records: Iterable[Dict[str, Any]],
        *,
        destination: Optional[str] = None,
    ) -> ExportResult:
        """Export records to the configured stream."""
        normalized = self.validate_records(records)
        if not normalized:
            return ExportResult(
                exporter=self.name,
                records_written=0,
                destination=destination or self.config.destination,
            ).complete()

        for record in normalized:
            if self._format == "json":
                self._stream.write(json.dumps(record, default=str) + "\n")
            elif self._format == "kv":
                parts = [f"{k}={v}" for k, v in record.items()]
                self._stream.write(" ".join(parts) + "\n")
            else:
                self._stream.write(str(record) + "\n")

        self._stream.flush()

        return ExportResult(
            exporter=self.name,
            records_written=len(normalized),
            destination=destination or self.config.destination,
        ).complete()

    def export_one(self, record: Dict[str, Any]) -> ExportResult:
        return self.export([record])