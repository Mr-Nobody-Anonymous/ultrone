"""Sensor uncertainty and degradation model."""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .base import WorldModel, WorldModelConfig

logger = logging.getLogger("Ultrone.Sim.WorldModeling.SensorUncertainty")


@dataclass
class SensorUncertaintyConfig(WorldModelConfig):
    """Configuration for sensor uncertainty model."""
    base_noise_std: float = 0.05
    degradation_rate: float = 0.001
    jamming_probability: float = 0.1


class SensorUncertaintyModel(WorldModel):
    """Models sensor noise, degradation, and jamming effects.

    Applies realistic uncertainty to sensor readings based on:
    - Distance to target
    - Environmental conditions
    - Sensor health/degradation
    - Electronic warfare (jamming)
    """

    def __init__(self, config: Optional[SensorUncertaintyConfig] = None):
        super().__init__(config or SensorUncertaintyConfig())
        self._noise_std: float = 0.05
        self._jamming_active: bool = False

    def initialize(self) -> None:
        self._noise_std = self.config.base_noise_std
        self._jamming_active = False
        logger.info("Sensor uncertainty model initialized")

    def update(self, dt: float) -> None:
        self._tick += 1
        # Gradual sensor degradation over time
        self._noise_std = min(0.3, self._noise_std + self.config.degradation_rate)
        # Random jamming events
        if np.random.random() < self.config.jamming_probability:
            self._jamming_active = not self._jamming_active

    def apply_noise(self, measurement: np.ndarray, distance: float) -> np.ndarray:
        """Apply distance-dependent noise to a sensor measurement."""
        distance_factor = 1.0 + 0.1 * distance
        jam_factor = 3.0 if self._jamming_active else 1.0
        noise = np.random.randn(*measurement.shape) * self._noise_std * distance_factor * jam_factor
        return measurement + noise

    def get_state(self) -> Dict[str, Any]:
        return {
            "noise_std": self._noise_std,
            "jamming_active": self._jamming_active,
        }

