# Copyright (c) Ultrone Contributors. All rights reserved.
"""Inspection-robot operator: waypoint patrols inside a bounded arena."""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from agents.civilian.base import CivilianMachineAgent


class InspectionRobotAgent(CivilianMachineAgent):
    """Drives a sandbox MobileRobot on waypoint inspection patrols."""

    MACHINE_KIND = "inspection_robot"
    TICK_LIMIT = 400

    def execute_mission(self, mission: Dict[str, Any]) -> Dict[str, Any]:
        if self.machine is None or self.interlock.e_stopped:
            result = {"success": False, "reason": "no machine or e-stop"}
            self._log_mission(mission.get("type", "?"), result)
            return result

        waypoints: List[Optional[tuple]] = [
            (float(x), float(y)) for x, y in mission["waypoints"]
        ]
        tolerance = float(mission.get("tolerance", 0.5))
        reached = 0
        battery_before = self.machine.battery

        for t in range(1, self.TICK_LIMIT + 1):
            target = waypoints[reached] if reached < len(waypoints) else None
            if target is None:
                break
            tx, ty = target
            dist, turn = self._steer_toward(
                self.machine.x, self.machine.y, self.machine.heading, tx, ty)
            linear = min(self.machine.MAX_LINEAR,
                         max(0.2, dist * 0.4)) if dist > tolerance * 0.6 else 0.0
            self.machine.command_velocity(linear, turn, t)
            self.controller.step_all(t)
            if math.hypot(tx - self.machine.x, ty - self.machine.y) <= tolerance:
                self.machine.command_velocity(0.0, 0.0, t)  # never latch speed
                reached += 1

        result = {
            "success": reached == len(waypoints),
            "waypoints_reached": reached,
            "waypoints_total": len(waypoints),
            "battery_used": round(battery_before - self.machine.battery, 4),
            "hard_violations": self.controller.hard_violations,
        }
        self._log_mission(mission.get("type", "patrol"), result)
        return result
