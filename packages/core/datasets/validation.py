# Copyright (c) Ultrone Contributors. All rights reserved.
"""Dataset Validator — schema validation, missing-value checks, and
deduplication."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Ultrone.Datasets.Validation")


@dataclass
class ValidationConfig:
    """Configuration for validation."""
    required_fields: List[str] = None
    max_missing_ratio: float = 0.1
    deduplicate: bool = True

    def __post_init__(self):
        if self.required_fields is None:
            self.required_fields = []


class DatasetValidator:
    """Validates dataset quality and deduplicates rows."""

    def __init__(self, config: Optional[ValidationConfig] = None):
        self.config = config or ValidationConfig()

    def validate(self, rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate a dataset and return a report."""
        report = {
            "total_rows": len(rows),
            "missing_values": {},
            "missing_ratio": 0.0,
            "duplicates": 0,
            "missing_fields": [],
            "valid": True,
        }

        if self.config.required_fields:
            for field in self.config.required_fields:
                missing = sum(1 for r in rows if field not in r or r.get(field) is None)
                report["missing_values"][field] = missing
                if missing / max(len(rows), 1) > self.config.max_missing_ratio:
                    report["missing_fields"].append(field)
                    report["valid"] = False

        if self.config.deduplicate:
            report["duplicates"] = self._count_duplicates(rows)

        return report

    def deduplicate(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate rows."""
        seen = set()
        unique = []
        for row in rows:
            key = tuple(sorted((k, str(v)) for k, v in row.items()))
            if key not in seen:
                seen.add(key)
                unique.append(row)
        return unique

    def _count_duplicates(self, rows: List[Dict[str, Any]]) -> int:
        seen = set()
        count = 0
        for row in rows:
            key = tuple(sorted((k, str(v)) for k, v in row.items()))
            if key in seen:
                count += 1
            else:
                seen.add(key)
        return count

    def get_stats(self) -> Dict[str, Any]:
        return {"type": "DatasetValidator", "required_fields": len(self.config.required_fields)}
