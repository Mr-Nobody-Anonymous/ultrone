# Copyright (c) Ultrone Contributors. All rights reserved.
"""Universal Control Layer: unified simulation platform control.

One abstract interface -- ``PlatformController`` -- over EVERY simulated
machine, so reasoning code never branches on platform kind:

    controller.execute_task({"type": "navigate", "to": [15, 15]})

works identically for a delivery drone (air), a railcar (land), a survey
vessel (sea), an imaging satellite (space), or a network sensor (cyber),
routed through a per-domain PlatformAdapter.

*** SIMULATION SAFETY BOUNDARY ***

This layer terminates at simulated machines defined in
``sandbox/machines.py``. There is deliberately NO transport, driver, or
API surface toward real aircraft, vehicles, vessels, satellites, weapons,
or networks. Every actuation path ends in a deterministic sandbox
machine guarded by its own SafetyInterlock. This boundary is enforced by
test (``tests/test_ucl.py``).
"""

from __future__ import annotations

import enum
import hashlib
import json
import math
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from sandbox import machines as _m


# --------------------------------------------------------------------- #
# Capability model                                                       #
# --------------------------------------------------------------------- #
class Capability(str, enum.Enum):
    SENSE = "sense"
    MOVE = "move"
    COMMUNICATE = "communicate"
    NAVIGATE = "navigate"
    TRACK = "track"
    OBSERVE = "observe"
    MANAGE_POWER = "manage_power"
    MANAGE_PAYLOAD = "manage_payload"
    EXECUTE_TASK = "execute_task"


#: Data-driven capability sheets keyed by machine KIND. Adding platform
#: #500 means adding one row here -- no agent code changes.
CAPABILITY_SHEETS: Dict[str, frozenset] = {
    "delivery_drone": frozenset({
        Capability.SENSE, Capability.MOVE, Capability.NAVIGATE,
        Capability.COMMUNICATE, Capability.MANAGE_POWER,
        Capability.MANAGE_PAYLOAD}),
    "robot": frozenset({
        Capability.SENSE, Capability.MOVE, Capability.NAVIGATE,
        Capability.MANAGE_POWER}),
    "railcar": frozenset({
        Capability.MOVE, Capability.NAVIGATE, Capability.MANAGE_PAYLOAD}),
    "research_vessel": frozenset({
        Capability.SENSE, Capability.MOVE, Capability.NAVIGATE,
        Capability.OBSERVE, Capability.MANAGE_POWER}),
    "eo_satellite": frozenset({
        Capability.SENSE, Capability.MOVE, Capability.OBSERVE,
        Capability.COMMUNICATE, Capability.MANAGE_POWER}),
    "network_sensor": frozenset({Capability.SENSE, Capability.OBSERVE}),
    "arm": frozenset({Capability.MANAGE_PAYLOAD,
                      Capability.EXECUTE_TASK}),
    "conveyor": frozenset({Capability.EXECUTE_TASK}),
    "tank": frozenset({Capability.MANAGE_POWER, Capability.EXECUTE_TASK}),
    "hvac": frozenset({Capability.EXECUTE_TASK}),
    "crane": frozenset({Capability.MANAGE_PAYLOAD,
                        Capability.EXECUTE_TASK}),
    "cnc": frozenset({Capability.EXECUTE_TASK}),
    "microgrid": frozenset({Capability.MANAGE_POWER,
                            Capability.EXECUTE_TASK}),
    "water_pumps": frozenset({Capability.MANAGE_POWER,
                              Capability.EXECUTE_TASK}),
}


class CapabilityModel:
    """Registry lookup: which universal capabilities does a kind support?"""

    @staticmethod
    def capabilities_for(kind: str) -> frozenset:
        return CAPABILITY_SHEETS.get(kind, frozenset())

    @staticmethod
    def supports(kind: str, capability) -> bool:
        cap = Capability(capability)
        return cap in CapabilityModel.capabilities_for(kind)

    @staticmethod
    def sheet(kind: str) -> Dict[str, Any]:
        caps = sorted(c.value for c in CapabilityModel.capabilities_for(kind))
        return {"kind": kind, "capabilities": caps}


