# Copyright (c) Ultrone Contributors. All rights reserved.
"""Dataset Metadata — computes statistics and stores metadata for datasets."""

from __future__ import annotations

import logging
import statistics
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Ultrone.Datasets.Metadata")


@dataclass
class DatasetMetadata:
    """Computed metadata for a dataset."""
    name: str = ""
    num_rows: int = 0
    num_columns: int = 0
    column_types: Dict[str, str] = field(default_factory=dict)
    column_stats: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    null_counts: Dict[str, int] = field(default_factory=dict)

    @classmethod
    def compute(cls, rows: List[Dict[str, Any]], name: str = "") -> "DatasetMetadata":
        """Compute metadata from a list of rows."""
        md = cls(name=name)
        if not rows:
            return md
        md.num_rows = len(rows)
        columns = sorted({k for r in rows for k in r})
        md.num_columns = len(columns)
        for col in columns:
            values = [r.get(col) for r in rows]
            md.column_types[col] = _infer_type(values)
            md.null_counts[col] = sum(1 for v in values if v is None)
            numeric = [v for v in values if isinstance(v, (int, float))]
            if numeric:
                md.column_stats[col] = {
                    "mean": statistics.mean(numeric),
                    "min": min(numeric),
                    "max": max(numeric),
                }
        return md

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name, "num_rows": self.num_rows, "num_columns": self.num_columns,
            "column_types": self.column_types, "column_stats": self.column_stats,
            "null_counts": self.null_counts,
        }


class MetadataStore:
    """Registry of dataset metadata."""

    def __init__(self):
        self._metadata: Dict[str, DatasetMetadata] = {}

    def store(self, dataset_id: str, metadata: DatasetMetadata) -> None:
        self._metadata[dataset_id] = metadata

    def get(self, dataset_id: str) -> Optional[DatasetMetadata]:
        return self._metadata.get(dataset_id)

    def list_all(self) -> List[DatasetMetadata]:
        return list(self._metadata.values())

    def get_stats(self) -> Dict[str, Any]:
        return {"type": "MetadataStore", "datasets": len(self._metadata)}


def _infer_type(values: List[Any]) -> str:
    types = {type(v).__name__ for v in values if v is not None}
    if not types:
        return "empty"
    if types <= {"int"}:
        return "int"
    if types <= {"int", "float"}:
        return "float"
    if types <= {"str"}:
        return "str"
    return "mixed"
