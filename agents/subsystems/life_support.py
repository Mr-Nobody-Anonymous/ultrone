# Copyright (c) Ultrone Contributors. All rights reserved.
"""Life-support subsystem: consumable-driven crew sustainment machinery.

Distinct from :class:`~agents.subsystems.environment.EnvironmentSubsystem`
(which models the cabin atmosphere STATE): this is the machinery that
consumes reserves to sustain it -- O2 generation, water reclamation,
rationing. Composition determines presence: crewed platforms only.
"""

from __future__ import annotations

from typing import Any, Dict

from agents.subsystems.base import Subsystem, command


class LifeSupportSubsystem(Subsystem):
    """Consumable reserves drawn down by life-support generation."""

    name = "life_support"

    DRAW_PER_UNIT = 0.05          # reserve pct per tick at full generation

    def __init__(self, o2_reserve_pct: float = 100.0,
                 water_reserve_pct: float = 100.0) -> None:
        super().__init__()
        self.o2_reserve_pct = float(o2_reserve_pct)
        self.water_reserve_pct = float(water_reserve_pct)
        self.generation = 0.6         # 0..1 setpoint
        self.rationing = False

    @command("set_generation")
    def set_generation(self, rate: float = 0.6) -> float:
        rate = min(1.0, max(0.0, float(rate)))
        self.generation = rate
        if rate > 0.8 and self.rationing:
            raise RuntimeError("cannot exceed 0.8 generation while rationing")
        return round(self.generation, 3)

    @command("set_rationing")
    def set_rationing(self, on: bool = False) -> bool:
        self.rationing = bool(on)
        if on and self.generation > 0.8:
            self.generation = 0.8
        return self.rationing

    @command("resupply")
    def resupply(self, o2_pct: float = 100.0,
                 water_pct: float = 100.0) -> Dict[str, float]:
        self.o2_reserve_pct = min(100.0, self.o2_reserve_pct + float(o2_pct))
        self.water_reserve_pct = min(100.0,
                                     self.water_reserve_pct + float(water_pct))
        return {"o2_reserve_pct": round(self.o2_reserve_pct, 3),
                "water_reserve_pct": round(self.water_reserve_pct, 3)}

    @property
    def sustainable_ticks(self) -> int:
        draw = max(1e-9, self.generation * self.DRAW_PER_UNIT)
        if not self.rationing:
            return int(min(self.o2_reserve_pct,
                           self.water_reserve_pct) / draw)
        # Rationing halves effective consumption.
        return int(min(self.o2_reserve_pct,
                       self.water_reserve_pct) / (draw / 2.0))

    def tick(self, tick: int) -> None:
        factor = 0.5 if self.rationing else 1.0
        draw = self.generation * self.DRAW_PER_UNIT * factor
        self.o2_reserve_pct = max(0.0, self.o2_reserve_pct - draw)
        self.water_reserve_pct = max(0.0, self.water_reserve_pct - draw)

    def status(self) -> Dict[str, Any]:
        return {**super().status(),
                "generation": round(self.generation, 3),
                "rationing": self.rationing,
                "o2_reserve_pct": round(self.o2_reserve_pct, 3),
                "water_reserve_pct": round(self.water_reserve_pct, 3),
                "sustainable_ticks": self.sustainable_ticks}
