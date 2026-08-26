# Copyright (c) Ultrone Contributors. All rights reserved.
"""Water-systems operator: transfer quotas under concurrent-pump limits."""

from __future__ import annotations

from typing import Any, Dict

from agents.civilian.base import CivilianMachineAgent


class WaterOperatorAgent(CivilianMachineAgent):
    """Runs a sandbox PumpStation to meet a transfer quota safely."""

    MACHINE_KIND = "water_operator"
    TICK_LIMIT = 200

    def attach_station(self, machine) -> None:
        self.attach_machine(machine)

    def execute_mission(self, mission: Dict[str, Any]) -> Dict[str, Any]:
        station = getattr(self, "machine", None)
        if station is None or self.interlock.e_stopped:
            result = {"success": False, "reason": "no station or e-stop"}
            self._log_mission(mission.get("type", "?"), result)
            return result

        quota = float(mission.get("quantity", 30.0))
        start_level = station.clearwell_level
        target = min(start_level + quota,
                     station.CLEARWELL_CAPACITY - 1.0)   # headroom margin
        violations_before = self.controller.hard_violations

        pumps = sorted(station.pump_states)
        for t in range(1, self.TICK_LIMIT + 1):
            running = [p for p in pumps if station.pump_states[p]]
            need = target - station.clearwell_level
            desired = station.MAX_CONCURRENT if need > station.PUMP_RATE * len(pumps) * 0.5 \
                else min(len(pumps), max(1, int(need / station.PUMP_RATE)))
            for idx, pid in enumerate(pumps):
                should_run = idx < desired and need > 0
                if station.pump_states[pid] != should_run:
                    station.command_pump(pid, should_run, tick=t)
            self.controller.step_all(t)
            need = target - station.clearwell_level
            if need <= 0:
                for pid in pumps:
                    if station.pump_states[pid]:
                        station.command_pump(pid, False, tick=t)
                break

        transferred = round(station.clearwell_level - start_level, 3)
        clean = self.controller.hard_violations == violations_before
        result = {
            "success": bool(transferred >= quota * 0.95 and clean),
            "transferred": transferred,
            "quota": quota,
            "clean": clean,
        }
        self._log_mission(mission.get("type", "transfer"), result)
        return result