# --------------------------------------------------------------------- #
# Domain adapters                                                        #
# --------------------------------------------------------------------- #
class PlatformAdapter:
    """Translates universal commands into sandbox machine behavior."""

    DOMAIN: str = "unknown"
    HANDLES_KINDS: frozenset = frozenset()

    def matches(self, machine) -> bool:
        return machine.KIND in self.HANDLES_KINDS

    def position(self, machine) -> Optional[Tuple[float, ...]]:
        return None

    def move(self, machine, command: Dict[str, Any], tick: int) -> bool:
        raise NotImplementedError(f"{type(machine).__name__} cannot move")

    def sense(self, machine, request: str) -> Any:
        return machine.telemetry()

    def communicate(self, machine, message: Dict[str, Any],
                    tick: int) -> Dict[str, Any]:
        return {"delivered": True, "note": "logged", "message": message}

    def manage_system(self, machine, command: Dict[str, Any],
                      tick: int) -> bool:
        return False


class AirAdapter(PlatformAdapter):
    DOMAIN = "air"
    HANDLES_KINDS = frozenset({"delivery_drone"})

    def position(self, machine):
        return (machine.x, machine.y, machine.z)

    def move(self, machine, command, tick):
        return machine.command_velocity(
            float(command.get("vx", 0)), float(command.get("vy", 0)),
            float(command.get("vz", 0)), tick=tick)

    def sense(self, machine, request):
        if request == "position":
            return {"x": machine.x, "y": machine.y, "z": machine.z}
        if request == "battery":
            return {"battery_pct": machine.battery_pct}
        return machine.telemetry()

    def communicate(self, machine, message, tick):
        if message.get("action") == "downlink":
            count = machine.command_downlink(tick=tick)
            return {"delivered": True, "downlinked_images": count}
        return super().communicate(machine, message, tick)

    def manage_system(self, machine, command, tick):
        action = command.get("action")
        if action == "recharge":
            return machine.command_recharge(tick=tick)
        if action == "pick_payload":
            return machine.command_pick_payload(
                float(command.get("kg", 0)), tick=tick)
        if action == "drop_payload":
            return machine.command_drop_payload(tick=tick)
        if action == "declare_nofly":
            machine.declare_nofly_zone(
                float(command["cx"]), float(command["cy"]),
                float(command["radius"]))
            return True
        return False


class LandAdapter(PlatformAdapter):
    DOMAIN = "land"
    HANDLES_KINDS = frozenset({"robot", "railcar"})

    def position(self, machine):
        if machine.KIND == "robot":
            return (machine.x, machine.y)
        return (machine.position, 0.0)

    def move(self, machine, command, tick):
        if machine.KIND == "robot":
            return machine.command_velocity(
                float(command.get("linear", 0)),
                float(command.get("angular", 0)), tick=tick)
        return machine.command_throttle(float(command.get("speed", 0)),
                                        tick=tick)

    def sense(self, machine, request):
        if request == "position":
            pos = self.position(machine)
            return {"x": pos[0], "y": pos[1]}
        return machine.telemetry()

    def manage_system(self, machine, command, tick):
        if machine.KIND != "railcar":
            return False
        action = command.get("action")
        if action == "load":
            return machine.command_load(int(command.get("units", 0)),
                                        tick=tick)
        if action == "unload":
            return machine.command_unload(tick=tick) > 0
        if action == "doors":
            return machine.command_doors(bool(command.get("open", False)),
                                         tick=tick)
        return False


