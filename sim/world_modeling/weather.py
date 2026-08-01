"""Weather model for battlefield simulation."""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .base import WorldModel, WorldModelConfig

logger = logging.getLogger("Ultrone.Sim.WorldModeling.Weather")


@dataclass
class WeatherConfig(WorldModelConfig):
    """Configuration for weather model."""
    initial_condition: str = "clear"
    change_probability: float = 0.05


class WeatherModel(WorldModel):
    """Weather model for battlefield conditions.

    Simulates weather conditions that affect visibility, sensor accuracy,
    and movement. Supports clear, cloudy, rainy, foggy, and stormy conditions.
    """

    CONDITIONS = ["clear", "cloudy", "rainy", "foggy", "stormy"]
    
    # Transition matrix: probability of transitioning from one condition to another
    # Rows: current, Columns: next
    TRANSITION_MATRIX = np.array([
        [0.85, 0.10, 0.03, 0.02, 0.00],  # clear
        [0.15, 0.70, 0.10, 0.03, 0.02],  # cloudy
        [0.05, 0.15, 0.70, 0.05, 0.05],  # rainy
        [0.10, 0.10, 0.05, 0.70, 0.05],  # foggy
        [0.00, 0.05, 0.20, 0.05, 0.70],  # stormy
    ])

    def __init__(self, config: Optional[WeatherConfig] = None):
        super().__init__(config or WeatherConfig())
        self._condition: str = self.config.initial_condition if hasattr(self.config, 'initial_condition') else "clear"

    def update(self, dt: float) -> None:
        """Advance weather by one time step."""
        self._tick += 1
        if np.random.random() < self.config.change_probability:
            idx = self.CONDITIONS.index(self._condition)
            probs = self.TRANSITION_MATRIX[idx]
            self._condition = np.random.choice(self.CONDITIONS, p=probs)

    def get_state(self) -> Dict[str, Any]:
        return {
            "condition": self._condition,
            "visibility_modifier": self._get_visibility_modifier(),
            "sensor_modifier": self._get_sensor_modifier(),
        }

    def _get_visibility_modifier(self) -> float:
        modifiers = {"clear": 1.0, "cloudy": 0.8, "rainy": 0.5, "foggy": 0.3, "stormy": 0.2}
        return modifiers.get(self._condition, 1.0)

    def _get_sensor_modifier(self) -> float:
        modifiers = {"clear": 1.0, "cloudy": 0.9, "rainy": 0.6, "foggy": 0.4, "stormy": 0.3}
        return modifiers.get(self._condition, 1.0)
