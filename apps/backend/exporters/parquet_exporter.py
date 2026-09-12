"""
Argus — Parquet Exporter
========================
Exports records to Apache Parquet format for efficient columnar storage.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from .base import ExportConfig, ExportResult, Exporter


class ParquetExporter(Exporter):
    """Exports records to Parquet format using pyarrow if available."""

    name = "parquet"

    def __init__(self, config: Optional[ExportConfig] = None) -> None:
        super().__init__(config)
        self._pyarrow = None
        try:
            import pyarrow  # type: ignore
            self._pyarrow = pyarrow
        except ImportError:
            pass

    def export(
        self,
        records: Iterable[Dict[str, Any]],
        *,
        destination: Optional[str] = None,
    ) -> ExportResult:
        """Export records to a Parquet file."""
        dest = destination or self.config.destination
        if not dest:
            raise ValueError("Parquet exporter requires a destination path")

        normalized = self.validate_records(records)
        if not normalized:
            return ExportResult(
                exporter=self.name,
                records_written=0,
                destination=dest,
            ).complete()

        if self._pyarrow is None:
            raise ImportError("pyarrow is required for Parquet export")

        table = self._pyarrow.Table.from_pylist(normalized)
        self._pyarrow.parquet.write_table(table, dest)

        return ExportResult(
            exporter=self.name,
            records_written=len(normalized),
            destination=dest,
        ).complete()

    def export_one(self, record: Dict[str, Any]) -> ExportResult:
        return self.export([record])