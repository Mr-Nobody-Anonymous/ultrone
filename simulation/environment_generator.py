"""Procedural environment generation."""
from __future__ import annotations
from typing import Any, Dict, Optional
import numpy as np

class EnvironmentGenerator:
    def __init__(self, seed: int = 42) -> None:
        self._rng = np.random.default_rng(seed)
    def generate_terrain(self, width: int = 100, height: int = 100) -> np.ndarray:
        return self._rng.random((height, width))
    def generate_entities(self, count: int = 10) -> list:
        return [{"id": i, "x": float(self._rng.random()*100), "y": float(self._rng.random()*100)} for i in range(count)]