class SeaAdapter(PlatformAdapter):
    DOMAIN = "sea"
    HANDLES_KINDS = frozenset({"research_vessel"})

    def position(self, machine):
        return (machine.x, machine.y)

    def move(self, machine, command, tick):
        heading = command.get("heading_deg")
        if heading is not None:
            machine.heading = float(heading)
        return machine.command_velocity(float(command.get("linear", 0)),
                                        tick=tick)

    def sense(self, machine, request):
        if request == "position":
            return {"x": machine.x, "y": machine.y,
                    "fuel": round(machine.fuel, 3)}
        return machine.telemetry()

    def manage_system(self, machine, command, tick):
        action = command.get("action")
        if action == "refuel":
            return machine.command_refuel(tick=tick)
        if action == "collect_sample":
            return machine.collect_sample(tick=tick)
        return False


class SpaceAdapter(PlatformAdapter):
    DOMAIN = "space"
    HANDLES_KINDS = frozenset({"eo_satellite"})

    def position(self, machine):
        return (machine.phase_deg,)

    def move(self, machine, command, tick):
        # Orbital motion is passive and deterministic; "move" is a
        # station-keeping acknowledgment.
        return True

    def sense(self, machine, request):
        if request == "position":
            return {"phase_deg": round(machine.phase_deg, 2)}
        if request == "battery":
            return {"battery_pct": machine.battery_pct}
        return machine.telemetry()

    def communicate(self, machine, message, tick):
        if message.get("action") == "downlink":
            count = machine.command_downlink(tick=tick)
            return {"delivered": True, "downlinked_images": count}
        return super().communicate(machine, message, tick)


class CyberAdapter(PlatformAdapter):
    DOMAIN = "cyber"
    HANDLES_KINDS = frozenset({"network_sensor"})

    def sense(self, machine, request):
        if request == "scan":
            return machine.command_scan(tick=0)
        return machine.telemetry()

    # No move/manage: the sensor observes. That IS the safety boundary.


class FacilityAdapter(PlatformAdapter):
    """Static industrial machines (production/power/water/facility).

    ``manage_system`` routes whitelisted actions to the machine's own
    ``command_<action>`` methods -- the machine's interlock still refuses
    anything outside its envelope.
    """

    DOMAIN = "facility"
    HANDLES_KINDS = frozenset({
        "arm", "conveyor", "tank", "hvac", "crane", "cnc",
        "microgrid", "water_pumps",
    })

    def move(self, machine, command, tick):
        return False                      # static installations

    def manage_system(self, machine, command, tick):
        action = str(command.get("action", ""))
        if not action:
            return False
        method = getattr(machine, f"command_{action}", None)
        if method is None:
            return False
        try:
            return bool(method(*command.get("args", [])))
        except TypeError:
            return False


ADAPTERS: Tuple[PlatformAdapter, ...] = (
    AirAdapter(), LandAdapter(), SeaAdapter(), SpaceAdapter(), CyberAdapter(),
    FacilityAdapter(),
)

KIND_TO_DOMAIN: Dict[str, str] = {
    kind: adapter.DOMAIN
    for adapter in ADAPTERS for kind in adapter.HANDLES_KINDS
}


def adapter_for(machine) -> PlatformAdapter:
    for adapter in ADAPTERS:
        if adapter.matches(machine):
            return adapter
    raise ValueError(
        f"no domain adapter for machine kind '{machine.KIND}' -- the "
        f"universal control layer only drives sandbox machines")


class NullAdapter(PlatformAdapter):
    """Fallback for bus-driven platforms without a physical model."""


@dataclass(frozen=True)
class _BusCommand:
    """Minimal structured-command shape accepted by any CommandBus.

    Structurally identical to ``agents.commands.Command`` -- duck-typed
    on purpose so the universal layer stays free of agents/* imports.
    """

    subsystem: str
    action: str
    parameters: Dict[str, Any] = field(default_factory=dict)

    DOMAIN = "abstract"
    HANDLES_KINDS = frozenset()

    def move(self, machine, command, tick):
        return False


