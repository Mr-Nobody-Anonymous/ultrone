# Copyright (c) Ultrone Contributors. All rights reserved.
"""Transit network node: scheduled route service along waypoints."""

from __future__ import annotations

from typing import Any, Dict

from agents.commands import Command
from agents.infrastructure.base import InfrastructureNodeAgent


class TransitNetworkAgent(InfrastructureNodeAgent):
    """Simulated transit segment serving ordered stops along a route."""

    MACHINE_KIND = "transit_network"
    SERVICE_SPEED = 1.0

    def _build_subsystems(self) -> list:
        from agents.subsystems.computing import (ConfigurationSubsystem,
                                                 MonitoringSubsystem)
        from agents.subsystems.mobility import MobilitySubsystem
        from agents.subsystems.platform_subsystems import (
            AutonomySubsystem, CommunicationSubsystem, HealthSubsystem,
            NavigationSubsystem)

        return [
            NavigationSubsystem(),
            MobilitySubsystem(max_speed=1.5),
            MonitoringSubsystem(),
            ConfigurationSubsystem(allowed_keys=("headway_s",
                                                 "service_mode")),
            CommunicationSubsystem(),
            HealthSubsystem(wear_rate=0.004),
            AutonomySubsystem(),
        ]

    def execute_mission(self, mission: Dict[str, Any]) -> Dict[str, Any]:
        route = [(float(x), float(y))
                 for x, y in mission.get("route", [])]
        if not route:
            return {"success": False, "reason": "no route"}
        self.execute(Command("mobility", "set_mode", {"mode": "wheels"}))
        self.execute(Command("mobility", "drive",
                             {"speed": self.SERVICE_SPEED}))
        nav = self.get_subsystem("navigation")
        served = 0
        for sx, sy in route:
            arrived = False
            for tick in range(1, 300):
                dx, dy = sx - nav.x, sy - nav.y
                if (dx * dx + dy * dy) ** 0.5 <= 0.5:
                    arrived = True
                    break
                import math

                bearing = math.atan2(sy - nav.y, sx - nav.x)
                self.execute(Command("navigation", "set_heading",
                                     {"deg": math.degrees(bearing)}))
                rad = math.radians(nav.heading_deg)
                speed = min(self.SERVICE_SPEED,
                            max(0.4, (dx * dx + dy * dy) ** 0.5 * 0.3))
                nav.x += math.cos(rad) * speed
                nav.y += math.sin(rad) * speed
                self.tick_platform(tick)
            if not arrived:
                break
            served += 1
        self.execute(Command("mobility", "stop"))
        return {
            "success": served == len(route),
            "stops_total": len(route),
            "stops_served": served,
        }
