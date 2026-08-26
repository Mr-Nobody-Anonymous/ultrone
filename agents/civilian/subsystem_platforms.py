# Copyright (c) Ultrone Contributors. All rights reserved.
"""Subsystem-composed civilian platforms (simulation-only).

These agents demonstrate the subsystem architecture on non-weaponized
machines: a survey aircraft and a delivery truck, built entirely from
composed subsystems and driven exclusively through the structured
Command interface. No combat capability exists anywhere in this module.
"""

from __future__ import annotations

import math
from typing import Any, Dict

from agents.commands import Command, CommandBus
from agents.civilian.base import CivilianMachineAgent
from agents.subsystems.platform_subsystems import (
    AutonomySubsystem,
    CommunicationSubsystem,
    HealthSubsystem,
    NavigationSubsystem,
    PayloadSubsystem,
    PowerSubsystem,
    PropulsionSubsystem,
    SensorSubsystem,
)


class SubsystemPlatformAgent(CivilianMachineAgent):
    """Common wiring: a CommandBus over composed subsystems."""

    #: Hierarchical capability leaves shared by these platforms.
    _CAPABILITY_LEAVES = ("storage", "transmit", "receive", "diagnostics",
                          "faults", "task_execution")

    def __init__(self, unit_id: str, **kwargs) -> None:
        super().__init__(unit_id, **kwargs)
        self.bus = CommandBus()

    # -- standard platform API (mirrors SubsystemControlledAgent) -------- #
    def register_subsystem(self, subsystem) -> None:
        self.bus.register(subsystem)

    def execute(self, command: Command):
        return self.bus.execute(command)

    def subsystem_names(self):
        return self.bus.names()

    def get_subsystem(self, name: str):
        return self.bus.get(name)

    def available_capabilities(self) -> Dict[str, Any]:
        from agents.capabilities import HierarchicalCapabilitySet

        return HierarchicalCapabilitySet(
            self._CAPABILITY_LEAVES).available()

    @property
    def platform_state(self):
        from agents.state import PlatformStateView

        return PlatformStateView(self.bus)

    def tick_platform(self, tick: int) -> None:
        self.controller.step_all(tick)
        for name in self.bus.names():
            subsystem = self.bus.get(name)
            if hasattr(subsystem, "tick"):
                subsystem.tick(tick)


class SurveyAircraftAgent(SubsystemPlatformAgent):
    """Air domain (civilian): aerial survey aircraft with subsystems."""

    MACHINE_KIND = "survey_aircraft"

    def __init__(self, unit_id: str, seed: int = 0, **kwargs) -> None:
        super().__init__(unit_id, seed=seed, **kwargs)
        self.propulsion = PropulsionSubsystem(
            fuel_capacity=60.0, burn_per_tick_at_full=0.4, max_speed=4.0)
        self.power = PowerSubsystem(generation_kw=3.0)
        self.navigation = NavigationSubsystem(x=2.0, y=2.0)
        self.sensors = SensorSubsystem(seed=seed)
        self.comms = CommunicationSubsystem()
        self.health = HealthSubsystem(wear_rate=0.02)
        self.autonomy = AutonomySubsystem()
        for subsystem in (self.propulsion, self.power, self.navigation,
                          self.sensors, self.comms, self.health,
                          self.autonomy):
            self.register_subsystem(subsystem)

    def execute_mission(self, mission: Dict[str, Any]) -> Dict[str, Any]:
        waypoints = [(float(x), float(y))
                     for x, y in mission.get("waypoints", [])]
        if not waypoints or self.interlock.e_stopped:
            return {"success": False, "reason": "no waypoints or e-stop"}

        self.execute(Command("propulsion", "start_engine"))
        scanned = 0
        for wx, wy in waypoints:
            self.execute(Command("navigation", "set_destination",
                                 {"position": [wx, wy]}))
            for tick in range(1, 200):
                dist = self.navigation.distance_to_destination()
                if dist <= 0.5:
                    break
                bearing = math.atan2(wy - self.navigation.y,
                                     wx - self.navigation.x)
                self.execute(Command("navigation", "set_heading",
                                     {"deg": math.degrees(bearing)}))
                throttle = min(1.0, dist / 10.0)
                self.execute(Command("propulsion", "set_throttle",
                                     {"value": throttle}))
                # Fly: integrate position along the current heading.
                speed = self.propulsion.speed_available
                rad = math.radians(self.navigation.heading_deg)
                self.navigation.x += math.cos(rad) * speed
                self.navigation.y += math.sin(rad) * speed
                self.tick_platform(tick)

            scan = self.execute(Command("sensors", "scan", {"targets": 2}))
            if scan.success:
                scanned += 1
            self.execute(Command("power", "recharge", {"pct": 1.0}))

        self.execute(Command("propulsion", "stop_engine"))
        diag = self.execute(Command("health", "run_diagnostics"))
        return {
            "success": scanned == len(waypoints),
            "waypoints_scanned": scanned,
            "waypoints_total": len(waypoints),
            "fuel_remaining": round(self.propulsion.fuel, 3),
            "wear": diag.value["wear"] if diag.success else None,
        }


class DeliveryTruckAgent(SubsystemPlatformAgent):
    """Land domain (civilian): electric delivery truck with subsystems."""

    MACHINE_KIND = "delivery_truck"

    def __init__(self, unit_id: str, **kwargs) -> None:
        super().__init__(unit_id, **kwargs)
        self.payload = PayloadSubsystem(capacity_kg=500.0)
        self.power = PowerSubsystem(battery_pct=90.0, generation_kw=0.0)
        self.navigation = NavigationSubsystem(x=0.0, y=0.0)
        self.comms = CommunicationSubsystem()
        self.autonomy = AutonomySubsystem()
        for subsystem in (self.payload, self.power, self.navigation,
                          self.comms, self.autonomy):
            self.register_subsystem(subsystem)

    def execute_mission(self, mission: Dict[str, Any]) -> Dict[str, Any]:
        destination = tuple(float(v) for v in
                            mission.get("destination", [20.0, 20.0]))
        cargo_kg = float(mission.get("cargo_kg", 50.0))
        loaded = self.execute(Command("payload", "load",
                                      {"kg": cargo_kg}))
        if not loaded.success:
            return {"success": False,
                    "reason": loaded.reason or "overload refused"}
        self.execute(Command("navigation", "set_destination",
                             {"position": list(destination)}))

        for tick in range(1, 300):
            dist = self.navigation.distance_to_destination()
            if dist <= 0.5:
                break
            bearing = math.atan2(destination[1] - self.navigation.y,
                                 destination[0] - self.navigation.x)
            self.execute(Command("navigation", "set_heading",
                                 {"deg": math.degrees(bearing)}))
            step_speed = min(2.0, max(0.5, dist * 0.25))
            self.navigation.x += math.cos(bearing) * step_speed
            self.navigation.y += math.sin(bearing) * step_speed
            # Electric drive drains stored energy while moving.
            self.power.set_load(1.2)
            self.power.battery_pct = max(
                0.0, self.power.battery_pct - 0.08)
            self.tick_platform(tick)

        arrived = self.navigation.distance_to_destination() <= 0.5
        unloaded = self.execute(Command("payload", "unload")).value
        return {
            "success": bool(arrived and loaded.success),
            "delivered_kg": float(unloaded or 0.0),
            "battery_pct": round(self.power.battery_pct, 3),
        }