"""Weather effects model for simulation realism."""

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
    change_interval: int = 50  # ticks between weather changes
    initial_condition: str = "clear"  # clear, cloudy, rain, fog, storm


class WeatherModel(WorldModel):
    """Weather effects model.

    Affects:
    - Sensor detection range (fog/rain reduce visibility)
    - Weapon accuracy (wind, precipitation)
    - Agent movement speed (terrain becomes muddy)
    - Communication range (storm interference)
    """

    CONDITIONS = ["clear", "cloudy", "rain", "fog", "storm"]

    def __init__(self, config: Optional[WeatherConfig] = None):
        super().__init__(config or WeatherConfig())
        self._condition: str = "clear"
        self._wind_speed: float = 0.0
        self._precipitation: float = 0.0
        self._visibility: float = 1.0
        self._next_change: int = 0

    def initialize(self) -> None:
        self._condition = self.config.initial_condition
        self._next_change = self.config.change_interval
        self._apply_condition_effects()
        logger.info("Weather initialized: %s", self._condition)

    def update(self, dt: float) -> None:
        self._tick += 1
        if self._tick >= self._next_change:
            self._condition = np.random.choice(self.CONDITIONS)
            self._apply_condition_effects()
            self._next_change = self._tick + self.config.change_interval
            logger.debug("Weather changed to: %s", self._condition)

    def _apply_condition_effects(self) -> None:
        effects = {
            "clear": (0.0, 0.0, 1.0),
            "cloudy": (2.0, 0.1, 0.9),
            "rain": (5.0, 0.5, 0.6),
            "fog": (1.0, 0.3, 0.3),
            "storm": (15.0, 0.9, 0.2),
        }
        self._wind_speed, self._precipitation, self._visibility = effects.get(self._condition, (0, 0, 1))

    @property
    def condition(self) -> str:
        return self._condition

    @property
    def visibility_multiplier(self) -> float:
        return self._visibility

    def get_state(self) -> Dict[str, Any]:
        return {
            "condition": self._condition,
            "wind_speed": self._wind_speed,
            "precipitation": self._precipitation,
            "visibility": self._visibility,
        }

    def reset(self) -> None:
        super().reset()
        self.initialize()

