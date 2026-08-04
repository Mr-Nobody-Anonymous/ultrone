# Copyright (c) Ultrone Contributors. All rights reserved.
"""Augmenter — data augmentation strategies for expanding datasets."""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Ultrone.Datasets.Augmentation")


@dataclass
class AugmentationConfig:
    """Configuration for augmentation."""
    noise_scale: float = 0.05
    seed: int = 42
    strategy: str = "noise"       # noise, jitter, mixup


class Augmenter:
    """Generates augmented variants of dataset rows."""

    def __init__(self, config: Optional[AugmentationConfig] = None):
        self.config = config or AugmentationConfig()
        self._rng = random.Random(self.config.seed)
        self._augmented = 0

    def augment(self, rows: List[Dict[str, Any]], factor: int = 2) -> List[Dict[str, Any]]:
        """Return the original rows plus augmented variants."""
        result = list(rows)
        for _ in range(max(0, factor - 1)):
            for row in rows:
                variant = self._augment_row(row)
                if variant is not None:
                    result.append(variant)
                    self._augmented += 1
        return result

    def _augment_row(self, row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if self.config.strategy == "noise":
            return self._add_noise(row)
        if self.config.strategy == "jitter":
            return self._jitter(row)
        if self.config.strategy == "mixup":
            return self._mixup(row)
        return None

    def _add_noise(self, row: Dict[str, Any]) -> Dict[str, Any]:
        new_row = dict(row)
        for key, val in row.items():
            if isinstance(val, (int, float)):
                new_row[key] = val + self._rng.gauss(0, self.config.noise_scale)
        return new_row

    def _jitter(self, row: Dict[str, Any]) -> Dict[str, Any]:
        new_row = dict(row)
        for key, val in row.items():
            if isinstance(val, (int, float)):
                scale = self.config.noise_scale * max(abs(val), 1.0)
                new_row[key] = val + self._rng.uniform(-scale, scale)
        return new_row

    def _mixup(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Mixup-style: shuffle numeric feature values within the row."""
        new_row = dict(row)
        keys = [k for k, v in row.items() if isinstance(v, (int, float))]
        if keys:
            order = list(keys)
            self._rng.shuffle(order)
            for i, k in enumerate(keys):
                new_row[k] = row[order[i]]
        return new_row

    def get_stats(self) -> Dict[str, Any]:
        return {
            "type": "Augmenter",
            "strategy": self.config.strategy,
            "augmented_rows": self._augmented,
        }
