# Copyright (c) Ultrone Contributors. All rights reserved.
"""Telemetry, kinematics, and vehicle state schemas."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class KinematicTelemetry:
    heading_deg: float = 0.0
    ground_speed_knots: float = 0.0
    vertical_speed_fpm: float = 0.0
    roll_deg: float = 0.0
    pitch_deg: float = 0.0
    yaw_rate_dps: float = 0.0
    timestamp: float = field(default_factory=time.time)
