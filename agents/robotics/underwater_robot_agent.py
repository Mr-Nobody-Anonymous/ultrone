# Copyright (c) Ultrone Contributors. All rights reserved.
"""Underwater robot: ballast depth control + sonar survey missions."""

from __future__ import annotations

from typing import Any, Dict

from agents.commands import Command
from agents.robotics.base import RoboticPlatformAgent


class UnderwaterRobotAgent(RoboticPlatformAgent):
    """AUV-style platform: dives via ballast, surveys via passive sonar."""

    MACHINE_KIND = "underwater_robot"

    def _build_subsystems(self) -> list:
        from agents.subsystems.attitude import AttitudeSubsystem
        from agents.subsystems.naval import BallastSubsystem, SonarSubsystem
        from agents.subsystems.platform_subsystems import (
            AutonomySubsystem, CommunicationSubsystem, NavigationSubsystem,
            PowerSubsystem, PropulsionSubsystem)

        return [
            BallastSubsystem(max_depth_m=100.0),
            SonarSubsystem(),
            AttitudeSubsystem(),
            PropulsionSubsystem(fuel_capacity=50.0, max_speed=1.5),
            NavigationSubsystem(),
            CommunicationSubsystem(),
            PowerSubsystem(battery_pct=90.0, generation_kw=1.0),
            AutonomySubsystem(),
        ]

    def execute_mission(self, mission: Dict[str, Any]) -> Dict[str, Any]:
        points = self._waypoints(mission)
        depth = float(mission.get("depth_m", 20.0))
        if not points:
            return {"success": False, "reason": "no survey points"}

        # Dive first -- ballast fill gates descending.
        self.execute(Command("ballast", "fill_ballast", {"amount": 0.6}))
        dived = self.execute(Command("ballast", "dive",
                                     {"depth_m": depth}))
        prop = self.get_subsystem("propulsion")
        self.execute(Command("propulsion", "start_engine"))
        self.execute(Command("propulsion", "set_throttle", {"value": 0.8}))
        surveyed = 0
        for px, py in points:
            arrived, _ = self._transit(px, py,
                                       lambda: prop.speed_available)
            if not arrived:
                break
            listening = self.execute(Command("sonar", "passive_listen",
                                             {"contacts": 2}))
            if listening.success:
                surveyed += 1
        # Surface and secure at end of survey.
        self.execute(Command("ballast", "blow_ballast", {"amount": 1.0}))
        self.execute(Command("ballast", "surface"))
        self.execute(Command("propulsion", "stop_engine"))
        for _ in range(50):
            self.tick_platform(0)
            if self.ballast.surfaced:
                break
        return {
            "success": surveyed == len(points) and self.ballast.surfaced,
            "points_surveyed": surveyed,
            "points_total": len(points),
            "dive_accepted": bool(dived.success),
            "final_depth_m": round(self.ballast.depth_m, 3),
        }
