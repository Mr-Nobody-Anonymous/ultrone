# Copyright (c) Ultrone Contributors. All rights reserved.
"""Attitude subsystem: pitch/roll/yaw with rate limits and hard clamps."""

from __future__ import annotations

from typing import Any, Dict

from agents.subsystems.base import Subsystem, command


class AttitudeSubsystem(Subsystem):
    """Pitch / roll / yaw with rate limits and hard clamps."""

    name = "attitude"

    LIMITS = {"pitch": (-30.0, 30.0), "roll": (-45.0, 45.0),
              "yaw": (-180.0, 180.0)}
    MAX_RATE = 10.0

    def __init__(self) -> None:
        super().__init__()
        self.pitch = 0.0
        self.roll = 0.0
        self.yaw = 0.0

    @command("apply_rates")
    def apply_rates(self, pitch_rate: float = 0.0,
                    roll_rate: float = 0.0,
                    yaw_rate: float = 0.0) -> Dict[str, float]:
        pr = max(-self.MAX_RATE, min(self.MAX_RATE, pitch_rate))
        rr = max(-self.MAX_RATE, min(self.MAX_RATE, roll_rate))
        yr = max(-self.MAX_RATE, min(self.MAX_RATE, yaw_rate))
        self.pitch = min(30.0, max(-30.0, self.pitch + pr))
        self.roll = min(45.0, max(-45.0, self.roll + rr))
        self.yaw = (self.yaw + yr) % 360.0
        return {"pitch": round(self.pitch, 3), "roll": round(self.roll, 3),
                "yaw": round(self.yaw, 3)}

    @command("level")
    def level(self) -> Dict[str, float]:
        self.pitch = self.roll = 0.0
        return {"pitch": 0.0, "roll": 0.0}

    def status(self) -> Dict[str, Any]:
        return {**super().status(), "pitch": round(self.pitch, 3),
                "roll": round(self.roll, 3), "yaw": round(self.yaw, 3)}
