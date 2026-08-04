"""
Argus — Exporter Base Classes
=============================
Abstract exporter protocol with typed configuration and result models.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional


@dataclass
class ExportConfig:
    """Base configuration for an exporter."""

    destination: str = ""
    overwrite: bool = False
    include_metadata: bool = True
    batch_size: int = 1000
    compression: str = "auto"


@dataclass
class ExportResult:
    """Result of an export operation."""

    export_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    exporter: str = ""
    records_written: int = 0
    destination: str = ""
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def complete(self) -> "ExportResult":
        self.completed_at = datetime.utcnow()
        self.duration_seconds = (self.completed_at - self.started_at).total_seconds()
        return self


class Exporter(ABC):
    """Abstract base class for all exporters."""

    name: str = "base"

    def __init__(self, config: Optional[ExportConfig] = None) -> None:
        self.config = config or ExportConfig()

    @abstractmethod
    def export(
        self,
        records: Iterable[Dict[str, Any]],
        *,
        destination: Optional[str] = None,
    ) -> ExportResult:
        """Export records to the configured destination."""
        ...

    @abstractmethod
    def export_one(self, record: Dict[str, Any]) -> ExportResult:
        """Export a single record."""
        ...

    def validate_records(
        self, records: Iterable[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Validate and normalize records before export."""
        normalized: List[Dict[str, Any]] = []
        for record in records:
            if not isinstance(record, dict):
                continue
            normalized.append(dict(record))
        return normalized

    def close(self) -> None:
        """Release any resources held by the exporter."""
        pass


class BatchExporter(Exporter):
    """Exporter that accumulates records and exports in batches."""

    def __init__(self, config: Optional[ExportConfig] = None) -> None:
        super().__init__(config)
        self._buffer: List[Dict[str, Any]] = []
        self._total_written: int = 0

    def flush(self) -> ExportResult:
        """Flush buffered records."""
        if not self._buffer:
            return ExportResult(
                exporter=self.name,
                records_written=0,
                destination=self.config.destination,
            ).complete()
        result = self.export(self._buffer)
        self._buffer.clear()
        self._total_written += result.records_written
        return result

    def export_one(self, record: Dict[str, Any]) -> ExportResult:
        self._buffer.append(record)
        if len(self._buffer) >= self.config.batch_size:
            return self.flush()
        return ExportResult(
            exporter=self.name,
            records_written=1,
            destination=self.config.destination,
        )

    @property
    def total_written(self) -> int:
        return self._total_written