# Copyright (c) Ultrone Contributors. All rights reserved.
"""Flight-control subsystem: heading / altitude / speed targets + autopilot.

Self-contained kinematics (no dependency on other subsystems): commanded
targets are approached at fixed deterministic rates while the autopilot is
engaged. Simulation-only.
"""

from __future__ import annotations

from typing import Any, Dict

from agents.subsystems.base import Subsystem, command


class FlightControlSubsystem(Subsystem):
    """Heading, altitude, and speed command layer with autopilot hold."""

    name = "flight_control"

    HEADING_RATE_DEG = 3.0       # degrees per tick
    CLIMB_RATE_M = 2.0           # meters per tick
    ACCEL_UNITS = 0.4            # speed units per tick

    def __init__(self, cruise_altitude: float = 100.0,
                 max_altitude: float = 500.0,
                 max_speed: float = 3.0) -> None:
        super().__init__()
        self.max_altitude = float(max_altitude)
        self.max_speed = float(max_speed)
        self.autopilot = False
        self.heading = 0.0
        self.altitude = float(cruise_altitude)
        self.speed = 0.0
        self.target_heading = 0.0
        self.target_altitude = float(cruise_altitude)
        self.target_speed = 0.0

    @command("set_heading")
    def set_heading(self, deg: float = 0.0) -> float:
        self.target_heading = float(deg) % 360.0
        return round(self.target_heading, 3)

    @command("set_altitude")
    def set_altitude(self, meters: float = 0.0) -> float:
        self.target_altitude = min(self.max_altitude, max(0.0, float(meters)))
        return round(self.target_altitude, 3)

    @command("set_speed")
    def set_speed(self, value: float = 0.0) -> float:
        self.target_speed = min(self.max_speed, max(0.0, float(value)))
        return round(self.target_speed, 3)

    @command("engage_autopilot")
    def engage_autopilot(self) -> bool:
        self.autopilot = True
        return True

    @command("disengage_autopilot")
    def disengage_autopilot(self) -> bool:
        self.autopilot = False
        return True

    @command("level_off")
    def level_off(self) -> float:
        self.target_altitude = self.altitude
        return round(self.target_altitude, 3)

    def tick(self, tick: int) -> None:
        if not self.autopilot:
            return
        # Turn toward target heading along the shortest arc.
        error = (self.target_heading - self.heading + 180.0) % 360.0 - 180.0
        step = max(-self.HEADING_RATE_DEG, min(self.HEADING_RATE_DEG, error))
        self.heading = (self.heading + step) % 360.0
        # Approach altitude and speed targets linearly.
        d_alt = self.target_altitude - self.altitude
        self.altitude += max(-self.CLIMB_RATE_M,
                             min(self.CLIMB_RATE_M, d_alt))
        d_spd = self.target_speed - self.speed
        self.speed += max(-self.ACCEL_UNITS, min(self.ACCEL_UNITS, d_spd))

    def status(self) -> Dict[str, Any]:
        return {**super().status(),
                "autopilot": self.autopilot,
                "heading": round(self.heading, 3),
                "target_heading": round(self.target_heading, 3),
                "altitude": round(self.altitude, 3),
                "target_altitude": round(self.target_altitude, 3),
                "speed": round(self.speed, 3),
                "target_speed": round(self.target_speed, 3)}
