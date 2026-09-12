# Copyright (c) Ultrone Contributors. All rights reserved.
"""Sensor payload, radar modes, and detection coverage schemas."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class SensorModality(str, Enum):
    RADAR_AESA = "radar_aesa"
    RADAR_PULSE = "radar_pulse"
    EO_IR = "eo_ir"
    SIGINT = "sigint"
    ELINT = "elint"
    ACOUSTIC = "acoustic"
    LIDAR = "lidar"


@dataclass
class SensorCoverageCone:
    azimuth_center_deg: float = 0.0
    azimuth_width_deg: float = 120.0
    elevation_min_deg: float = -10.0
    elevation_max_deg: float = 60.0
    max_range_km: float = 200.0


@dataclass
class SensorSpec:
    sensor_id: str
    modality: SensorModality
    coverage: SensorCoverageCone = field(default_factory=SensorCoverageCone)
    refresh_rate_hz: float = 1.0
    is_active: bool = True
