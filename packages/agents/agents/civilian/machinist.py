# Copyright (c) Ultrone Contributors. All rights reserved.
"""CNC machinist agent: safe production runs with tool lifecycle."""

from __future__ import annotations

from typing import Any, Dict

from agents.civilian.base import CivilianMachineAgent


class MachiningAgent(CivilianMachineAgent):
    """Runs a sandbox CNCMachine through production missions."""

    MACHINE_KIND = "cnc_machinist"
    TICK_LIMIT = 600

    def execute_mission(self, mission: Dict[str, Any]) -> Dict[str, Any]:
        if self.machine is None or self.interlock.e_stopped:
            result = {"success": False, "reason": "no machine or e-stop"}
            self._log_mission(mission.get("type", "?"), result)
            return result
        quantity = int(mission.get("quantity", 10))
        rpm = int(mission.get("rpm", 9000))
        feed = float(mission.get("feed_rate", 1.0))
        start_count = self.machine.parts_completed
        target = start_count + quantity

        # Safe startup sequence: door closed -> spindle on.
        self.machine.command_door(open_=False, tick=1)
        if not self.machine.command_spindle(True, rpm, tick=2,
                                            feed_rate=feed):
            self.machine.command_door(open_=True, tick=3)
            result = {"success": False,
                      "reason": "spindle refused (door/tool/rpm)"}
            self._log_mission(mission.get("type", "machine_parts"), result)
            return result

        service_events = 0
        for t in range(1, self.TICK_LIMIT + 1):
            self.controller.step_all(t)
            if self.machine.parts_completed >= target:
                break
            if self.machine.needs_tool_service:
                # Stop spindle, open door, service, resume.
                self.machine.command_spindle(False, 0, tick=t)
                self.machine.command_door(True, tick=t)
                self.machine.command_tool_change(tick=t)
                self.machine.command_door(False, tick=t)
                self.machine.command_spindle(True, rpm, tick=t, feed_rate=feed)
                service_events += 1
        self.machine.command_spindle(False, 0, tick=self.TICK_LIMIT + 1)
        self.machine.command_door(True, tick=self.TICK_LIMIT + 2)

        produced = self.machine.parts_completed - start_count
        result = {
            "success": produced >= quantity,
            "parts_produced": round(produced, 2),
            "tool_service_events": service_events,
        }
        self._log_mission(mission.get("type", "machine_parts"), result)
        return result
