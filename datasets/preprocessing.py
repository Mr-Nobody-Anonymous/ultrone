# Copyright (c) Ultrone Contributors. All rights reserved.
"""Preprocessor — normalization, standardization, and cleaning of datasets."""

from __future__ import annotations

import logging
import statistics
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Ultrone.Datasets.Preprocessing")


@dataclass
class PreprocessingConfig:
    """Configuration for preprocessing."""
    normalize: bool = True
    standardize: bool = False
    fill_missing: bool = True
    fill_value: float = 0.0


class Preprocessor:
    """Applies preprocessing transforms to dataset rows."""

    def __init__(self, config: Optional[PreprocessingConfig] = None):
        self.config = config or PreprocessingConfig()
        self._stats: Dict[str, Dict[str, float]] = {}

    def fit(self, rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
        """Compute per-column statistics from rows."""
        columns = self._collect_columns(rows)
        stats: Dict[str, Dict[str, float]] = {}
        for col in columns:
            values = [r[col] for r in rows if isinstance(r.get(col), (int, float))]
            if values:
                stats[col] = {
                    "mean": statistics.mean(values),
                    "stddev": statistics.stdev(values) if len(values) > 1 else 1.0,
                    "min": min(values),
                    "max": max(values),
                }
            else:
                stats[col] = {"mean": 0.0, "stddev": 1.0, "min": 0.0, "max": 1.0}
        self._stats = stats
        return stats

    def transform(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply normalization/standardization using fitted stats."""
        if not self._stats:
            self.fit(rows)
        result = []
        for row in rows:
            new_row = dict(row)
            for col, col_stats in self._stats.items():
                val = new_row.get(col)
                if val is None:
                    if self.config.fill_missing:
                        new_row[col] = self.config.fill_value
                    continue
                if isinstance(val, (int, float)):
                    if self.config.standardize:
                        std = col_stats["stddev"] or 1.0
                        new_row[col] = (val - col_stats["mean"]) / std
                    elif self.config.normalize:
                        rng = (col_stats["max"] - col_stats["min"]) or 1.0
                        new_row[col] = (val - col_stats["min"]) / rng
            result.append(new_row)
        return result

    def fit_transform(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Fit statistics then transform."""
        self.fit(rows)
        return self.transform(rows)

    @staticmethod
    def _collect_columns(rows: List[Dict[str, Any]]) -> List[str]:
        cols: List[str] = []
        for row in rows:
            for key in row:
                if key not in cols:
                    cols.append(key)
        return cols

    def get_stats(self) -> Dict[str, Any]:
        return {
            "type": "Preprocessor",
            "columns_tracked": len(self._stats),
            "columns": list(self._stats.keys()),
        }