class PlatformController:
    """One interface for any simulated platform, in any domain.

    When a ``command_bus`` is attached there is exactly ONE authoritative
    actuation path::

        UCL verb -> structured Command -> CommandBus -> subsystems
                 -> platform state

    ``execute_command`` takes a Command directly; ``manage_system`` /
    ``move`` / ``communicate`` accept either a structured Command or a
    plain dict ({subsystem, action, parameters} / destination keys /
    recipient keys) and translate onto the same bus, so no parallel
    command mechanism exists for bus-driven platforms. Domain-adapter
    methods remain only for machines without a bus.
    """

    def __init__(self, machine,
                 world_model: Optional["WorldModel"] = None,
                 stepper=None,
                 command_bus=None) -> None:
        self.machine = machine
        self.command_bus = command_bus
        try:
            self.adapter = adapter_for(machine)
        except ValueError:
            if command_bus is None:
                raise
            self.adapter = NullAdapter()      # bus-driven abstract platform
        self.world = world_model
        self.stepper = stepper          # e.g., MachineController.step_all
        self.tick = 0

    # -- single-path plumbing -------------------------------------------------- #
    @staticmethod
    def _as_command(command):
        """Duck-typed normalization to a bus-routable command spec.

        Returns ``(subsystem, action, parameters)`` when ``command``
        already looks like a structured command (a agents.commands.Command
        instance or an equivalent dict); ``None`` otherwise. Deliberately
        duck-typed so sandbox/ never imports agents/.
        """
        if command is None:
            return None
        if hasattr(command, "subsystem") and hasattr(command, "action"):
            params = getattr(command, "parameters", None) or {}
            return command.subsystem, command.action, dict(params)
        if isinstance(command, dict):
            subsystem = command.get("subsystem")
            action = command.get("action")
            if subsystem and action:
                return subsystem, action, dict(command.get("parameters")
                                               or {})
        return None

    def _bus_execute(self, subsystem: str, action: str,
                     parameters: Dict[str, Any]):
        # NOTE: no agents.* import here -- the safety boundary requires
        # that sandbox/ depends only on stdlib + sandbox. CommandBus
        # accepts ANY object exposing subsystem/action/parameters.
        return self.command_bus.execute(
            _BusCommand(subsystem=subsystem, action=action,
                        parameters=parameters))

    def _log_command(self, subsystem: str, action: str, result) -> None:
        if self.world is not None:
            self.world.record_communication(self.platform_id, {
                "kind": "command",
                "subsystem": subsystem,
                "action": action,
                "success": bool(getattr(result, "success", False)),
                "reason": getattr(result, "reason", "") or "",
            })

    @property
    def platform_id(self) -> str:
        return self.machine.machine_id

    @property
    def domain(self) -> str:
        return self.adapter.DOMAIN

    def supports(self, capability) -> bool:
        return CapabilityModel.supports(self.machine.KIND, capability)

    def get_state(self) -> Dict[str, Any]:
        return self.machine.telemetry()

    def sense(self, request: str = "telemetry") -> Any:
        return self.adapter.sense(self.machine, request)

    def move(self, command: Dict[str, Any]) -> bool:
        # Bus platforms: movement IS two canonical commands on the same
        # path -- navigation.set_destination (+ optional propulsion
        # throttle). No second actuation mechanism.
        if self.command_bus is not None and isinstance(command, dict):
            target = command.get("to") or command.get("destination") \
                or command.get("position")
            if target and "navigation" in self.command_bus.names():
                result = self._bus_execute(
                    "navigation", "set_destination", {"position": target})
                speed = command.get("throttle", command.get("speed"))
                if result.success and speed is not None \
                        and "propulsion" in self.command_bus.names():
                    thr = self._bus_execute(
                        "propulsion", "set_throttle",
                        {"value": float(speed)})
                    result = result if not thr.success else result
                if result.success and self.world is not None:
                    self.world.record_position(self)
                return bool(result.success)
        accepted = self.adapter.move(self.machine, command, tick=self.tick)
        if accepted and self.world is not None:
            self.world.record_position(self)
        return accepted

    def communicate(self, message: Dict[str, Any]) -> Dict[str, Any]:
        # Bus platforms: transmission is the comms subsystem's command.
        if self.command_bus is not None and isinstance(message, dict) \
                and message.get("recipient") is not None \
                and "communications" in self.command_bus.names():
            result = self._bus_execute(
                "communications", "transmit",
                {"recipient": message.get("recipient"),
                 "content": message.get("content")})
            reply = {"delivered": bool(result.success),
                     "reason": getattr(result, "reason", "") or ""}
            if self.world is not None:
                self.world.record_communication(self.platform_id, message)
            return reply
        reply = self.adapter.communicate(self.machine, message,
                                         tick=self.tick)
        if self.world is not None:
            self.world.record_communication(self.platform_id, message)
        return reply

    def manage_system(self, command) -> bool:
        """Single-path system management.

        Accepts a structured Command (or its dict form) and routes it
        through the attached CommandBus; falls back to the domain adapter
        only when the platform has no bus.
        """
        if self.command_bus is not None:
            spec = self._as_command(command)
            if spec is not None:
                subsystem, action, parameters = spec
                result = self._bus_execute(subsystem, action, parameters)
                self._log_command(subsystem, action, result)
                return bool(result.success)
        return self.adapter.manage_system(self.machine, command,
                                          tick=self.tick)

    def execute_command(self, command) -> "CommandResult":
        """Authoritative actuation path: Command -> bus -> subsystems.

        Requires an attached ``command_bus``. The result is recorded in
        the world model's communication log when one is attached.
        """
        if self.command_bus is None:
            raise ValueError(
                "no command_bus attached: this platform is adapter-driven")
        result = self.command_bus.execute(command)
        if self.world is not None:
            self.world.record_communication(self.platform_id, {
                "kind": "command",
                "subsystem": command.subsystem,
                "action": command.action,
                "success": result.success,
                "reason": result.reason,
            })
        return result

    def _step_world(self):
        self.tick += 1
        if self.stepper is not None:
            self.stepper(self.tick)
        elif hasattr(self.machine, "step"):
            try:
                self.machine.step(self.tick)
            except TypeError:
                pass   # machines whose step takes extra args
        if self.world is not None:
            self.world.advance_tick()

    # -- high-level tasks ----------------------------------------------------- #
    def execute_task(self, task: Dict[str, Any],
                     max_ticks: int = 400) -> Dict[str, Any]:
        """Domain-independent task dispatch."""
        kind = task.get("type")
        if kind == "navigate":
            return self._task_navigate(tuple(task["to"]), max_ticks)
        if kind == "scan":
            return {"success": True,
                    "reading": self.sense(str(task.get("request", "scan")))}
        if kind == "image":
            ok = self.machine.command_image(str(task["target"]),
                                            tick=self.tick)
            return {"success": ok}
        if kind == "produce":
            return self._task_produce(task, max_ticks)
        return {"success": False,
                "reason": f"unknown task type {kind} for "
                          f"{self.machine.KIND}"}

    def _position_2d(self):
        pos = self.adapter.position(self.machine)
        if pos is None or len(pos) < 2:
            raise ValueError("platform has no 2D position")
        return float(pos[0]), float(pos[1])

    def _task_navigate(self, dest, max_ticks):
        for _ in range(max_ticks):
            x, y = self._position_2d()
            dist = math.hypot(dest[0] - x, dest[1] - y)
            if dist <= 0.6:
                self.move({})
                return {"success": True, "final_dist": round(dist, 4),
                        "ticks_used": self.tick}
            speed = min(1.0, max(0.3, dist * 0.3))
            bearing = math.atan2(dest[1] - y, dest[0] - x)
            heading_deg = math.degrees(bearing)
            # Heading-controlled platforms need a rate command too.
            angular = 0.0
            if hasattr(self.machine, "heading"):
                err = (bearing - self.machine.heading + math.pi) \
                    % (2 * math.pi) - math.pi
                angular = max(-1.0, min(1.0, err * 2.0))
            accepted = self.move({
                "linear": speed, "speed": speed,
                "vx": math.cos(bearing) * speed,
                "vy": math.sin(bearing) * speed,
                "vz": 0.0,
                "heading_deg": heading_deg,
                "angular": angular,
            })
            if not accepted:
                return {"success": False, "reason": "move refused"}
            self._step_world()
        return {"success": False, "reason": "tick budget exhausted"}

    def _task_produce(self, task, max_ticks):
        quantity = int(task.get("quantity", 10))
        machine = self.machine
        if isinstance(machine, _m.CNCMachine):
            start = machine.parts_completed
            machine.command_door(False, tick=self.tick)
            machine.command_spindle(True, int(task.get("rpm", 9000)),
                                    tick=self.tick,
                                    feed_rate=float(task.get("feed_rate", 1)))
            for _ in range(max_ticks):
                self._step_world()
                if machine.parts_completed - start >= quantity:
                    machine.command_spindle(False, 0, tick=self.tick)
                    machine.command_door(True, tick=self.tick)
                    return {"success": True,
                            "produced": round(machine.parts_completed
                                              - start, 2)}
                if machine.needs_tool_service:
                    machine.command_spindle(False, 0, tick=self.tick)
                    machine.command_tool_change(tick=self.tick)
                    machine.command_spindle(True, int(task.get("rpm", 9000)),
                                            tick=self.tick,
                                            feed_rate=float(task.get("feed_rate", 1)))
            return {"success": False, "reason": "quantity not met"}
        if isinstance(machine, _m.ConveyorLine):
            start = machine.items_produced
            for _ in range(max_ticks):
                self._step_world()
                if machine.jammed:
                    machine.command_clear_jam(tick=self.tick)
                else:
                    machine.command_speed(float(task.get("speed", 1.8)),
                                          tick=self.tick)
                if machine.items_produced - start >= quantity:
                    machine.command_speed(0.0, tick=self.tick)
                    return {"success": True,
                            "produced": round(machine.items_produced
                                              - start, 2)}
            return {"success": False, "reason": "quantity not met"}
        return {"success": False, "reason": "machine cannot produce"}


