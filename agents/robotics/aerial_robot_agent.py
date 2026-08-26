# Copyright (c) Ultrone Contributors. All rights reserved.
"""Aerial robot: propulsion + flight-control waypoint missions."""

from __future__ import annotations

import math
from typing import Any, Dict

from agents.commands import Command
from agents.robotics.base import RoboticPlatformAgent


class AerialRobotAgent(RoboticPlatformAgent):
    """Small UAV: engine/autopilot discipline with payload delivery legs."""

    MACHINE_KIND = "aerial_robot"

    def _build_subsystems(self) -> list:
        from agents.subsystems.flight import FlightControlSubsystem
        from agents.subsystems.platform_subsystems import (
            AutonomySubsystem, CommunicationSubsystem, NavigationSubsystem,
            PayloadSubsystem, PowerSubsystem, PropulsionSubsystem,
            SensorSubsystem)

        return [
            PropulsionSubsystem(fuel_capacity=40.0, max_speed=3.0),
            FlightControlSubsystem(cruise_altitude=60.0,
                                   max_altitude=120.0),
            NavigationSubsystem(),
            SensorSubsystem(seed=0),
            CommunicationSubsystem(),
            PowerSubsystem(generation_kw=2.0),
            PayloadSubsystem(capacity_kg=5.0),
            AutonomySubsystem(),
        ]

    def execute_mission(self, mission: Dict[str, Any]) -> Dict[str, Any]:
        waypoints = self._waypoints(mission)
        if not waypoints:
            return {"success": False, "reason": "no waypoints"}
        self.execute(Command("propulsion", "start_engine"))
        self.execute(Command("flight_control", "engage_autopilot"))
        self.execute(Command("flight_control", "set_altitude",
                             {"meters": self.flight_control.target_altitude}))
        visited = 0
        nav = self.get_subsystem("navigation")
        for wx, wy in waypoints:
            self.execute(Command("navigation", "set_destination",
                                 {"position": [wx, wy]}))
            arrived = False
            for tick in range(1, 300):
                dist = math.hypot(wx - nav.x, wy - nav.y)
                if dist <= 0.5:
                    arrived = True
                    break
                bearing = math.atan2(wy - nav.y, wx - nav.x)
                self.execute(Command("navigation", "set_heading",
                                     {"deg": math.degrees(bearing)}))
                throttle = min(1.0, max(0.35, dist * 0.25))
                self.execute(Command("propulsion", "set_throttle",
                                     {"value": round(throttle, 3)}))
                rad = math.radians(nav.heading_deg)
                nav.x += math.cos(rad) * self.propulsion.speed_available
                nav.y += math.sin(rad) * self.propulsion.speed_available
                self.tick_platform(tick)
            if not arrived:
                break
            visited += 1
            self.execute(Command("sensors", "scan", {"targets": 1}))
        self.execute(Command("propulsion", "stop_engine"))
        return {
            "success": visited == len(waypoints),
            "waypoints_visited": visited,
            "waypoints_total": len(waypoints),
            "fuel_remaining": round(self.propulsion.fuel, 3),
            "altitude": round(self.flight_control.altitude, 3),
        }
