# Copyright (c) Ultrone Contributors. All rights reserved.
"""Universal machine operator: control ANY machine with zero per-kind code.

Unlike the sibling operators (which each hard-wire one sandbox machine
class), this agent is **kind-agnostic**. At mission time it:

1. discovers what every attached machine accepts via
   ``MachineController.describe_machines()`` -- capability sheets are
   derived from each machine's ``command_*`` API, including machines
   whose methods were generated at runtime from a declarative spec;
2. plans a sequence of ``{"machine", "action", "params"}`` steps from
   the mission dict;
3. sends them through ``MachineController.dispatch``, so the machine's
   own SafetyInterlock remains the single gatekeeper;
4. optionally waits for a state condition between steps
   (``wait_for``: {"sensor": ..., "op": "ge", "value": ...} evaluated
   against telemetry).

Because nothing about it is machine-specific, it can drive arms,
drones, printers, pumps, batteries -- and any machine type added to
the zoo later -- without modification.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from agents.civilian.base import CivilianMachineAgent


class UniversalOperatorAgent(CivilianMachineAgent):
    """Data-driven operator over the whole heterogeneous machine zoo."""

    MACHINE_KIND = "universal_operator"
    TICK_LIMIT = 600

    # -- capability discovery ------------------------------------------------ #
    def capability_sheet(self) -> Dict[str, Dict[str, object]]:
        return self.controller.describe_machines()

    def can_control(self, machine_id: str, action: str) -> bool:
        sheet = self.capability_sheet().get(machine_id)
        return bool(sheet) and action in sheet["capabilities"]

    # -- condition waiting --------------------------------------------------- #
    def _telemetry_of(self, machine_id: str) -> Dict[str, object]:
        machine = self.controller.machines.get(machine_id)
        return machine.telemetry() if machine is not None else {}

    @staticmethod
    def _condition_met(telemetry: Dict[str, object],
                       cond: Dict[str, Any]) -> bool:
        actual = telemetry.get(cond.get("sensor", ""))
        if actual is None:
            return False
        try:
            value = float(cond.get("value", 0))
            actual = float(actual)
        except (TypeError, ValueError):
            return actual == cond.get("value")
        op = cond.get("op", "ge")
        return {
            "ge": lambda: actual >= value,
            "le": lambda: actual <= value,
            "eq": lambda: abs(actual - value) < 1e-6,
            "gt": lambda: actual > value,
            "lt": lambda: actual < value,
        }.get(op, lambda: False)()

    def _await_condition(self, cond: Dict[str, Any]) -> bool:
        for t in range(1, self.TICK_LIMIT + 1):
            self.controller.step_all(t)
            if self.interlock.e_stopped:
                return False
            for mid in self.controller.machines:
                if self._condition_met(self._telemetry_of(mid), cond):
                    return True
        return False

    # -- mission execution ---------------------------------------------------- #
    def execute_mission(self, mission: Dict[str, Any]) -> Dict[str, Any]:
        kind = mission.get("type", "?")
        if self.machine is None or self.interlock.e_stopped:
            result = {"success": False, "reason":
                      "no machines attached or e-stop latched"}
            self._log_mission(kind, result)
            return result

        steps: List[Dict[str, Any]] = list(mission.get("steps", []))
        completed = 0
        refusals: List[Dict[str, Any]] = []
        violations_before = self.controller.hard_violations
        tick = 0

        for i, step in enumerate(steps):
            machine_id = str(step.get("machine", ""))
            action = str(step.get("action", ""))
            params = dict(step.get("params", {}))

            if not self.can_control(machine_id, action):
                refusals.append({"step": i, "reason":
                                 f"capability '{action}' unknown on "
                                 f"'{machine_id}'"})
                continue
            tick += 1
            if not self.controller.dispatch(machine_id, action, tick=tick,
                                            **params):
                refusals.append({"step": i, "reason":
                                 "interlock refusal recorded"})
                continue
            completed += 1

            cond = step.get("wait_for")
            if cond and not self._await_condition(cond):
                refusals.append({"step": i, "reason": "condition timed out"})

        clean = self.controller.hard_violations == violations_before
        result = {
            "success": bool(steps) and not refusals and clean,
            "steps_total": len(steps),
            "steps_completed": completed,
            "refusals": refusals,
            "clean": clean,
        }
        self._log_mission(kind, result)
        return result
