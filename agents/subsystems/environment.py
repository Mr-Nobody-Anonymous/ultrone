# Copyright (c) Ultrone Contributors. All rights reserved.
"""Environment subsystem: cabin pressure and atmosphere quality state."""

from __future__ import annotations

from typing import Any, Dict

from agents.subsystems.base import Subsystem, command


class EnvironmentSubsystem(Subsystem):
    """Cabin/environmental life-support: pressure and oxygen quality."""

    name = "environment"

    def __init__(self, pressure_kpa: float = 101.3,
                 o2_pct: float = 20.9) -> None:
        super().__init__()
        self.pressure_kpa = pressure_kpa
        self.o2_pct = o2_pct
        self.scrubber_on = True

    @command("set_scrubber")
    def set_scrubber(self, on: bool = True) -> bool:
        self.scrubber_on = bool(on)
        return True

    @command("repressurize")
    def repressurize(self, target: float = 101.3) -> float:
        self.pressure_kpa = float(target)
        return self.pressure_kpa

    def tick(self, tick: int) -> None:
        if self.scrubber_on:
            self.o2_pct = min(21.5, self.o2_pct + 0.1)
        else:
            self.o2_pct = max(12.0, self.o2_pct - 0.15)

    def is_safe(self) -> bool:
        return self.pressure_kpa >= 60.0 and self.o2_pct >= 17.0

    def status(self) -> Dict[str, Any]:
        return {**super().status(),
                "pressure_kpa": round(self.pressure_kpa, 3),
                "o2_pct": round(self.o2_pct, 3),
                "safe": self.is_safe()}
