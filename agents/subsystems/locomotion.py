# Copyright (c) Ultrone Contributors. All rights reserved.
"""Locomotion subsystem: ground mobility modes, speed, odometry."""

from __future__ import annotations

from typing import Any, Dict

from agents.subsystems.base import Subsystem, command


class MobilitySubsystem(Subsystem):
    """Locomotion for wheeled / tracked / legged ground platforms."""

    name = "mobility"
    MODES = ("stationary", "wheels", "tracks", "legs")

    def __init__(self, max_speed: float = 2.0,
                 terrain_factor: float = 1.0) -> None:
        super().__init__()
        self.max_speed = float(max_speed)
        self.terrain_factor = max(0.0, float(terrain_factor))
        self.mode = "stationary"
        self.speed = 0.0
        self.odometry = 0.0

    @command("set_mode")
    def set_mode(self, mode: str = "stationary") -> str:
        if mode not in self.MODES:
            raise RuntimeError(f"unknown locomotion mode '{mode}'")
        self.mode = mode
        if mode == "stationary":
            self.speed = 0.0
        return self.mode

    @command("drive")
    def drive(self, speed: float = 0.0) -> float:
        if self.mode == "stationary":
            raise RuntimeError("cannot drive while stationary -- set_mode first")
        limit = self.max_speed * self.terrain_factor
        self.speed = min(limit, max(0.0, float(speed)))
        return round(self.speed, 3)

    @command("stop")
    def stop(self) -> float:
        self.speed = 0.0
        return 0.0

    def tick(self, tick: int) -> None:
        self.odometry += self.speed

    def status(self) -> Dict[str, Any]:
        return {**super().status(), "mode": self.mode,
                "speed": round(self.speed, 3),
                "odometry": round(self.odometry, 3),
                "speed_limit": round(self.max_speed * self.terrain_factor, 3)}
