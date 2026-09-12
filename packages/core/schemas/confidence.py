# Copyright (c) Ultrone Contributors. All rights reserved.
"""Confidence scoring, Bayesian uncertainty, and threshold schemas."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ConfidenceBand(str, Enum):
    HIGH = "high"          # >= 0.85
    NOMINAL = "nominal"    # 0.65 - 0.84
    LOW = "low"            # 0.45 - 0.64
    UNRELIABLE = "unreliable" # < 0.45


@dataclass
class ConfidenceScore:
    value: float = 1.0
    prior: float = 0.5
    sample_count: int = 1
    uncertainty: float = 0.0

    @property
    def band(self) -> ConfidenceBand:
        if self.value >= 0.85:
            return ConfidenceBand.HIGH
        if self.value >= 0.65:
            return ConfidenceBand.NOMINAL
        if self.value >= 0.45:
            return ConfidenceBand.LOW
        return ConfidenceBand.UNRELIABLE
