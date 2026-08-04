# Copyright (c) Ultrone Contributors. All rights reserved.
"""Synthetic Generator — generates synthetic datasets for experiments."""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("Ultrone.Datasets.Synthetic")


@dataclass
class SyntheticConfig:
    """Configuration for synthetic generation."""
    num_samples: int = 100
    num_features: int = 4
    seed: int = 42
    class_balance: bool = True
    feature_ranges: Dict[str, tuple] = field(default_factory=dict)


class SyntheticGenerator:
    """Generates synthetic datasets with configurable distributions."""

    def __init__(self, config: Optional[SyntheticConfig] = None):
        self.config = config or SyntheticConfig()
        self._rng = random.Random(self.config.seed)

    def generate(self, generator_fn: Optional[Callable[[random.Random], Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """Generate rows. If ``generator_fn`` is provided, use it per-row."""
        rows = []
        for _ in range(self.config.num_samples):
            if generator_fn is not None:
                rows.append(generator_fn(self._rng))
            else:
                rows.append(self._generate_row())
        return rows

    def _generate_row(self) -> Dict[str, Any]:
        row: Dict[str, Any] = {}
        for i in range(self.config.num_features):
            key = f"feature_{i}"
            if key in self.config.feature_ranges:
                lo, hi = self.config.feature_ranges[key]
                row[key] = self._rng.uniform(lo, hi)
            else:
                row[key] = self._rng.gauss(0, 1)
        if self.config.class_balance:
            row["label"] = self._rng.randint(0, 1)
        return row

    def generate_classification(self, n_classes: int = 2) -> List[Dict[str, Any]]:
        """Generate a balanced classification dataset."""
        rows = []
        per_class = self.config.num_samples // n_classes
        for cls in range(n_classes):
            for _ in range(per_class):
                row = {"label": cls}
                for i in range(self.config.num_features):
                    row[f"feature_{i}"] = self._rng.gauss(cls, 1.0)
                rows.append(row)
        return rows

    def get_stats(self) -> Dict[str, Any]:
        return {
            "type": "SyntheticGenerator",
            "config": {"num_samples": self.config.num_samples, "num_features": self.config.num_features},
        }