# --------------------------------------------------------------------- #
# Shared world model                                                     #
# --------------------------------------------------------------------- #
@dataclass
class EntitySnapshot:
    entity_id: str
    kind: str
    domain: str
    tick: int
    state: Dict[str, Any]


class WorldModel:
    """Shared world representation: entities, comms, environment.

    Agents ask the world model for observations instead of reaching into
    other agents -- the coordination substrate for multi-domain missions.
    """

    def __init__(self) -> None:
        self.entities: Dict[str, EntitySnapshot] = {}
        self.communications: List[Dict[str, Any]] = []
        self.environment: Dict[str, Any] = {"tick": 0}

    def register(self, controller: PlatformController) -> EntitySnapshot:
        return self.record_position(controller)

    def record_position(self, controller) -> EntitySnapshot:
        snap = EntitySnapshot(
            entity_id=controller.platform_id,
            kind=controller.machine.KIND,
            domain=controller.domain,
            tick=self.environment["tick"],
            state=controller.get_state(),
        )
        self.entities[snap.entity_id] = snap
        return snap

    def record_communication(self, sender_id: str,
                             message: Dict[str, Any]) -> None:
        self.communications.append({
            "tick": self.environment["tick"],
            "sender": sender_id,
            "message": message,
        })

    def observe(self, entity_id: str) -> Optional[EntitySnapshot]:
        return self.entities.get(entity_id)

    def observations_by_domain(self, domain: str) -> List[EntitySnapshot]:
        return [e for e in self.entities.values() if e.domain == domain]

    def advance_tick(self) -> int:
        self.environment["tick"] += 1
        return self.environment["tick"]


