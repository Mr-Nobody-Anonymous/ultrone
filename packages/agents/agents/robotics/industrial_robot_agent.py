# Copyright (c) Ultrone Contributors. All rights reserved.
"""Industrial robot arm: payload cycling under compute supervision."""

from __future__ import annotations

from typing import Any, Dict

from agents.commands import Command
from agents.robotics.base import RoboticPlatformAgent


class IndustrialRobotAgent(RoboticPlatformAgent):
    """Fixed-base manipulator: load/unload production cycles."""

    MACHINE_KIND = "industrial_robot"

    def _build_subsystems(self) -> list:
        from agents.subsystems.computing import ComputeSubsystem
        from agents.subsystems.mobility import MobilitySubsystem
        from agents.subsystems.platform_subsystems import (
            AutonomySubsystem, CommunicationSubsystem, HealthSubsystem,
            PayloadSubsystem, PowerSubsystem, SensorSubsystem)

        return [
            ComputeSubsystem(cores=2),
            MobilitySubsystem(max_speed=1.0, terrain_factor=1.0),
            PayloadSubsystem(capacity_kg=12.0),
            SensorSubsystem(seed=0),
            CommunicationSubsystem(),
            PowerSubsystem(battery_pct=100.0, generation_kw=4.0),
            HealthSubsystem(wear_rate=0.05),
            AutonomySubsystem(),
        ]

    def execute_mission(self, mission: Dict[str, Any]) -> Dict[str, Any]:
        cycles = max(0, int(mission.get("cycles", 3)))
        part_kg = min(float(mission.get("part_kg", 2.0)),
                      self.get_subsystem("payload").capacity_kg)
        completed = 0
        self.execute(Command("autonomy", "set_mode", {"mode": "auto"}))
        for _ in range(cycles):
            self.execute(Command("compute", "allocate", {"pct": 25.0}))
            picked = self.execute(Command("payload", "load",
                                          {"kg": part_kg}))
            placed = self.execute(Command("payload", "unload"))
            self.execute(Command("compute", "release", {"pct": 25.0}))
            if picked.success and (placed.value or 0.0) > 0:
                completed += 1
        diag = self.execute(Command("health", "run_diagnostics"))
        return {
            "success": completed == cycles,
            "cycles_completed": completed,
            "cycles_requested": cycles,
            "wear": round((diag.value or {}).get("wear", 0.0), 3),
        }
