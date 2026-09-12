# Copyright (c) Ultrone Contributors. All rights reserved.
"""Warehouse-arm operator: joint positioning and gripper handling."""

from __future__ import annotations

from typing import Any, Dict

from agents.civilian.base import CivilianMachineAgent


class WarehouseArmAgent(CivilianMachineAgent):
    """Drives a sandbox RoboticArm for pick/place style missions."""

    MACHINE_KIND = "warehouse_arm"
    TICK_LIMIT = 120

    def execute_mission(self, mission: Dict[str, Any]) -> Dict[str, Any]:
        if self.machine is None or self.interlock.e_stopped:
            result = {"success": False, "reason": "no machine or e-stop"}
            self._log_mission(mission.get("type", "?"), result)
            return result

        joints: Dict[str, float] = {
            j: float(v) for j, v in mission.get("joints", {}).items()
        }
        if not self.machine.command_move(joints, tick=1):
            result = {"success": False,
                      "reason": "interlock refused joint targets"}
            self._log_mission(mission.get("type", "position"), result)
            return result

        settled = False
        for t in range(1, self.TICK_LIMIT + 1):
            self.controller.step_all(t)
            if all(abs(self.machine.joints[j] - v) <= 0.05
                   for j, v in joints.items()):
                settled = True
                break
        gripper_ok = True
        if "gripper" in mission:
            gripper_ok = self.machine.command_gripper(
                str(mission["gripper"]), tick=self.TICK_LIMIT + 1)

        result = {
            "success": settled and gripper_ok,
            "settled": settled,
            "joints_final": {j: round(v, 3)
                             for j, v in self.machine.joints.items()},
            "gripper": self.machine.gripper,
        }
        self._log_mission(mission.get("type", "position"), result)
        return result
