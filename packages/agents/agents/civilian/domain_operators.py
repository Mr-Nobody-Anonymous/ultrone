# Copyright (c) Ultrone Contributors. All rights reserved.
"""Domain-coverage operators: sea, land, space, and cyber ANALYSIS.

Civilian counterparts to the platform domains, all simulation-only:

- VesselOperatorAgent   (sea)  -- survey vessel station-keeping + sampling
- RailOperatorAgent     (land) -- freight run with overspeed protection
- SatelliteOpsAgent     (space)-- imaging campaigns inside orbital windows
- NetworkAnalystAgent   (cyber)-- passive baseline/analyze; observe-only

Same governance as the rest of ``agents/civilian``: no ENGAGE capability,
every command interlocked, everything deterministic.
"""

from __future__ import annotations

import math
from typing import Any, Dict

from agents.civilian.base import CivilianMachineAgent


class VesselOperatorAgent(CivilianMachineAgent):
    """Sea domain: survey-vessel transit + station sampling."""

    MACHINE_KIND = "vessel_operator"
    TICK_LIMIT = 500
    REFUEL_BELOW = 25.0

    def attach_vessel(self, machine) -> None:
        self.attach_machine(machine)

    def execute_mission(self, mission: Dict[str, Any]) -> Dict[str, Any]:
        vessel = getattr(self, "machine", None)
        stations = [(float(x), float(y))
                    for x, y in mission.get("stations", [])]
        if vessel is None or not stations or self.interlock.e_stopped:
            result = {"success": False,
                      "reason": "no vessel/stations or e-stop"}
            self._log_mission(mission.get("type", "?"), result)
            return result

        sampled = 0
        for sx, sy in stations:
            self._transit(vessel, sx, sy)
            if math.hypot(sx - vessel.x, sy - vessel.y) <= 0.6 \
                    and vessel.collect_sample(tick=0):
                sampled += 1
            if vessel.fuel < self.REFUEL_BELOW:
                vessel.command_refuel(tick=0)

        result = {
            "success": sampled == len(stations),
            "samples_collected": sampled,
            "stations_total": len(stations),
            "fuel_remaining": round(vessel.fuel, 2),
        }
        self._log_mission(mission.get("type", "survey"), result)
        return result

    def _transit(self, vessel, tx: float, ty: float) -> None:
        for t in range(1, self.TICK_LIMIT + 1):
            dx, dy = tx - vessel.x, ty - vessel.y
            dist = math.hypot(dx, dy)
            if dist <= 0.6:
                vessel.command_velocity(0.0, tick=t)
                break
            turn = (math.atan2(dy, dx) - vessel.heading + math.pi) \
                % (2 * math.pi) - math.pi
            vessel.heading += max(-0.4, min(0.4, turn * 1.5))
            linear = min(vessel.MAX_SPEED, max(0.3, dist * 0.3))
            vessel.command_velocity(linear, tick=t)
            vessel.step(t)


class RailOperatorAgent(CivilianMachineAgent):
    """Land domain: freight runs respecting overspeed and door rules."""

    MACHINE_KIND = "rail_operator"
    TICK_LIMIT = 300

    def attach_railcar(self, machine) -> None:
        self.attach_machine(machine)

    def execute_mission(self, mission: Dict[str, Any]) -> Dict[str, Any]:
        car = getattr(self, "machine", None)
        cargo = int(mission.get("cargo", 10))
        if car is None or self.interlock.e_stopped:
            result = {"success": False,
                      "reason": "no railcar or e-stop"}
            self._log_mission(mission.get("type", "?"), result)
            return result

        car.command_load(cargo, tick=1)
        delivered_units = 0
        for t in range(1, self.TICK_LIMIT + 1):
            remaining = car.TRACK_LENGTH - car.position
            speed = min(car.SPEED_LIMIT, max(0.5, remaining * 0.3)) \
                if remaining > 0.5 else 0.0
            car.command_throttle(speed, tick=t)
            car.step(t)
            # Arrived = within half a unit of the terminus AND fully stopped.
            if car.TRACK_LENGTH - car.position <= 0.5 and car.speed == 0.0:
                delivered_units = car.command_unload(tick=t)
                break

        result = {
            "success": delivered_units == cargo,
            "delivered_units": delivered_units,
        }
        self._log_mission(mission.get("type", "freight_run"), result)
        return result


class SatelliteOpsAgent(CivilianMachineAgent):
    """Space domain: imaging campaigns within orbital sensor windows."""

    MACHINE_KIND = "satellite_operator"
    TICK_LIMIT = 400

    def attach_satellite(self, machine) -> None:
        self.attach_machine(machine)

    def execute_mission(self, mission: Dict[str, Any]) -> Dict[str, Any]:
        sat = getattr(self, "machine", None)
        targets = list(mission.get("targets", []))
        if sat is None or not targets or self.interlock.e_stopped:
            result = {"success": False,
                      "reason": "no satellite/targets or e-stop"}
            self._log_mission(mission.get("type", "?"), result)
            return result

        captured: Dict[str, int] = {t: 0 for t in targets}
        for t in range(1, self.TICK_LIMIT + 1):
            pending = [tgt for tgt in targets if captured[tgt] < 1]
            if not pending:
                break
            for target_id in pending:
                if sat.command_image(target_id, tick=t):
                    captured[target_id] += 1
            self.controller.step_all(t)

        downlinked = sat.command_downlink(tick=self.TICK_LIMIT + 1)
        result = {
            "success": all(v >= 1 for v in captured.values()),
            "images_captured": dict(captured),
            "downlinked": downlinked,
        }
        self._log_mission(mission.get("type", "imaging_campaign"), result)
        return result


class NetworkAnalystAgent(CivilianMachineAgent):
    """Cyber domain: passive baseline learning and deviation analysis.

    Analysis only. The bound machine exposes no way to send, modify, or
    exploit anything, so neither does this agent.
    """

    MACHINE_KIND = "network_analyst"
    BASELINE_SCANS = 6

    def attach_sensor(self, machine) -> None:
        self.attach_machine(machine)

    def execute_mission(self, mission: Dict[str, Any]) -> Dict[str, Any]:
        sensor = getattr(self, "machine", None)
        hosts = list(mission.get("hosts", []))
        if sensor is None or self.interlock.e_stopped:
            result = {"success": False,
                      "reason": "no sensor or e-stop"}
            self._log_mission(mission.get("type", "?"), result)
            return result

        sensor.register_hosts(hosts)
        for t in range(1, self.BASELINE_SCANS + 1):
            sensor.command_scan(tick=t)

        baseline = sensor.learn_baseline()
        alerts = sensor.analyze()
        result = {
            "success": True,
            "hosts_monitored": len(hosts),
            "baseline": baseline,
            "alerts": alerts,
        }
        self._log_mission(mission.get("type", "baseline_analyze"), result)
        return result