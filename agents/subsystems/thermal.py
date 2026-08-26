# Copyright (c) Ultrone Contributors. All rights reserved.
"""Thermal subsystem: temperature management with overheat protection."""

from __future__ import annotations

from typing import Any, Dict

from agents.subsystems.base import Subsystem, command


class ThermalSubsystem(Subsystem):
    """Temperature management with overheating protection."""

    name = "thermal"

    def __init__(self, ambient: float = 20.0,
                 overheat_limit: float = 85.0) -> None:
        super().__init__()
        self.temperature = ambient
        self.ambient = ambient
        self.cooling = False
        self.overheat_limit = overheat_limit
        self.overheat_events = 0

    @command("set_cooling")
    def set_cooling(self, on: bool = True) -> bool:
        self.cooling = bool(on)
        return True

    def add_heat(self, amount: float) -> None:
        self.temperature += float(amount)
        if self.temperature > self.overheat_limit:
            self.lock_in_overheat()

    def lock_in_overheat(self) -> None:
        if not any(f.get("reason") == "overheat"
                   for f in self.faults[-3:]):
            self.record_fault("overheat")
            self.overheat_events += 1

    def tick(self, tick: int) -> None:
        if self.cooling:
            self.temperature -= 1.5
        drift = (self.ambient - self.temperature) * 0.05
        self.temperature += drift
        if self.temperature > self.overheat_limit:
            self.lock_in_overheat()

    def is_overheating(self) -> bool:
        return self.temperature > self.overheat_limit

    def status(self) -> Dict[str, Any]:
        return {**super().status(),
                "temperature": round(self.temperature, 3),
                "cooling": self.cooling,
                "is_overheating": self.is_overheating(),
                "overheat_events": self.overheat_events}
