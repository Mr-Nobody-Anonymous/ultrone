# Copyright (c) Ultrone Contributors. All rights reserved.
"""Ground robot: waypoint patrols via the mobility + navigation subsystems."""

from __future__ import annotations

from typing import Any, Dict

from agents.commands import Command
from agents.robotics.base import RoboticPlatformAgent


class GroundRobotAgent(RoboticPlatformAgent):
    """Wheeled/tracked inspection robot driving waypoint patrols."""

    MACHINE_KIND = "ground_robot"
    CRUISE_SPEED = 1.2

    def _build_subsystems(self) -> list:
        from agents.subsystems.locomotion import MobilitySubsystem
        from agents.subsystems.platform_subsystems import (
            AutonomySubsystem, CommunicationSubsystem, HealthSubsystem,
            NavigationSubsystem, PowerSubsystem, SensorSubsystem)

        return [
            MobilitySubsystem(max_speed=2.0),
            NavigationSubsystem(),
            SensorSubsystem(seed=0),
            CommunicationSubsystem(),
            PowerSubsystem(battery_pct=95.0, generation_kw=0.0),
            HealthSubsystem(wear_rate=0.02),
            AutonomySubsystem(),
        ]

    def execute_mission(self, mission: Dict[str, Any]) -> Dict[str, Any]:
        waypoints = self._waypoints(mission)
        if not waypoints:
            return {"success": False, "reason": "no waypoints"}
        self.execute(Command("mobility", "set_mode", {"mode": "wheels"}))
        self.execute(Command("mobility", "drive",
                             {"speed": self.CRUISE_SPEED}))
        served = 0
        for wx, wy in waypoints:
            arrived, _ = self._transit(
                wx, wy, lambda: self.mobility.speed)
            if not arrived:
                break
            served += 1
            self.execute(Command("sensors", "scan", {"targets": 1}))
        self.execute(Command("mobility", "stop"))
        diag = self.execute(Command("health", "run_diagnostics"))
        return {
            "success": served == len(waypoints),
            "waypoints_served": served,
            "waypoints_total": len(waypoints),
            "wear": round((diag.value or {}).get("wear", 0.0), 3),
            "distance_driven": round(self.mobility.odometry, 3),
        }
