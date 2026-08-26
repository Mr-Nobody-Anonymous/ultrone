# Copyright (c) Ultrone Contributors. All rights reserved.
"""Crane operator: sway-aware load lift-and-place missions."""

from __future__ import annotations

from typing import Any, Dict

from agents.civilian.base import CivilianMachineAgent


class CraneOperatorAgent(CivilianMachineAgent):
    """Drives a sandbox OverheadCrane with anti-sway discipline."""

    MACHINE_KIND = "crane_operator"
    TICK_LIMIT = 400

    def execute_mission(self, mission: Dict[str, Any]) -> Dict[str, Any]:
        if self.machine is None or self.interlock.e_stopped:
            result = {"success": False, "reason": "no machine or e-stop"}
            self._log_mission(mission.get("type", "?"), result)
            return result
        result = self._lift_and_place(
            pick=tuple(mission["pick"]),
            place=tuple(mission["place"]),
            load_kg=float(mission.get("load_kg", 100.0)),
        )
        self._log_mission(mission.get("type", "lift_place"), result)
        return result

    def _move_axis_to(self, getter: Any, setter: Any, target: float,
                      tick_budget: int) -> bool:
        """Move one axis to target, yielding whenever sway locks motion.

        The interlock refusing a move is not a failure -- it is the crane
        telling us to hold still while the load stops swinging. Damped
        waiting is the correct operator behavior.
        """
        t = 0
        while abs(getter() - target) > 0.15 and t < tick_budget:
            v = max(-1.0, min(1.0, (target - getter()) * 0.4))
            if not setter(v, self.TICK_LIMIT + t):
                self.controller.step_all(self.TICK_LIMIT + t)   # damp
            else:
                self.controller.step_all(self.TICK_LIMIT + t)
            t += 1
        settled = abs(getter() - target) <= 0.15
        setter(0.0, self.TICK_LIMIT + t)         # zero the actuator
        for _ in range(tick_budget):             # allow residual sway to damp
            if abs(self.machine.sway_deg) <= 0.05:
                break
            self.controller.step_all(self.TICK_LIMIT + t)
            t += 1
        return settled

    def _lift_and_place(self, pick: tuple, place: tuple,
                        load_kg: float) -> Dict[str, Any]:
        crane = self.machine
        steps_ok = True
        # 1) travel empty to the pick location.
        steps_ok &= self._move_axis_to(
            lambda: crane.bridge,
            lambda v, t: crane.command_move(v, crane._v_trolley, t),
            float(pick[0]), self.TICK_LIMIT)
        steps_ok &= self._move_axis_to(
            lambda: crane.trolley,
            lambda v, t: crane.command_move(crane._v_bridge, v, t),
            float(pick[1]), self.TICK_LIMIT)
        # 2) lower, attach, raise.
        steps_ok &= crane.command_hoist(-(crane.hoist_height - 1.0), 0)
        attach_ok = crane.command_attach_load(load_kg, 0)
        steps_ok &= attach_ok
        steps_ok &= crane.command_hoist(crane.HOIST_RANGE[1]
                                        - crane.hoist_height, 0)
        # 3) travel loaded to the drop location.
        steps_ok &= self._move_axis_to(
            lambda: crane.bridge,
            lambda v, t: crane.command_move(v, crane._v_trolley, t),
            float(place[0]), self.TICK_LIMIT)
        steps_ok &= self._move_axis_to(
            lambda: crane.trolley,
            lambda v, t: crane.command_move(crane._v_bridge, v, t),
            float(place[1]), self.TICK_LIMIT)
        # 4) lower and release.
        steps_ok &= crane.command_hoist(-(crane.hoist_height - 0.8), 0)
        release_ok = crane.command_release_load(0)
        crane.command_hoist(crane.HOIST_RANGE[1] - crane.hoist_height, 0)

        return {
            "success": bool(steps_ok and release_ok),
            "load_delivered_kg": load_kg if release_ok else 0.0,
            "final_sway_deg": round(crane.sway_deg, 3),
            "hard_violations": self.controller.hard_violations,
        }