# --------------------------------------------------------------------- #
# Mission system                                                         #
# --------------------------------------------------------------------- #
@dataclass
class Mission:
    mission_id: str
    objective: str
    required_capabilities: frozenset
    priority: int = 1
    assigned: List[str] = field(default_factory=list)
    status: str = "PLANNED"


class MissionPlanner:
    """Capability-based assignment: WHO can do this mission? (not WHAT is it)"""

    def __init__(self, controllers: Dict[str, PlatformController],
                 world: WorldModel) -> None:
        self.controllers = controllers
        self.world = world

    def find_capable(self, required) -> List[str]:
        reqs = {Capability(c) for c in required}
        return [
            cid for cid, ctrl in sorted(self.controllers.items())
            if all(ctrl.supports(c) for c in reqs)
        ]

    def assign(self, mission: Mission) -> Mission:
        mission.assigned = self.find_capable(mission.required_capabilities)
        mission.status = "ASSIGNED" if mission.assigned else "INFEASIBLE"
        return mission

    def complete(self, mission: Mission) -> Mission:
        mission.status = "COMPLETE"
        return mission


# --------------------------------------------------------------------- #
# Simulation lab assembly                                                #
# --------------------------------------------------------------------- #
class SimulationLab:
    """Multi-domain simulated fleet + universal control layer.

    Air (delivery drone), land (mobile robot, freight railcar),
    sea (research vessel), space (imaging satellite), cyber (network
    sensor) -- every platform behind the same PlatformController
    interface, every actuation interlocked and simulated.
    """

    def __init__(self, seed: int = 0) -> None:
        self.world = WorldModel()
        self.machine_controller = _m.MachineController(seed=seed)
        lock = self.machine_controller.interlock
        drone = _m.LogisticsDrone("uav-1", lock)
        robot = _m.MobileRobot("ugv-1", lock)
        railcar = _m.FreightRailcar("rail-1", lock)
        vessel = _m.ResearchVessel("usv-1", lock)
        satellite = _m.EarthObservationSatellite("sat-1", lock)
        sensor = _m.NetworkSensor("cyber-1", lock, seed=seed)
        cnc = _m.CNCMachine("cnc-1", lock)
        conveyor = _m.ConveyorLine("conv-1", lock)

        for machine in (drone, robot, railcar, vessel, satellite, sensor,
                        cnc, conveyor):
            self.machine_controller.register(machine)

        self.machines: List[Any] = [drone, robot, railcar, vessel,
                                    satellite, sensor, cnc, conveyor]
        self.controllers: Dict[str, PlatformController] = {}
        for machine in self.machines:
            ctrl = PlatformController(
                machine, world_model=self.world,
                stepper=self.machine_controller.step_all)
            self.controllers[ctrl.platform_id] = ctrl
            self.world.register(ctrl)
        self.planner = MissionPlanner(self.controllers, self.world)

    def controller(self, platform_id: str) -> PlatformController:
        return self.controllers[platform_id]

    def domains_covered(self) -> List[str]:
        return sorted({c.domain for c in self.controllers.values()})

    def hard_violations(self) -> int:
        return sum(m.lock.hard_violations for m in self.machines)

    def run_mission(self, mission: Mission,
                    plan: Dict[str, Dict[str, Any]],
                    max_ticks: int = 400) -> Dict[str, Any]:
        """Assign by capability, then execute each assigned platform's plan."""
        self.planner.assign(mission)
        results: Dict[str, Any] = {}
        if mission.status == "ASSIGNED":
            for platform_id, task in plan.items():
                if platform_id in mission.assigned:
                    results[platform_id] = self.controllers[platform_id] \
                        .execute_task(task, max_ticks=max_ticks)
        complete = bool(results) and all(
            r.get("success") for r in results.values())
        if complete:
            mission.status = "COMPLETE"
        return {
            "mission": {
                "mission_id": mission.mission_id,
                "objective": mission.objective,
                "status": mission.status,
                "assigned": list(mission.assigned),
                "required_capabilities": sorted(
                    c.value if hasattr(c, "value") else str(c)
                    for c in mission.required_capabilities),
            },
            "results": results,
            "all_succeeded": complete,
            "hard_violations": self.hard_violations(),
        }
