# Copyright (c) Ultrone Contributors. All rights reserved.
"""Naval subsystems: ballast/depth control and sonar (simulation-only).

- :class:`BallastSubsystem` -- ballast tank fill/blow driving a bounded
  depth state toward a target depth (surface/dive/hold).
- :class:`SonarSubsystem` -- passive listening and active pinging with
  deterministic readings; active pings temporarily reveal own position.
"""

from __future__ import annotations

import random
from typing import Any, Dict

from agents.subsystems.base import Subsystem, command


class BallastSubsystem(Subsystem):
    """Ballast tanks + depth control for submerged operation."""

    name = "ballast"

    FILL_NEEDED_TO_DIVE = 0.30   # minimum tank fill to descend
    RATE_M_PER_TICK = 4.0

    def __init__(self, max_depth_m: float = 300.0,
                 initial_depth_m: float = 0.0) -> None:
        super().__init__()
        self.max_depth_m = float(max_depth_m)
        self.depth_m = max(0.0, float(initial_depth_m))
        self.target_depth_m = self.depth_m
        self.fill = 0.0             # 0..1 ballast water fraction

    @command("fill_ballast")
    def fill_ballast(self, amount: float = 0.25) -> float:
        self.fill = min(1.0, max(0.0, self.fill + float(amount)))
        return round(self.fill, 3)

    @command("blow_ballast")
    def blow_ballast(self, amount: float = 0.25) -> float:
        self.fill = min(1.0, max(0.0, self.fill - float(amount)))
        return round(self.fill, 3)

    @command("dive")
    def dive(self, depth_m: float = 50.0) -> float:
        depth = min(self.max_depth_m, max(0.0, float(depth_m)))
        if depth > self.depth_m and self.fill < self.FILL_NEEDED_TO_DIVE:
            raise RuntimeError(
                "insufficient ballast to dive -- fill_ballast first")
        self.target_depth_m = depth
        return round(self.target_depth_m, 3)

    @command("hold_depth")
    def hold_depth(self) -> float:
        self.target_depth_m = self.depth_m
        return round(self.target_depth_m, 3)

    @command("surface")
    def surface(self) -> float:
        self.target_depth_m = 0.0
        return round(self.target_depth_m, 3)

    @property
    def surfaced(self) -> bool:
        return self.depth_m <= 0.01

    def tick(self, tick: int) -> None:
        descending = self.target_depth_m > self.depth_m
        if descending and self.fill < self.FILL_NEEDED_TO_DIVE:
            return                    # cannot descend without ballast
        error = self.target_depth_m - self.depth_m
        step = max(-self.RATE_M_PER_TICK, min(self.RATE_M_PER_TICK, error))
        self.depth_m = max(0.0, self.depth_m + step)

    def status(self) -> Dict[str, Any]:
        return {**super().status(),
                "depth_m": round(self.depth_m, 3),
                "target_depth_m": round(self.target_depth_m, 3),
                "ballast_fill": round(self.fill, 3),
                "surfaced": self.surfaced}


class SonarSubsystem(Subsystem):
    """Passive listen / active ping with deterministic contact readings."""

    name = "sonar"
    MODES = ("passive", "active")
    REVEAL_TICKS = 5             # active ping reveals own position for N ticks

    def __init__(self, seed: int = 0, range_units: float = 50.0) -> None:
        super().__init__()
        self.mode = "passive"
        self.range_units = float(range_units)
        self.rng = random.Random(seed)
        self._last_active_tick = -10_000

    @command("set_mode")
    def set_mode(self, mode: str = "passive") -> str:
        if mode not in self.MODES:
            raise RuntimeError(f"unknown sonar mode '{mode}'")
        self.mode = mode
        return self.mode

    @command("passive_listen")
    def passive_listen(self, contacts: int = 3) -> Dict[str, Any]:
        self.mode = "passive"
        return {"mode": "passive",
                "bearings": {f"contact_{i}":
                             round(self.rng.random() * 360.0, 1)
                             for i in range(max(1, contacts))}}

    @command("active_ping")
    def active_ping(self, contacts: int = 2) -> Dict[str, Any]:
        self.mode = "active"
        # Stamp with the most recent observed tick; tick() keeps it fresh.
        self._last_active_tick = getattr(self, "_tick_now", -1)
        return {"mode": "active",
                "ranges": {f"contact_{i}":
                           round(self.rng.random() * self.range_units, 2)
                           for i in range(max(1, contacts))}}

    @property
    def position_revealed(self) -> bool:
        return (getattr(self, "_tick_now", -1)
                - self._last_active_tick) < self.REVEAL_TICKS

    def tick(self, tick: int) -> None:
        self._tick_now = tick

    def status(self) -> Dict[str, Any]:
        return {**super().status(), "mode": self.mode,
                "range_units": round(self.range_units, 3),
                "position_revealed": self.position_revealed}
