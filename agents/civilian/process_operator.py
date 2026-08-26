# Copyright (c) Ultrone Contributors. All rights reserved.
"""Facility process operator: tank levels, conveyor throughput, climate."""

from __future__ import annotations

from typing import Any, Dict

from agents.civilian.base import CivilianMachineAgent


class ProcessOperatorAgent(CivilianMachineAgent):
    """Operates attached process machines via interlocked commands."""

    MACHINE_KIND = "process_operator"
    TICK_LIMIT = 150

    def attach_tank(self, machine) -> None:
        self.attach_machine(machine)
        self.tank = machine

    def attach_conveyor(self, machine) -> None:
        self.controller.register(machine)
        self.conveyor = machine

    def attach_climate(self, machine) -> None:
        self.controller.register(machine)
        self.hvac = machine

    # ------------------------------------------------------------------ #
    def execute_mission(self, mission: Dict[str, Any]) -> Dict[str, Any]:
        if self.interlock.e_stopped:
            result = {"success": False, "reason": "e-stop latched"}
            self._log_mission(mission.get("type", "?"), result)
            return result
        kind = mission.get("type")
        if kind == "hold_level":
            result = self._hold_level(float(mission["target"]))
        elif kind == "produce":
            result = self._produce(int(mission["quantity"]))
        elif kind == "set_climate":
            result = self._set_climate(float(mission["target"]))
        else:
            result = {"success": False,
                      "reason": f"unknown mission type {kind}"}
        self._log_mission(kind or "?", result)
        return result

    def _hold_level(self, target: float) -> Dict[str, Any]:
        tank = getattr(self, "tank", None)
        if tank is None:
            return {"success": False, "reason": "no tank attached"}
        held = 0
        settle = None
        for t in range(1, self.TICK_LIMIT + 1):
            valve = max(0.0, min(100.0,
                                 40.0 + (target - tank.level) * 4.0))
            tank.command_valve(valve, t)
            self.controller.step_all(t)
            if abs(tank.level - target) <= 2.0:
                held += 1
                if settle is None:
                    settle = t
            else:
                held = 0
            if held >= 10:
                break
        clean = self.controller.hard_violations == 0
        return {"success": held >= 10 and clean, "settled_tick": settle,
                "held_ticks": held, "clean": clean}

    def _produce(self, quantity: int) -> Dict[str, Any]:
        conveyor = getattr(self, "conveyor", None)
        if conveyor is None:
            return {"success": False, "reason": "no conveyor attached"}
        conveyor.command_speed(conveyor.MAX_SPEED, tick=1)
        recoveries = 0
        for t in range(1, self.TICK_LIMIT + 1):
            self.controller.step_all(t)
            if conveyor.jammed:
                conveyor.command_clear_jam(t)
                recoveries += 1
            if conveyor.items_produced >= quantity:
                break
        return {
            "success": conveyor.items_produced >= quantity,
            "items": round(conveyor.items_produced, 2),
            "jam_recoveries": recoveries,
        }

    def _set_climate(self, target: float) -> Dict[str, Any]:
        hvac = getattr(self, "hvac", None)
        if hvac is None:
            return {"success": False, "reason": "no climate unit attached"}
        for t in range(1, self.TICK_LIMIT + 1):
            err = target - hvac.temperature
            mode = "heat" if err > 0.05 else "cool" if err < -0.05 else "off"
            hvac.command_mode(mode, t)
            self.controller.step_all(t)
            if abs(hvac.temperature - target) <= 0.75:
                hvac.command_mode("off", t)
                return {"success": True,
                        "final_temperature": round(hvac.temperature, 3),
                        "ticks": t}
        return {"success": False,
                "final_temperature": round(hvac.temperature, 3)}
