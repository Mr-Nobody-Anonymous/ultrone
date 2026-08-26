# Copyright (c) Ultrone Contributors. All rights reserved.
"""Delivery-drone operator: battery-aware parcel delivery missions."""

from __future__ import annotations

import math
from typing import Any, Dict, Optional, Tuple

from agents.civilian.base import CivilianMachineAgent


class DeliveryDroneAgent(CivilianMachineAgent):
    """Flies a sandbox LogisticsDrone; manages battery reserve honestly."""

    MACHINE_KIND = "drone_logistics"
    TICK_LIMIT = 500

    def execute_mission(self, mission: Dict[str, Any]) -> Dict[str, Any]:
        if self.machine is None or self.interlock.e_stopped:
            result = {"success": False, "reason": "no machine or e-stop"}
            self._log_mission(mission.get("type", "?"), result)
            return result
        dest = tuple(float(v) for v in mission["destination"])
        payload = float(mission.get("payload_kg", 1.0))
        altitude = float(mission.get("altitude", 12.0))
        result = self._deliver(dest, payload, altitude)
        self._log_mission(mission.get("type", "deliver"), result)
        return result

    # ------------------------------------------------------------------ #
    def _fly_to(self, tx: float, ty: float, cruise_z: float,
                tick_limit: int) -> bool:
        drone = self.machine
        # Climb first.
        for t in range(1, tick_limit + 1):
            if drone.z >= cruise_z:
                break
            if not drone.command_velocity(0.0, 0.0, 0.8, tick=t):
                return False
            self.controller.step_all(t)
        # Cruise horizontally toward the destination.
        t = 0
        while math.hypot(tx - drone.x, ty - drone.y) > 0.6 and t < tick_limit:
            dx, dy = tx - drone.x, ty - drone.y
            vx = max(-drone.CRUISE_SPEED,
                     min(drone.CRUISE_SPEED, dx * 0.3))
            vy = max(-drone.CRUISE_SPEED,
                     min(drone.CRUISE_SPEED, dy * 0.3))
            # Normalize the pair so diagonal commands respect the cap.
            mag = math.hypot(vx, vy)
            if mag > drone.CRUISE_SPEED:
                vx *= drone.CRUISE_SPEED / mag
                vy *= drone.CRUISE_SPEED / mag
            if not drone.command_velocity(vx, vy, 0.0, tick=t):
                return False                     # no-fly / reserve refusal
            self.controller.step_all(t)
            t += 1
        # Descend only when directly above the destination.
        for t in range(1, tick_limit + 1):
            if drone.z == 0.0:
                break
            hover_vx = max(-0.5, min(0.5, (tx - drone.x) * 0.3))
            hover_vy = max(-0.5, min(0.5, (ty - drone.y) * 0.3))
            if not drone.command_velocity(hover_vx, hover_vy, -0.8, tick=t):
                return False
            self.controller.step_all(t)
        return math.hypot(tx - drone.x, ty - drone.y) <= 1.0 and drone.z == 0.0

    def _recharge_if_needed(self, minimum_pct: float) -> int:
        drone = self.machine
        ticks = 0
        if drone.battery_pct >= minimum_pct:
            return 0
        drone.command_recharge(tick=0)
        while drone.battery_pct < minimum_pct and ticks < 200:
            self.controller.step_all(0)
            ticks += 1
        drone.charging = False
        return ticks

    def _deliver(self, dest: Tuple[float, float], payload_kg: float,
                 altitude: float) -> Dict[str, Any]:
        drone = self.machine
        self._recharge_if_needed(minimum_pct=60.0)
        if not drone.command_pick_payload(payload_kg, tick=1):
            return {"success": False, "reason": "payload refused"}

        outbound_ok = self._fly_to(dest[0], dest[1], altitude,
                                   self.TICK_LIMIT)
        delivered = False
        if outbound_ok:
            drone.command_drop_payload(tick=1)
            delivered = True
        returned = self._fly_to(*self._home_xy(), altitude, self.TICK_LIMIT)
        self._recharge_if_needed(minimum_pct=60.0)

        return {
            "success": bool(outbound_ok and delivered and returned),
            "delivered": delivered,
            "returned_home": returned,
            "final_battery_pct": round(drone.battery_pct, 2),
            "hard_violations": self.controller.hard_violations,
        }

    def _home_xy(self) -> Tuple[float, float]:
        home = getattr(self.machine, "x", 0.0), getattr(self.machine, "y", 0.0)
        # Home is the drone's spawn point, recorded at attach time.
        return getattr(self, "_home", home)

    def attach_machine(self, machine) -> None:
        super().attach_machine(machine)
        self._home = (machine.x, machine.y)
