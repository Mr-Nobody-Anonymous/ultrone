# Copyright (c) Ultrone Contributors. All rights reserved.
"""Battlefield environment model with weather and visibility effects."""

import random
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Optional

from ..data.terrain import Terrain, TerrainType

logger = logging.getLogger("Ultrone.Sim.Environment")


class WeatherCondition(Enum):
    """Weather conditions affecting sensors and movement."""
    CLEAR = "clear"
    PARTLY_CLOUDY = "partly_cloudy"
    OVERCAST = "overcast"
    LIGHT_RAIN = "light_rain"
    HEAVY_RAIN = "heavy_rain"
    FOG = "fog"
    SANDSTORM = "sandstorm"
    SNOW = "snow"


@dataclass
class VisibilityReport:
    """Current visibility conditions for the battlefield."""
    visibility_km: float  # Visual visibility at ground level
    sensor_degradation: float  # Multiplier for sensor effectiveness (0.0-1.0)
    movement_penalty: float  # Multiplier for movement speed (0.0-1.0)
    weather: WeatherCondition
    wind_speed_kmh: float
    
    def to_dict(self) -> dict:
        return {
            "visibility_km": self.visibility_km,
            "sensor_degradation": self.sensor_degradation,
            "movement_penalty": self.movement_penalty,
            "weather": self.weather.value,
            "wind_speed_kmh": self.wind_speed_kmh,
        }


class Environment:
    """
    Environmental conditions for the battlefield.
    
    Models weather, visibility, day/night cycle, and their effects on
    sensors, movement, and combat effectiveness.
    """
    
    def __init__(
        self,
        terrain: Optional[Terrain] = None,
        width_km: float = 100.0,
        height_km: float = 100.0,
    ):
        self.terrain = terrain or Terrain(width_meters=int(width_km * 1000), height_meters=int(height_km * 1000))
        self.width_km = width_km
        self.height_km = height_km
        
        # Time-of-day affects visibility and sensor effectiveness
        self.day_duration_ticks = 120  # Half day
        self.current_tick = 0
        
        # Weather state
        self._weather = WeatherCondition.CLEAR
        self._wind_speed = 10.0
        self._visibility = 20.0  # km
        
        # Cached visibility report
        self._visibility_cache: Optional[VisibilityReport] = None
        self._cache_tick: int = -1
    
    def update(self, tick: int) -> VisibilityReport:
        """Update environment for a given tick and return visibility report."""
        self.current_tick = tick
        
        # Weather changes slowly
        if random.random() < 0.01:  # 1% chance per tick
            self._weather = random.choice(list(WeatherCondition))
            self._visibility_cache = None
        
        # Wind varies more quickly
        self._wind_speed = max(0, min(100, self._wind_speed + random.uniform(-5, 5)))
        
        return self.get_visibility()
    
    def get_visibility(self) -> VisibilityReport:
        """Get current visibility conditions."""
        if self._visibility_cache and self._cache_tick == self.current_tick:
            return self._visibility_cache
        
        # Base values
        visibility = self._visibility
        sensor_deg = 1.0
        movement_penalty = 1.0
        
        # Weather effects
        weather_effects = {
            WeatherCondition.CLEAR: (30.0, 1.0, 1.0),
            WeatherCondition.PARTLY_CLOUDY: (20.0, 0.95, 0.98),
            WeatherCondition.OVERCAST: (15.0, 0.9, 0.95),
            WeatherCondition.LIGHT_RAIN: (10.0, 0.85, 0.9),
            WeatherCondition.HEAVY_RAIN: (5.0, 0.7, 0.8),
            WeatherCondition.FOG: (1.0, 0.5, 0.7),
            WeatherCondition.SANDSTORM: (0.5, 0.3, 0.6),
            WeatherCondition.SNOW: (8.0, 0.75, 0.85),
        }
        
        base_vis, base_sensor, base_move = weather_effects.get(self._weather, (20.0, 1.0, 1.0))
        
        # Day/night cycle
        time_of_day = (self.current_tick % self.day_duration_ticks) / self.day_duration_ticks
        if 0.25 < time_of_day < 0.75:  # Daytime
            pass  # Full visibility
        else:  # Nighttime
            base_vis *= 0.2
            base_sensor *= 0.7
        
        # Wind effects on aerial sensors
        if self._wind_speed > 50:
            base_sensor *= 0.95
        
        self._visibility_cache = VisibilityReport(
            visibility_km=base_vis,
            sensor_degradation=base_sensor,
            movement_penalty=movement_penalty,
            weather=self._weather,
            wind_speed_kmh=self._wind_speed,
        )
        self._cache_tick = self.current_tick
        
        return self._visibility_cache
    
    def is_day(self) -> bool:
        """Check if it's daytime."""
        time_of_day = (self.current_tick % self.day_duration_ticks) / self.day_duration_ticks
        return 0.25 < time_of_day < 0.75
    
    def get_time_of_day(self) -> str:
        """Get time of day string."""
        time_of_day = (self.current_tick % self.day_duration_ticks) / self.day_duration_ticks
        if 0.2 < time_of_day < 0.3:
            return "dawn"
        elif 0.25 < time_of_day < 0.75:
            return "day"
        elif 0.7 < time_of_day < 0.8:
            return "dusk"
        else:
            return "night"
    
    def get_stats(self) -> dict:
        """Get environment statistics."""
        vis = self.get_visibility()
        return {
            "weather": vis.weather.value,
            "visibility_km": vis.visibility_km,
            "wind_speed_kmh": vis.wind_speed_kmh,
            "time_of_day": self.get_time_of_day(),
            "terrain_size": f"{self.terrain.get_width_cells()}x{self.terrain.get_height_cells()}",
        }