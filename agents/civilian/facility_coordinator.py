# Copyright (c) Ultrone Contributors. All rights reserved.
"""Facility coordinator: one agent, many heterogeneous machines at once.

Where the other operators each master ONE machine, the coordinator
orchestrates several concurrently -- production (CNC), material flow
(conveyor), and facility climate (HVAC) advance together on a shared
clock. This is the multi-machine control capability: keeping every
machine inside its envelope *simultaneously*.
"""

from __future__ import annotations

from typing import Any, Dict

from agents.civilian.base import CivilianMachineAgent
from sandbox.machines import CNCMachine, ClimateUnit, ConveyorLine


class FacilityCoordinatorAgent(CivilianMachineAgent):
    MACHINE_KIND = "facility_coordinator"
    TICK_LIMIT = 800

    def attach_cnc(self, machine: CNCMachine) -> None:
        self.controller.register(machine)
        self.cnc = machine

    def attach_conveyor(self, machine: ConveyorLine) -> None:
        self.controller.register(machine)
        self.conveyor = machine

    def attach_climate(self, machine: ClimateUnit) -> None:
        self.controller.register(machine)
        self.hvac = machine

    def execute_mission(self, mission: Dict[str, Any]) -> Dict[str, Any]:
        cnc = getattr(self, "cnc", None)
        conveyor = getattr(self, "conveyor", None)
        hvac = getattr(self, "hvac", None)
        if not all((cnc, conveyor, hvac)) or self.interlock.e_stopped:
            result = {"success": False,
                      "reason": "missing machines or e-stop"}
            self._log_mission(mission.get("type", "?"), result)
            return result

        parts_needed = int(mission.get("parts", 20))
        climate_target = float(mission.get("climate_target", 21.0))
        violations_before = self.controller.hard_violations
        start_parts = cnc.parts_completed

        # Start production safely.
        cnc.command_door(open_=False, tick=1)
        spindle_ok = cnc.command_spindle(True, 9000, tick=2, feed_rate=1.5)
        conveyor.command_speed(1.2, tick=2)

        produced_ok = False
        climate_held = 0
        for t in range(1, self.TICK_LIMIT + 1):
            self.controller.step_all(t)

            if not produced_ok and cnc.parts_completed - start_parts \
                    >= parts_needed:
                cnc.command_spindle(False, 0, tick=t)
                produced_ok = True
            elif not produced_ok and cnc.needs_tool_service:
                cnc.command_spindle(False, 0, tick=t)
                cnc.command_tool_change(tick=t)
                cnc.command_spindle(True, 9000, tick=t, feed_rate=1.5)

            # Climate runs CONCURRENTLY with production.
            err = climate_target - hvac.temperature
            hvac.command_mode(
                "heat" if err > 0.05 else "cool" if err < -0.05 else "off",
                tick=t)
            if abs(hvac.temperature - climate_target) <= 0.75:
                climate_held += 1

            if produced_ok and climate_held >= 10:
                break

        clean = self.controller.hard_violations == violations_before
        produced = round(cnc.parts_completed - start_parts, 2)
        result = {
            "success": bool(produced >= parts_needed and clean),
            "parts_produced": produced,
            "climate_ticks_in_band": climate_held,
            "clean": clean,
        }
        self._log_mission(mission.get("type", "fulfill_order"), result)
        return result
