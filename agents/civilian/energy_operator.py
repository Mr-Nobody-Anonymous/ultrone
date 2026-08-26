# Copyright (c) Ultrone Contributors. All rights reserved.
"""Energy-grid operator: serve load without brownouts, spend fuel wisely."""

from __future__ import annotations

from typing import Any, Dict

from agents.civilian.base import CivilianMachineAgent


class EnergyOperatorAgent(CivilianMachineAgent):
    """Dispatches a sandbox PowerMicrogrid against a demand profile."""

    MACHINE_KIND = "energy_operator"
    TICK_LIMIT = 300
    GEN_ON_THRESHOLD_PCT = 45.0       # start backup before the floor bites

    def attach_microgrid(self, machine) -> None:
        self.attach_machine(machine)

    def execute_mission(self, mission: Dict[str, Any]) -> Dict[str, Any]:
        grid = getattr(self, "machine", None)
        if grid is None or self.interlock.e_stopped:
            result = {"success": False, "reason": "no microgrid or e-stop"}
            self._log_mission(mission.get("type", "?"), result)
            return result

        duration = int(mission.get("duration", 48))
        profile = mission.get("demand_profile")
        brownout_before = grid.brownouts

        for t in range(1, duration + 1):
            demand = float(profile(t)) if callable(profile) \
                else float(mission.get("demand", grid.demand_kw))
            grid.command_load(demand, tick=t)
            # Start the generator when the battery approaches its floor --
            # dispatch ahead of trouble instead of reacting to it.
            if grid.battery_pct <= self.GEN_ON_THRESHOLD_PCT:
                grid.command_generator(True, tick=t)
            elif grid.battery_pct >= self.GEN_ON_THRESHOLD_PCT + 20.0:
                grid.command_generator(False, tick=t)
            self.controller.step_all(t)

        served_cleanly = grid.brownouts == brownout_before
        result = {
            "success": bool(served_cleanly and grid.fuel_pct >= 0),
            "brownouts": grid.brownouts - brownout_before,
            "final_battery_pct": round(grid.battery_pct, 2),
            "fuel_remaining_pct": round(grid.fuel_pct, 2),
        }
        self._log_mission(mission.get("type", "serve_load"), result)
        return result
