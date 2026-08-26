# Copyright (c) Ultrone Contributors. All rights reserved.
"""Environment model, physics modifiers, and sensor simulation.

- ``EnvironmentModel``  -- terrain passability, deterministic weather
  (wind/rain/cloud), sea state from wind, atmospheric density by altitude.
- physics helpers       -- environment-adjusted effective speeds and
  pairwise collision checks for tracked platforms.
- ``SensorSuite``       -- radar / optical / sonar observation models with
  weather attenuation and detection probability by range.

All models are deliberately simple, closed-form, and exactly
reproducible -- appropriate for a sandbox where every number must be
explainable.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class Weather:
    base_wind: float = 6.0            # m/s
    gust_amplitude: float = 3.0
    period_ticks: float = 48.0
    cloud_cover: float = 0.3          # 0..1 constant ceiling fraction

    def wind_speed(self, tick: int) -> float:
        return round(self.base_wind + self.gust_amplitude * math.sin(
            2 * math.pi * tick / self.period_ticks), 3)

    def rain_intensity(self, tick: int) -> float:
        phase = (tick % int(self.period_ticks)) / self.period_ticks
        if not 0.25 <= phase <= 0.75:
            return 0.0
        return round(max(0.0, math.sin(math.pi * (phase - 0.25) * 2.0)), 3)

    def sea_state(self, tick: int) -> int:
        return min(9, max(0, int(self.wind_speed(tick) / 3.0)))


class TerrainGrid:
    """Coarse passability grid; hills slow surface movement."""

    CELL = 4.0

    def __init__(self, size: float = 64.0, seed: int = 0) -> None:
        self.size = size
        rng = random.Random(seed)
        n = max(1, int(size // self.CELL))
        self.hills = {(rng.randrange(n), rng.randrange(n))
                      for _ in range(max(1, n // 8))}

    def is_hill(self, x: float, y: float) -> bool:
        return (int(x // self.CELL), int(y // self.CELL)) in self.hills

    def slope_factor(self, x: float, y: float) -> float:
        return 0.7 if self.is_hill(x, y) else 1.0

    def in_bounds(self, x: float, y: float) -> bool:
        return 0.0 <= x <= self.size and 0.0 <= y <= self.size


class EnvironmentModel:
    """Terrain + weather + atmosphere + solar, all tick-deterministic."""

    def __init__(self, seed: int = 0, size: float = 64.0,
                 weather: Optional[Weather] = None) -> None:
        self.terrain = TerrainGrid(size=size, seed=seed)
        self.weather = weather or Weather()
        self.last_tick = 0

    def update(self, tick: int) -> None:
        self.last_tick = tick

    def wind(self, tick: Optional[int] = None) -> float:
        return self.weather.wind_speed(tick if tick is not None
                                       else self.last_tick)

    def rain(self, tick: Optional[int] = None) -> float:
        return self.weather.rain_intensity(tick if tick is not None
                                           else self.last_tick)

    def sea_state(self, tick: Optional[int] = None) -> int:
        return self.weather.sea_state(tick if tick is not None
                                      else self.last_tick)

    @staticmethod
    def atmosphere_density(altitude_m: float) -> float:
        return round(1.225 * math.exp(-max(0.0, altitude_m) / 8500.0), 5)

    @staticmethod
    def solar_irradiance(tick: int) -> float:
        phase = (tick % 24) / 24.0
        return round(max(0.0, math.sin(math.pi * phase)), 3)

    def effective_speed(self, speed: float, domain: str,
                        altitude_m: float = 0.0,
                        tick: Optional[int] = None) -> float:
        wind = self.wind(tick)
        if domain == "air":
            factor = 1.0 - min(0.5, 0.05 * wind + 0.2 * self.rain(tick))
            factor *= self.atmosphere_density(altitude_m) / 1.225
        elif domain == "sea":
            factor = 1.0 - min(0.6, 0.06 * self.sea_state(tick))
        else:
            factor = 1.0 - min(0.4, 0.04 * wind)
        return round(speed * max(0.25, factor), 4)


# --------------------------------------------------------------------- #
# Physics helpers                                                        #
# --------------------------------------------------------------------- #
def check_collisions(positions: Dict[str, Tuple[float, float]],
                     min_separation: float = 1.0) -> List[Tuple[str, str]]:
    ids = sorted(positions)
    colliding: List[Tuple[str, str]] = []
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            ax, ay = positions[a]
            bx, by = positions[b]
            if math.hypot(ax - bx, ay - by) < min_separation:
                colliding.append((a, b))
    return colliding


def kinematic_step(x: float, y: float, heading_rad: float,
                   linear: float, dt: float = 1.0) -> Tuple[float, float]:
    return (x + math.cos(heading_rad) * linear * dt,
            y + math.sin(heading_rad) * linear * dt)


# --------------------------------------------------------------------- #
# Sensors                                                                #
# --------------------------------------------------------------------- #
@dataclass
class Contact:
    contact_id: str
    kind: str
    x: float
    y: float


class SensorSuite:
    """Radar / optical / sonar observation models over known contacts."""

    def __init__(self, env: EnvironmentModel, seed: int = 0) -> None:
        self.env = env
        self.rng = random.Random(seed ^ 0x53E4)

    def radar_scan(self, own_x: float, own_y: float,
                   contacts: List[Contact], range_: float = 20.0,
                   tick: int = 0) -> List[Dict[str, Any]]:
        rain = self.env.rain(tick)
        detections: List[Dict[str, Any]] = []
        for c in contacts:
            dist = math.hypot(c.x - own_x, c.y - own_y)
            if dist > range_:
                continue
            detect_p = max(0.15, 1.0 - dist / range_) * (1.0 - 0.5 * rain)
            if self.rng.random() < detect_p:
                jitter = abs(self.rng.gauss(0.0, 0.3 * (rain + 0.05)))
                bearing = round(math.degrees(
                    math.atan2(c.y - own_y, c.x - own_x)) % 360, 2)
                detections.append({
                    "contact_id": c.contact_id, "kind": c.kind,
                    "range": round(dist, 3), "bearing_deg": bearing,
                    "position_error": round(jitter, 3),
                })
        return detections

    def optical_capture(self, target_id: str, tick: int,
                        cloud_cover: Optional[float] = None) -> Dict[str, Any]:
        cloud = self.env.weather.cloud_cover \
            if cloud_cover is None else cloud_cover
        quality = round(1.0 - 0.8 * cloud, 3)
        return {"target": target_id, "quality": quality,
                "usable": quality >= 0.4}

    def sonar_ping(self, own_x: float, own_y: float,
                   contacts: List[Contact], range_: float = 12.0
                   ) -> List[Dict[str, Any]]:
        return [{"contact_id": c.contact_id, "kind": c.kind,
                 "range": round(math.hypot(c.x - own_x, c.y - own_y), 3)}
                for c in contacts
                if math.hypot(c.x - own_x, c.y - own_y) <= range_]