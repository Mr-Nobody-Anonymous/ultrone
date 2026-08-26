# Copyright (c) Ultrone Contributors. All rights reserved.
"""Orbital-navigation subsystem: altitude/inclination state and delta-v burns.

Deliberately simplified two-body-style bookkeeping -- enough structure for
research scenarios, far from real astrodynamics. Simulation-only.
"""

from __future__ import annotations

from typing import Any, Dict

from agents.subsystems.base import Subsystem, command


class OrbitalNavigationSubsystem(Subsystem):
    """Orbit altitude/inclination with a finite delta-v budget."""

    name = "orbital_navigation"

    MIN_ALTITUDE_KM = 150.0
    KM_PER_DELTA_V = 0.5         # simplified raising efficiency

    def __init__(self, altitude_km: float = 500.0,
                 inclination_deg: float = 0.0,
                 delta_v_capacity: float = 100.0) -> None:
        super().__init__()
        self.altitude_km = float(altitude_km)
        self.inclination_deg = float(inclination_deg)
        self.delta_v_capacity = float(delta_v_capacity)
        self.delta_v_remaining = float(delta_v_capacity)
        self.burn_count = 0

    @command("set_inclination")
    def set_inclination(self, deg: float = 0.0) -> float:
        self.inclination_deg = min(180.0, max(-180.0, float(deg)))
        return round(self.inclination_deg, 3)

    @command("execute_burn")
    def execute_burn(self, delta_v: float = 0.0,
                     direction: str = "prograde") -> Dict[str, float]:
        delta_v = float(delta_v)
        if direction not in ("prograde", "retrograde"):
            raise RuntimeError(f"unknown burn direction '{direction}'")
        if delta_v <= 0:
            raise RuntimeError("delta_v must be positive")
        if delta_v > self.delta_v_remaining + 1e-9:
            raise RuntimeError(
                f"insufficient delta-v ({round(self.delta_v_remaining, 3)} "
                f"remaining)")
        self.delta_v_remaining -= delta_v
        if direction == "prograde":
            self.altitude_km += delta_v * self.KM_PER_DELTA_V
        else:
            self.altitude_km = max(self.MIN_ALTITUDE_KM,
                                   self.altitude_km
                                   - delta_v * self.KM_PER_DELTA_V)
        self.burn_count += 1
        return {"altitude_km": round(self.altitude_km, 3),
                "delta_v_remaining": round(self.delta_v_remaining, 3)}

    def orbital_period_minutes(self) -> float:
        """Deterministic simplified period model (documented approximation)."""
        return round(max(80.0, 90.0 + (self.altitude_km - 500.0) / 50.0), 3)

    def status(self) -> Dict[str, Any]:
        return {**super().status(),
                "altitude_km": round(self.altitude_km, 3),
                "inclination_deg": round(self.inclination_deg, 3),
                "delta_v_remaining": round(self.delta_v_remaining, 3),
                "delta_v_capacity": round(self.delta_v_capacity, 3),
                "burn_count": self.burn_count,
                "period_minutes": self.orbital_period_minutes()}
