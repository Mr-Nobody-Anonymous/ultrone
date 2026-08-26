# Copyright (c) Ultrone Contributors. All rights reserved.
"""Bridge: subsystem platforms inside the Universal Control Layer.

Provides the unified ``PlatformState`` builder and a
``SubsystemPlatformController`` -- a PlatformController whose single
actuation path is the platform's CommandBus (UCL -> CommandBus ->
subsystems -> state), with no domain adapter involved.

The state schema is standardized across every platform kind::

    PlatformState
    ├── position            (from navigation; z when derivable)
    ├── velocity            (speed_available x heading, else None)
    ├── orientation         (heading)
    ├── subsystem_states    (per-subsystem status dicts)
    ├── resources           (fuel / battery / payload / pools)
    ├── health              ({active_fault_count})
    ├── active_faults       (per-subsystem fault entries)
    ├── active_tasks        (sum of queued tasks)
    └── timestamp           (tick)
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from agents.commands import Command, CommandBus
from sandbox.ucl import PlatformController


# --------------------------------------------------------------------- #
# Unified platform state                                                 #
# --------------------------------------------------------------------- #
def _derived_velocity(states: Dict[str, Any],
                      nav: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Speed-along-heading vector when propulsion/flight data exists."""
    speed = None
    propulsion = states.get("propulsion")
    if isinstance(propulsion, dict):
        speed = propulsion.get("speed_available")
    flight = states.get("flight_control")
    if speed is None and isinstance(flight, dict):
        speed = flight.get("speed")
    heading = nav.get("heading") if isinstance(nav, dict) else None
    if not speed or heading is None:
        return None
    rad = math.radians(float(heading))
    return {"x": round(math.cos(rad) * float(speed), 3),
            "y": round(math.sin(rad) * float(speed), 3),
            "z": None}


def build_platform_state(bus: CommandBus,
                         tick: int = 0) -> Dict[str, Any]:
    """Standardized snapshot across every registered subsystem."""
    states: Dict[str, Any] = {}
    active_faults: List[Dict[str, Any]] = []
    resources: Dict[str, Any] = {}
    for name in bus.names():
        subsystem = bus.get(name)
        status = subsystem.status()
        states[name] = status
        active_faults.extend(
            {"subsystem": name, **f} for f in getattr(subsystem, "faults", []))
        if hasattr(subsystem, "fuel"):
            resources["fuel"] = round(subsystem.fuel, 3)
        if hasattr(subsystem, "battery_pct"):
            resources["battery_pct"] = round(subsystem.battery_pct, 3)
        if hasattr(subsystem, "carried_kg"):
            resources["payload_kg"] = round(subsystem.carried_kg, 3)
        if hasattr(subsystem, "levels"):
            resources.update({f"level_{k}": round(v, 3)
                              for k, v in subsystem.levels.items()})
    nav = states.get("navigation", {})
    return {
        "timestamp": tick,
        "position": {"x": nav.get("x"), "y": nav.get("y"),
                     "z": None},
        "velocity": _derived_velocity(states, nav),
        "orientation": {k: nav[k] for k in ("heading",)
                        if k in nav},
        "subsystem_states": states,
        "resources": resources,
        "health": {"active_fault_count": len(active_faults)},
        "active_faults": active_faults,
        "active_tasks": sum(
            s.get("queued_tasks", 0) for s in states.values()),
    }


def get_platform_state(source: Any) -> Dict[str, Any]:
    """Uniform ``what happened`` accessor.

    Accepts a ``SubsystemControlledAgent``, any UCL controller with a
    ``command_bus``, or a bare CommandBus -- and returns the same
    standardized snapshot either way.
    """
    bus = getattr(source, "bus", None) \
        or getattr(source, "command_bus", None)
    if bus is None and hasattr(source, "names") \
            and hasattr(source, "execute"):
        bus = source                      # a CommandBus itself
    if bus is None:
        raise TypeError("source has no command bus")
    return build_platform_state(bus)


class SubsystemMachineShim:
    """Duck-typed 'machine' exposing a CommandBus platform to the UCL."""

    KIND = "subsystem_platform"

    def __init__(self, machine_id: str, bus: CommandBus) -> None:
        self.machine_id = machine_id
        self.bus = bus

    def telemetry(self) -> Dict[str, Any]:
        return build_platform_state(self.bus)


class SubsystemPlatformController(PlatformController):
    """UCL controller whose actuation is exclusively CommandBus-based."""

    def __init__(self, machine_id: str, bus: CommandBus,
                 world_model=None) -> None:
        shim = SubsystemMachineShim(machine_id, bus)
        super().__init__(shim, world_model=world_model,
                         command_bus=bus)

    def get_state(self) -> Dict[str, Any]:
        return build_platform_state(self.command_bus)