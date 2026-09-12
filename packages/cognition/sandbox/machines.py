# Copyright (c) Ultrone Contributors. All rights reserved.
"""Simulated machine-control capability: actuators, interlocks, policies.

A general (civilian, simulation-only) machine zoo -- robotic arm,
differential-drive robot, conveyor line, process tank, climate unit --
behind a uniform command/telemetry interface with **safety interlocks as
first-class citizens**: every out-of-envelope command is rejected and
recorded, an emergency stop halts everything, and hard violations
(tank overflow, geofence escape) are counted and gated on.

This is the measurable form of "the agent can control many kinds of
machines safely". Nothing here touches real hardware: every machine is a
deterministic simulation stepped inside the sandbox.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple


# --------------------------------------------------------------------- #
# Safety interlock                                                       #
# --------------------------------------------------------------------- #
@dataclass(frozen=True)
class InterlockEvent:
    tick: int
    machine_id: str
    command: str
    reason: str


class SafetyInterlock:
    """Records rejected commands; owns the emergency-stop latch."""

    def __init__(self) -> None:
        self.events: List[InterlockEvent] = []
        self.e_stopped = False
        self.hard_violations = 0          # envelope breaches, not refusals

    def reject(self, tick: int, machine_id: str, command: str, reason: str) -> bool:
        self.events.append(InterlockEvent(tick, machine_id, command, reason))
        return False

    def violation(self, machine_id: str, reason: str) -> None:
        self.hard_violations += 1
        self.events.append(
            InterlockEvent(-1, machine_id, "ENVELOPE_BREACH", reason))

    def trigger_estop(self) -> None:
        self.e_stopped = True

    def clear_estop(self) -> None:
        self.e_stopped = False


# --------------------------------------------------------------------- #
# Machines                                                               #
# --------------------------------------------------------------------- #
class RoboticArm:
    KIND = "arm"
    JOINT_LIMITS = {"base": (-180.0, 180.0), "shoulder": (-90.0, 90.0),
                    "elbow": (0.0, 150.0)}
    MAX_JOINT_SPEED = 5.0              # degrees per tick

    def __init__(self, machine_id: str, lock: SafetyInterlock) -> None:
        self.machine_id = machine_id
        self.lock = lock
        self.joints = {j: 0.0 for j in self.JOINT_LIMITS}
        self.gripper = "open"
        self._target: Optional[Dict[str, float]] = None

    def command_move(self, targets: Dict[str, float], tick: int) -> bool:
        if self.lock.e_stopped:
            return self.lock.reject(tick, self.machine_id, "move", "e-stop")
        for joint, angle in targets.items():
            lo, hi = self.JOINT_LIMITS[joint]
            if not lo <= angle <= hi:
                return self.lock.reject(
                    tick, self.machine_id, "move",
                    f"joint '{joint}' angle {angle} outside [{lo}, {hi}]")
        self._target = dict(targets)
        return True

    def command_gripper(self, state: str, tick: int) -> bool:
        if state not in ("open", "closed"):
            return self.lock.reject(tick, self.machine_id, "gripper",
                                    f"unknown gripper state {state}")
        self.gripper = state
        return True

    def step(self, tick: int) -> None:
        if self._target is None or self.lock.e_stopped:
            return
        for joint, target in self._target.items():
            err = target - self.joints[joint]
            step = max(-self.MAX_JOINT_SPEED, min(self.MAX_JOINT_SPEED, err))
            self.joints[joint] += step

    def telemetry(self) -> Dict[str, object]:
        return {"kind": self.KIND, "joints": dict(self.joints),
                "gripper": self.gripper}


class MobileRobot:
    KIND = "robot"
    ARENA = 20.0
    MAX_LINEAR = 1.0

    def __init__(self, machine_id: str, lock: SafetyInterlock) -> None:
        self.machine_id = machine_id
        self.lock = lock
        self.x = self.y = 1.0
        self.heading = 0.0
        self.battery = 1.0
        self._linear = 0.0
        self._angular = 0.0

    def command_velocity(self, linear: float, angular: float,
                         tick: int) -> bool:
        if self.lock.e_stopped:
            return self.lock.reject(tick, self.machine_id, "velocity", "e-stop")
        if self.battery <= 0.0:
            return self.lock.reject(tick, self.machine_id, "velocity",
                                    "battery depleted")
        if abs(linear) > self.MAX_LINEAR:
            return self.lock.reject(tick, self.machine_id, "velocity",
                                    f"|linear| {linear} exceeds "
                                    f"{self.MAX_LINEAR}")
        self._linear, self._angular = linear, angular
        return True

    def step(self, tick: int) -> None:
        if self.lock.e_stopped:
            return
        self.heading += self._angular
        self.x += math.cos(self.heading) * self._linear
        self.y += math.sin(self.heading) * self._linear
        before = (self.x, self.y)
        self.x = min(max(0.0, self.x), self.ARENA)
        self.y = min(max(0.0, self.y), self.ARENA)
        if before != (self.x, self.y):
            self.lock.violation(self.machine_id, "geofence clamp engaged")
        self.battery = max(0.0, self.battery - abs(self._linear) * 0.004)

    def telemetry(self) -> Dict[str, object]:
        return {"kind": self.KIND, "x": round(self.x, 4),
                "y": round(self.y, 4), "heading": round(self.heading, 4),
                "battery": round(self.battery, 4)}


class ConveyorLine:
    KIND = "conveyor"
    MAX_SPEED = 2.0
    JAM_PROBABILITY = 0.02

    def __init__(self, machine_id: str, lock: SafetyInterlock) -> None:
        self.machine_id = machine_id
        self.lock = lock
        self.speed = 0.0
        self.items_produced = 0.0
        self.jammed = False

    def command_speed(self, speed: float, tick: int) -> bool:
        if self.lock.e_stopped and speed > 0:
            return self.lock.reject(tick, self.machine_id, "speed", "e-stop")
        if not 0.0 <= speed <= self.MAX_SPEED:
            return self.lock.reject(tick, self.machine_id, "speed",
                                    f"speed {speed} outside [0, "
                                    f"{self.MAX_SPEED}]")
        self.speed = speed
        return True

    def command_clear_jam(self, tick: int) -> bool:
        self.jammed = False
        return True

    def step(self, tick: int, rng: random.Random) -> None:
        if not self.jammed and self.rng_draw_needed(rng):
            self.jammed = True
            self.lock.events.append(InterlockEvent(
                tick, self.machine_id, "JAM", "random jam"))
        if self.jammed:
            self.speed = 0.0
        else:
            self.items_produced += self.speed

    def rng_draw_needed(self, rng: random.Random) -> bool:
        return self.speed > 0 and rng.random() < self.JAM_PROBABILITY

    def telemetry(self) -> Dict[str, object]:
        return {"kind": self.KIND, "speed": round(self.speed, 3),
                "jammed": self.jammed,
                "items_produced": round(self.items_produced, 2)}


class ProcessTank:
    KIND = "tank"
    CAPACITY = 100.0
    MAX_INFLOW = 10.0
    DEMAND = 4.0                     # constant outflow demand

    def __init__(self, machine_id: str, lock: SafetyInterlock) -> None:
        self.machine_id = machine_id
        self.lock = lock
        self.level = 50.0
        self.valve_opening = 0.0     # percent 0..100

    def command_valve(self, opening: float, tick: int) -> bool:
        if not 0.0 <= opening <= 100.0:
            return self.lock.reject(tick, self.machine_id, "valve",
                                    f"opening {opening} outside [0, 100]")
        self.valve_opening = opening
        return True

    def step(self, tick: int) -> None:
        inflow = self.valve_opening / 100.0 * self.MAX_INFLOW
        self.level += inflow - self.DEMAND
        if self.level > self.CAPACITY:
            self.lock.violation(self.machine_id, "tank overflow")
            self.level = self.CAPACITY
        if self.level < 0.0:
            self.level = 0.0

    def telemetry(self) -> Dict[str, object]:
        return {"kind": self.KIND, "level": round(self.level, 3),
                "valve_opening": round(self.valve_opening, 2)}


class ClimateUnit:
    KIND = "hvac"
    AMBIENT = 22.0

    def __init__(self, machine_id: str, lock: SafetyInterlock) -> None:
        self.machine_id = machine_id
        self.lock = lock
        self.temperature = 18.0
        self.mode = "off"

    def command_mode(self, mode: str, tick: int) -> bool:
        if mode not in ("off", "heat", "cool"):
            return self.lock.reject(tick, self.machine_id, "mode",
                                    f"unknown mode {mode}")
        self.mode = mode
        return True

    def step(self, tick: int) -> None:
        if self.mode == "heat":
            self.temperature += 0.5
        elif self.mode == "cool":
            self.temperature -= 0.5
        else:
            self.temperature += (self.AMBIENT - self.temperature) * 0.05

    def telemetry(self) -> Dict[str, object]:
        return {"kind": self.KIND, "temperature": round(self.temperature, 3),
                "mode": self.mode}


# --------------------------------------------------------------------- #
# Controller                                                             #
# --------------------------------------------------------------------- #
class MachineController:
    """Uniform registry + dispatch + stepping for heterogeneous machines."""

    def __init__(self, seed: int = 0) -> None:
        self.interlock = SafetyInterlock()
        self.machines: Dict[str, object] = {}
        self.rng = random.Random(seed)

    def register(self, machine) -> None:
        self.machines[machine.machine_id] = machine

    def step_all(self, tick: int) -> None:
        for machine in self.machines.values():
            if isinstance(machine, ConveyorLine):
                machine.step(tick, self.rng)
            else:
                machine.step(tick)

    def estop_all(self) -> None:
        self.interlock.trigger_estop()

    def resume_all(self) -> None:
        self.interlock.clear_estop()

    def telemetry(self) -> Dict[str, Dict[str, object]]:
        return {mid: m.telemetry() for mid, m in sorted(self.machines.items())}

    @property
    def hard_violations(self) -> int:
        return self.interlock.hard_violations

    # -- universal capability discovery --------------------------------- #
    def capabilities_of(self, machine_or_id: object) -> List[str]:
        """Actions a machine exposes, derived from its ``command_*`` API.

        This is what makes "control ALL kinds of machines" structural: an
        agent asks the controller what any machine accepts at runtime,
        with no hand-coded per-kind knowledge -- machines added later are
        automatically controllable through the same interface.
        """
        machine = (self.machines.get(machine_or_id)
                   if isinstance(machine_or_id, str) else machine_or_id)
        if machine is None:
            return []
        return sorted(
            name[len("command_"):] for name in dir(machine)
            if name.startswith("command_") and callable(getattr(machine, name))
        )

    def describe_machines(self) -> Dict[str, Dict[str, object]]:
        """Capability sheet for every attached machine."""
        return {
            mid: {"kind": getattr(m, "KIND", "?"),
                  "capabilities": self.capabilities_of(m)}
            for mid, m in sorted(self.machines.items())
        }

    # -- universal command dispatch -------------------------------------- #
    def dispatch(self, machine_id: str, action: str, tick: int = 0,
                 **params: object) -> bool:
        """Send ANY command to ANY registered machine by name.

        The machine's own SafetyInterlock stays the single gatekeeper:
        out-of-envelope payloads are refused and recorded exactly as when
        calling the typed methods directly.
        """
        machine = self.machines.get(machine_id)
        if machine is None:
            return self.interlock.reject(tick, machine_id, action,
                                         f"unknown machine '{machine_id}'")
        method = getattr(machine, f"command_{action}", None)
        if not callable(method):
            return self.interlock.reject(
                tick, machine_id, action,
                f"machine '{getattr(machine, 'KIND', '?')}' has no command "
                f"'{action}'")
        try:
            return bool(method(tick=tick, **params))
        except TypeError as exc:
            return self.interlock.reject(
                tick, machine_id, action,
                f"bad parameters for '{action}': {exc}")


def build_factory_floor(seed: int = 0) -> MachineController:
    ctrl = MachineController(seed=seed)
    lock = ctrl.interlock
    ctrl.register(RoboticArm("arm-1", lock))
    ctrl.register(MobileRobot("robot-1", lock))
    ctrl.register(ConveyorLine("conveyor-1", lock))
    ctrl.register(ProcessTank("tank-1", lock))
    ctrl.register(ClimateUnit("hvac-1", lock))
    return ctrl


# --------------------------------------------------------------------- #
# Control policies                                                       #
# --------------------------------------------------------------------- #
def proportional(current: float, target: float, gain: float = 0.3,
                 max_step: float = 5.0) -> float:
    err = target - current
    return max(-max_step, min(max_step, err * gain))


def run_setpoint_task(
    controller: MachineController, machine_id: str, tick_limit: int,
    read: Callable[[], float], actuate: Callable[[float, int], bool],
    target: float, tolerance: float, gain: float = 0.3,
) -> Dict[str, object]:
    """Generic closed-loop setpoint task; returns performance metrics."""
    settled_tick: Optional[int] = None
    max_overshoot = 0.0
    energy = 0.0
    for tick in range(1, tick_limit + 1):
        current = read()
        output = proportional(current, target, gain=gain)
        if actuate(output, tick):
            energy += abs(output)
        controller.step_all(tick)
        current = read()
        max_overshoot = max(max_overshoot, abs(current - target))
        if settled_tick is None and abs(current - target) <= tolerance:
            settled_tick = tick
    return {
        "machine_id": machine_id,
        "settled_tick": settled_tick,
        "settled": settled_tick is not None,
        "max_overshoot": round(max_overshoot, 4),
        "energy_proxy": round(energy, 3),
    }


def _task_arm_positioning(arm: RoboticArm, tick_limit: int) -> Dict[str, object]:
    targets = {"base": 120.0, "shoulder": -45.0, "elbow": 90.0}
    arm.command_move(targets, 0)
    settle_t = None
    for t in range(1, tick_limit + 1):
        arm.step(t)
        if settle_t is None and all(
            abs(arm.joints[j] - v) <= 0.6 for j, v in targets.items()
        ):
            settle_t = t
    return {"settled_tick": settle_t, "settled": settle_t is not None}


def _task_robot_navigation(robot: MobileRobot, ctrl: MachineController,
                           tick_limit: int) -> Dict[str, object]:
    tx, ty = 15.0, 15.0
    robot_settle = None
    battery_before = robot.battery
    for t in range(1, tick_limit + 1):
        dx, dy = tx - robot.x, ty - robot.y
        turn = (math.atan2(dy, dx) - robot.heading + math.pi) \
            % (2 * math.pi) - math.pi
        dist = math.hypot(dx, dy)
        lin = min(robot.MAX_LINEAR, max(0.2, dist * 0.4)) if dist > 0.3 else 0.0
        robot.command_velocity(lin, max(-1.0, min(1.0, turn * 2.0)), t)
        ctrl.step_all(t)
        if robot_settle is None and math.hypot(tx - robot.x, ty - robot.y) <= 0.5:
            robot.command_velocity(0.0, 0.0, t)   # zero the actuator: never
            robot_settle = t                      # leave a latched velocity
            break
    return {
        "settled_tick": robot_settle, "settled": robot_settle is not None,
        "battery_used": round(battery_before - robot.battery, 4),
    }


def _task_conveyor_throughput(conveyor: ConveyorLine,
                              ctrl: MachineController,
                              tick_limit: int) -> Dict[str, object]:
    conveyor.command_speed(1.8, 0)
    jam_recoveries = 0
    for t in range(1, tick_limit + 1):
        ctrl.step_all(t)
        if conveyor.jammed:
            conveyor.command_clear_jam(t)
            jam_recoveries += 1
        if conveyor.items_produced >= 25:
            break
    return {
        "items": round(conveyor.items_produced, 2),
        "jam_recoveries": jam_recoveries,
        "settled": conveyor.items_produced >= 25,
    }


def _task_tank_level_hold(tank: ProcessTank, ctrl: MachineController,
                          tick_limit: int) -> Dict[str, object]:
    # Feedforward (valve ~40% balances the constant demand) + proportional
    # feedback trim -- the textbook structure for level control.
    settle = None
    held = 0
    for t in range(1, tick_limit + 1):
        valve = max(0.0, min(100.0, 40.0 + (60.0 - tank.level) * 4.0))
        tank.command_valve(valve, t)
        ctrl.step_all(t)
        if abs(tank.level - 60.0) <= 2.0:
            held += 1
            if settle is None:
                settle = t
        else:
            held = 0
        if held >= 10:
            break
    return {"settled_tick": settle, "held_ticks": held, "settled": held >= 10}


def run_machine_control_suite(seed: int = 0, tick_limit: int = 120) -> Dict[str, object]:
    """One closed-loop task per machine kind + interlock safety checks."""
    ctrl = build_factory_floor(seed=seed)
    arm = ctrl.machines["arm-1"]
    robot = ctrl.machines["robot-1"]
    conveyor = ctrl.machines["conveyor-1"]
    tank = ctrl.machines["tank-1"]
    hvac = ctrl.machines["hvac-1"]

    tasks: Dict[str, Dict[str, object]] = {
        "arm_positioning": _task_arm_positioning(arm, tick_limit),
        "robot_navigation": _task_robot_navigation(robot, ctrl, tick_limit),
        "conveyor_throughput":
            _task_conveyor_throughput(conveyor, ctrl, tick_limit),
        "tank_level_hold": _task_tank_level_hold(tank, ctrl, tick_limit),
        "hvac_setpoint": run_setpoint_task(
            ctrl, "hvac-1", tick_limit=80,
            read=lambda: hvac.temperature,
            actuate=lambda out, t: hvac.command_mode(
                "heat" if out > 0.05 else "cool" if out < -0.05 else "off", t),
            target=21.0, tolerance=0.75, gain=0.12,
        ),
    }

    # Interlock negative controls (must all be refused).
    rejected = [
        not arm.command_move({"base": 400.0}, tick_limit + 1),
        not robot.command_velocity(9.9, 0.0, tick_limit + 1),
        not tank.command_valve(150.0, tick_limit + 1),
        not hvac.command_mode("explode", tick_limit + 1),
    ]

    all_settled = all(t["settled"] for t in tasks.values())
    report = {
        "tasks": tasks,
        "interlock_rejections_recorded": len(ctrl.interlock.events),
        "negative_controls_all_rejected": all(rejected),
        "hard_violations": ctrl.hard_violations,
        "zero_hard_violations": ctrl.hard_violations == 0,
        "all_settled": all_settled,
        "machines_controlled": len(ctrl.machines),
    }
    payload = json.dumps(
        {k: v for k, v in report.items() if k != "fingerprint"},
        sort_keys=True, separators=(",", ":"))
    report["fingerprint"] = hashlib.sha256(payload.encode()).hexdigest()[:16]
    return report


# --------------------------------------------------------------------- #
# Machine zoo extensions                                                 #
# --------------------------------------------------------------------- #
class OverheadCrane:
    """Bridge/trolley/hoist crane with pendulum-sway dynamics.

    Sway grows with velocity changes under load and decays when the crane
    holds still; the interlock refuses motion while sway exceeds the safe
    limit -- classic real crane discipline, enforced structurally.
    """

    KIND = "crane"
    BRIDGE_LIMIT = 20.0
    TROLLEY_LIMIT = 10.0
    HOIST_RANGE = (0.5, 8.0)          # hook height above floor
    MAX_HOOK_LOAD_KG = 500.0
    SWAY_LIMIT = 2.0                  # degrees of allowed sway
    MAX_AXIS_SPEED = 1.0

    def __init__(self, machine_id: str, lock: SafetyInterlock) -> None:
        self.machine_id = machine_id
        self.lock = lock
        self.bridge = 1.0
        self.trolley = 1.0
        self.hoist_height = 8.0
        self.hook_load_kg = 0.0       # 0 = empty hook
        self.sway_deg = 0.0
        self._v_bridge = 0.0
        self._v_trolley = 0.0

    def command_move(self, v_bridge: float, v_trolley: float,
                     tick: int) -> bool:
        # Stopping is ALWAYS permitted -- even under e-stop or heavy sway.
        if v_bridge == 0.0 and v_trolley == 0.0:
            self._v_bridge = 0.0
            self._v_trolley = 0.0
            return True
        if self.lock.e_stopped:
            return self.lock.reject(tick, self.machine_id, "move", "e-stop")
        if abs(self.sway_deg) > self.SWAY_LIMIT and self.hook_load_kg > 0:
            return self.lock.reject(
                tick, self.machine_id, "move",
                f"sway {self.sway_deg:.2f} deg exceeds {self.SWAY_LIMIT} "
                f"-- wait for damping")
        for name, v in (("bridge", v_bridge), ("trolley", v_trolley)):
            if abs(v) > self.MAX_AXIS_SPEED:
                return self.lock.reject(tick, self.machine_id, "move",
                                        f"{name} speed {v} exceeds cap")
        prev_vb, prev_vt = self._v_bridge, self._v_trolley
        self._v_bridge, self._v_trolley = v_bridge, v_trolley
        # Sway responds to acceleration, worse when carrying a load.
        accel = abs(v_bridge - prev_vb) + abs(v_trolley - prev_vt)
        load_factor = 2.0 if self.hook_load_kg > 0 else 1.0
        self.sway_deg += accel * 1.5 * load_factor
        return True

    def command_hoist(self, delta: float, tick: int) -> bool:
        if self.lock.e_stopped:
            return self.lock.reject(tick, self.machine_id, "hoist", "e-stop")
        new_height = self.hoist_height + delta
        lo, hi = self.HOIST_RANGE
        if not lo <= new_height <= hi:
            return self.lock.reject(tick, self.machine_id, "hoist",
                                    f"height {new_height:.2f} outside "
                                    f"[{lo}, {hi}]")
        self.hoist_height = new_height
        return True

    def command_attach_load(self, kg: float, tick: int) -> bool:
        if self.hook_load_kg > 0:
            return self.lock.reject(tick, self.machine_id, "attach",
                                    "hook already loaded")
        if kg > self.MAX_HOOK_LOAD_KG:
            return self.lock.reject(tick, self.machine_id, "attach",
                                    f"load {kg} kg exceeds rating "
                                    f"{self.MAX_HOOK_LOAD_KG}")
        self.hook_load_kg = kg
        return True

    def command_release_load(self, tick: int) -> bool:
        if self.hook_load_kg <= 0:
            return self.lock.reject(tick, self.machine_id, "release",
                                    "no load on hook")
        if self.hoist_height > 1.0:
            return self.lock.reject(tick, self.machine_id, "release",
                                    "load too high to release safely")
        self.hook_load_kg = 0.0
        return True

    def step(self, tick: int) -> None:
        self.bridge = min(max(0.0, self.bridge + self._v_bridge),
                          self.BRIDGE_LIMIT)
        self.trolley = min(max(0.0, self.trolley + self._v_trolley),
                           self.TROLLEY_LIMIT)
        self.sway_deg *= 0.85                 # deterministic damping
        if abs(self.sway_deg) < 0.05:
            self.sway_deg = 0.0

    def telemetry(self) -> Dict[str, object]:
        return {"kind": self.KIND, "bridge": round(self.bridge, 3),
                "trolley": round(self.trolley, 3),
                "hoist_height": round(self.hoist_height, 3),
                "sway_deg": round(self.sway_deg, 3),
                "hook_load_kg": self.hook_load_kg}


class CNCMachine:
    """Machining center with a door interlock and tool-wear lifecycle."""

    KIND = "cnc"
    MAX_RPM = 12000
    WEAR_PER_PART = 8.0
    WEAR_SERVICE_LIMIT = 80.0

    def __init__(self, machine_id: str, lock: SafetyInterlock) -> None:
        self.machine_id = machine_id
        self.lock = lock
        self.door_open = True               # safe default
        self.spindle_on = False
        self.spindle_rpm = 0
        self.feed_rate = 0.0
        self.parts_completed = 0
        self.tool_wear = 0.0

    def command_door(self, open_: bool, tick: int) -> bool:
        if self.spindle_on and open_:
            return self.lock.reject(tick, self.machine_id, "door",
                                    "cannot open door while spindle runs")
        self.door_open = bool(open_)
        return True

    def command_spindle(self, on: bool, rpm: int, tick: int,
                        feed_rate: float = 1.0) -> bool:
        if self.lock.e_stopped and on:
            return self.lock.reject(tick, self.machine_id, "spindle", "e-stop")
        if on and self.door_open:
            return self.lock.reject(tick, self.machine_id, "spindle",
                                    "door must be closed before spindle start")
        if on and self.tool_wear >= self.WEAR_SERVICE_LIMIT:
            return self.lock.reject(tick, self.machine_id, "spindle",
                                    "tool worn -- service required")
        if not 0 <= rpm <= self.MAX_RPM:
            return self.lock.reject(tick, self.machine_id, "spindle",
                                    f"rpm {rpm} outside [0, {self.MAX_RPM}]")
        self.spindle_on = on
        self.spindle_rpm = int(rpm) if on else 0
        self.feed_rate = feed_rate if on else 0.0
        return True

    def command_tool_change(self, tick: int) -> bool:
        if self.spindle_on:
            return self.lock.reject(tick, self.machine_id, "tool_change",
                                    "stop the spindle first")
        self.tool_wear = 0.0
        return True

    def step(self, tick: int) -> None:
        if self.spindle_on and not self.door_open:
            self.parts_completed += self.feed_rate * 0.1
            self.tool_wear += self.WEAR_PER_PART * self.feed_rate * 0.1

    @property
    def needs_tool_service(self) -> bool:
        return self.tool_wear >= self.WEAR_SERVICE_LIMIT

    def telemetry(self) -> Dict[str, object]:
        return {"kind": self.KIND, "spindle_on": self.spindle_on,
                "spindle_rpm": self.spindle_rpm,
                "parts_completed": round(self.parts_completed, 2),
                "tool_wear": round(self.tool_wear, 2),
                "door_open": self.door_open}


class LogisticsDrone:
    """Battery-powered delivery quadrotor with no-fly-zone governance."""

    KIND = "delivery_drone"
    ALT_CEILING = 40.0
    BATTERY_RESERVE_PCT = 15.0
    CRUISE_SPEED = 2.0

    def __init__(self, machine_id: str, lock: SafetyInterlock,
                 home: Tuple[float, float] = (2.0, 2.0)) -> None:
        self.machine_id = machine_id
        self.lock = lock
        self.x, self.y = home
        self.z = 0.0
        self.battery_pct = 100.0
        self.charging = False
        self.payload_kg = 0.0
        self.nofly_zones: List[Tuple[float, float, float]] = []  # (cx,cy,r)

    def declare_nofly_zone(self, cx: float, cy: float, radius: float) -> None:
        self.nofly_zones.append((cx, cy, radius))

    def _in_nofly(self, x: float, y: float) -> bool:
        return any((x - cx) ** 2 + (y - cy) ** 2 <= r ** 2
                   for cx, cy, r in self.nofly_zones)

    def command_velocity(self, vx: float, vy: float, vz: float,
                         tick: int) -> bool:
        if self.lock.e_stopped:
            return self.lock.reject(tick, self.machine_id, "velocity", "e-stop")
        if math.hypot(vx, vy) > self.CRUISE_SPEED:
            return self.lock.reject(tick, self.machine_id, "velocity",
                                    "cruise speed exceeded")
        nx, ny = self.x + vx, self.y + vy
        if self._in_nofly(nx, ny):
            return self.lock.reject(tick, self.machine_id, "velocity",
                                    "path enters a no-fly zone")
        reserve = self.BATTERY_RESERVE_PCT
        new_z = min(self.ALT_CEILING, max(0.0, self.z + vz))
        if new_z > 0 and self.battery_pct <= reserve and self.z > 0:
            return self.lock.reject(tick, self.machine_id, "velocity",
                                    "battery at reserve: land immediately")
        self.x, self.y, self.z = nx, ny, new_z
        if self.z > 0:
            self.battery_pct = max(
                0.0, self.battery_pct - 0.4 - self.payload_kg * 0.1)
        return True

    def command_recharge(self, tick: int) -> bool:
        if self.z > 0:
            return self.lock.reject(tick, self.machine_id, "recharge",
                                    "must land before recharging")
        self.charging = True
        return True

    def command_pick_payload(self, kg: float, tick: int) -> bool:
        if self.z > 0:
            return self.lock.reject(tick, self.machine_id, "payload",
                                    "land before handling payload")
        self.payload_kg = kg
        return True

    def command_drop_payload(self, tick: int) -> bool:
        if self.z > 0:
            return self.lock.reject(tick, self.machine_id, "payload",
                                    "cannot drop from the air")
        self.payload_kg = 0.0
        return True

    def step(self, tick: int) -> None:
        if self.charging:
            self.battery_pct = min(100.0, self.battery_pct + 2.0)
            if self.battery_pct >= 100.0:
                self.charging = False

    def telemetry(self) -> Dict[str, object]:
        return {"kind": self.KIND, "x": round(self.x, 3),
                "y": round(self.y, 3), "z": round(self.z, 3),
                "battery_pct": round(self.battery_pct, 2),
                "payload_kg": self.payload_kg}


class PowerMicrogrid:
    """Solar + battery + backup-generator microgrid dispatch.

    Solar output follows a deterministic daylight curve; the interlock
    enforces battery depth-of-discharge (a brownout is a hard violation)
    and blocks generator starts without fuel.
    """

    KIND = "microgrid"
    CAPACITY_KWH = 100.0
    BATTERY_FLOOR_PCT = 20.0
    GENERATOR_OUTPUT_KW = 12.0
    MAX_DEMAND_KW = 30.0

    def __init__(self, machine_id: str, lock: SafetyInterlock,
                 fuel_pct: float = 100.0) -> None:
        self.machine_id = machine_id
        self.lock = lock
        self.battery_pct = 60.0
        self.demand_kw = 10.0
        self.generator_on = False
        self.fuel_pct = fuel_pct
        self.brownouts = 0
        self._in_brownout = False
        self.last_tick = 0

    @staticmethod
    def solar_kw(tick: int) -> float:
        """Deterministic daylight curve peaking mid-day."""
        phase = (tick % 24) / 24.0
        return round(max(0.0, 18.0 * math.sin(math.pi * phase)), 2)

    def command_load(self, demand_kw: float, tick: int) -> bool:
        if not 0.0 <= demand_kw <= self.MAX_DEMAND_KW:
            return self.lock.reject(tick, self.machine_id, "load",
                                    f"demand {demand_kw} outside "
                                    f"[0, {self.MAX_DEMAND_KW}]")
        self.demand_kw = demand_kw
        return True

    def command_generator(self, on: bool, tick: int) -> bool:
        if on and self.fuel_pct <= 0.0:
            return self.lock.reject(tick, self.machine_id, "generator",
                                    "no fuel remaining")
        self.generator_on = bool(on)
        return True

    def step(self, tick: int) -> None:
        self.last_tick = tick
        supply = self.solar_kw(tick)
        if self.generator_on:
            supply += self.GENERATOR_OUTPUT_KW
            self.fuel_pct = max(0.0, self.fuel_pct - 0.4)
        delta_pct = (supply - self.demand_kw) / self.CAPACITY_KWH * 100.0
        self.battery_pct = min(100.0, self.battery_pct + delta_pct)
        if self.battery_pct < self.BATTERY_FLOOR_PCT:
            if not self._in_brownout:
                self.lock.violation(self.machine_id,
                                    "battery below depth-of-discharge floor")
                self.brownouts += 1
                self._in_brownout = True
            self.battery_pct = self.BATTERY_FLOOR_PCT   # load shed
        elif self._in_brownout and self.battery_pct > \
                self.BATTERY_FLOOR_PCT + 5.0:
            self._in_brownout = False

    def telemetry(self) -> Dict[str, object]:
        return {"kind": self.KIND,
                "solar_kw": self.solar_kw(self.last_tick),
                "demand_kw": self.demand_kw,
                "battery_pct": round(self.battery_pct, 2),
                "generator_on": self.generator_on,
                "fuel_pct": round(self.fuel_pct, 2),
                "brownouts": self.brownouts}


class PumpStation:
    """Two-reservoir water transfer station with concurrent pump limits."""

    KIND = "water_pumps"
    SOURCE_CAPACITY = 200.0
    CLEARWELL_CAPACITY = 80.0
    PUMP_RATE = 3.0                  # units/tick per running pump
    MAX_CONCURRENT = 2

    def __init__(self, machine_id: str, lock: SafetyInterlock) -> None:
        self.machine_id = machine_id
        self.lock = lock
        self.source_level = 150.0
        self.clearwell_level = 20.0
        self.pump_states: Dict[str, bool] = {
            "pump_a": False, "pump_b": False, "pump_c": False}

    def _running_count(self) -> int:
        return sum(1 for on in self.pump_states.values() if on)

    def command_pump(self, pump_id: str, on: bool, tick: int) -> bool:
        if pump_id not in self.pump_states:
            return self.lock.reject(tick, self.machine_id, "pump",
                                    f"unknown pump '{pump_id}'")
        if on and self.source_level < self.PUMP_RATE:
            return self.lock.reject(tick, self.machine_id, "pump",
                                    "source reservoir nearly dry")
        if on and not self.pump_states[pump_id] \
                and self._running_count() >= self.MAX_CONCURRENT:
            return self.lock.reject(
                tick, self.machine_id, "pump",
                f"at most {self.MAX_CONCURRENT} pumps may run concurrently")
        self.pump_states[pump_id] = bool(on)
        return True

    def step(self, tick: int) -> None:
        running = self._running_count()
        if running == 0 or self.source_level < self.PUMP_RATE * running:
            # Dry-source protection: pumps auto-stop, never cavitate.
            for pid in self.pump_states:
                self.pump_states[pid] = False
            return
        moved = self.PUMP_RATE * running
        self.source_level -= moved
        self.clearwell_level += moved
        if self.clearwell_level > self.CLEARWELL_CAPACITY:
            self.lock.violation(self.machine_id, "clearwell overflow")
            self.clearwell_level = self.CLEARWELL_CAPACITY

    def telemetry(self) -> Dict[str, object]:
        return {"kind": self.KIND,
                "source_level": round(self.source_level, 2),
                "clearwell_level": round(self.clearwell_level, 2),
                "pumps_running": self._running_count()}


class ResearchVessel:
    """Civilian survey vessel: station-keeping and sample collection."""

    KIND = "research_vessel"
    MAX_SPEED = 1.5
    FUEL_CAPACITY = 100.0
    FUEL_PER_SPEED_TICK = 0.8

    def __init__(self, machine_id: str, lock: SafetyInterlock) -> None:
        self.machine_id = machine_id
        self.lock = lock
        self.x = self.y = 0.0
        self.heading = 0.0
        self.fuel = self.FUEL_CAPACITY
        self.samples_collected = 0
        self._linear = 0.0

    def command_velocity(self, linear: float, tick: int) -> bool:
        if self.lock.e_stopped:
            return self.lock.reject(tick, self.machine_id, "velocity", "e-stop")
        if abs(linear) > self.MAX_SPEED:
            return self.lock.reject(tick, self.machine_id, "velocity",
                                    f"speed {linear} exceeds "
                                    f"{self.MAX_SPEED}")
        if self.fuel <= 0 and linear != 0:
            return self.lock.reject(tick, self.machine_id, "velocity",
                                    "out of fuel -- refuel required")
        self._linear = linear
        return True

    def command_refuel(self, tick: int) -> bool:
        if self._linear != 0:
            return self.lock.reject(tick, self.machine_id, "refuel",
                                    "can only refuel while stationary")
        self.fuel = self.FUEL_CAPACITY
        return True

    def collect_sample(self, tick: int) -> bool:
        if self._linear != 0:
            return self.lock.reject(tick, self.machine_id, "sample",
                                    "station-keeping required to sample")
        self.samples_collected += 1
        return True

    def step(self, tick: int) -> None:
        self.x += math.cos(self.heading) * self._linear
        self.y += math.sin(self.heading) * self._linear
        self.fuel = max(0.0, self.fuel - abs(self._linear)
                        * self.FUEL_PER_SPEED_TICK)
        if self.fuel <= 0:
            self._linear = 0.0

    def telemetry(self) -> Dict[str, object]:
        return {"kind": self.KIND, "x": round(self.x, 3),
                "y": round(self.y, 3), "heading": round(self.heading, 3),
                "fuel": round(self.fuel, 2),
                "samples_collected": self.samples_collected}


class FreightRailcar:
    """Land freight car on a fixed track with overspeed protection."""

    KIND = "railcar"
    TRACK_LENGTH = 100.0
    SPEED_LIMIT = 3.0

    def __init__(self, machine_id: str, lock: SafetyInterlock) -> None:
        self.machine_id = machine_id
        self.lock = lock
        self.position = 0.0
        self.speed = 0.0
        self.cargo_units = 0
        self.doors_closed = True

    def command_throttle(self, speed: float, tick: int) -> bool:
        if self.lock.e_stopped and speed != 0:
            return self.lock.reject(tick, self.machine_id, "throttle", "e-stop")
        if not self.doors_closed:
            return self.lock.reject(tick, self.machine_id, "throttle",
                                    "doors open -- close before moving")
        if abs(speed) > self.SPEED_LIMIT:
            return self.lock.reject(tick, self.machine_id, "throttle",
                                    f"speed {speed} exceeds limit "
                                    f"{self.SPEED_LIMIT}")
        self.speed = speed
        return True

    def command_doors(self, open_: bool, tick: int) -> bool:
        if open_ and self.speed != 0:
            return self.lock.reject(tick, self.machine_id, "doors",
                                    "cannot open doors while moving")
        self.doors_closed = not open_
        return True

    def command_load(self, units: int, tick: int) -> bool:
        if self.speed != 0:
            return self.lock.reject(tick, self.machine_id, "load",
                                    "stop before loading")
        self.cargo_units += units
        return True

    def command_unload(self, tick: int) -> int:
        if self.speed != 0:
            self.lock.reject(tick, self.machine_id, "unload",
                             "stop before unloading")
            return 0
        moved = self.cargo_units
        self.cargo_units = 0
        return moved

    def step(self, tick: int) -> None:
        self.position += self.speed
        if self.position >= self.TRACK_LENGTH:
            self.position = float(self.TRACK_LENGTH)
            self.speed = 0.0                     # terminus: automatic stop
        if self.position < 0.0:
            self.position = 0.0
            self.speed = 0.0

    def telemetry(self) -> Dict[str, object]:
        return {"kind": self.KIND, "position": round(self.position, 3),
                "speed": round(self.speed, 3),
                "cargo_units": self.cargo_units,
                "doors_closed": self.doors_closed}


class EarthObservationSatellite:
    """Civilian imaging satellite: orbital phase, eclipse battery cycle.

    Imaging a ground target is only possible while the target is within
    the sensor window (a deterministic slice of the orbit) and the
    battery has margin; eclipses drain, sunlight charges.
    """

    KIND = "eo_satellite"
    ORBIT_PERIOD = 40                   # ticks per full orbit
    BATTERY_MIN_FOR_IMAGING = 25.0

    def __init__(self, machine_id: str, lock: SafetyInterlock) -> None:
        self.machine_id = machine_id
        self.lock = lock
        self.phase_deg = 0.0            # 0..360 along the orbit
        self.battery_pct = 80.0
        self.images: List[Dict[str, Any]] = []
        self.downlinked = 0

    def _advance(self) -> None:
        self.phase_deg = (self.phase_deg + 360.0 / self.ORBIT_PERIOD) % 360.0

    @property
    def in_sunlight(self) -> bool:
        return self.phase_deg < 180.0

    def target_visible(self) -> bool:
        """Ground targets are visible for the first quarter of each orbit."""
        return self.phase_deg < 90.0

    def command_image(self, target_id: str, tick: int) -> bool:
        if self.lock.e_stopped:
            return self.lock.reject(tick, self.machine_id, "image", "e-stop")
        if not self.target_visible():
            return self.lock.reject(tick, self.machine_id, "image",
                                    f"target not in sensor window "
                                    f"(phase {self.phase_deg:.1f})")
        if self.battery_pct < self.BATTERY_MIN_FOR_IMAGING:
            return self.lock.reject(tick, self.machine_id, "image",
                                    "insufficient battery margin")
        self.battery_pct -= 10.0
        self.images.append({"target": target_id,
                            "phase_deg": round(self.phase_deg, 2),
                            "tick": tick})
        return True

    def command_downlink(self, tick: int) -> int:
        moved = len(self.images)
        self.downlinked += moved
        self.images.clear()
        return moved

    def step(self, tick: int) -> None:
        self._advance()
        if self.in_sunlight:
            self.battery_pct = min(100.0, self.battery_pct + 3.0)
        else:
            self.battery_pct = max(0.0, self.battery_pct - 2.0)

    def telemetry(self) -> Dict[str, object]:
        return {"kind": self.KIND,
                "phase_deg": round(self.phase_deg, 2),
                "in_sunlight": self.in_sunlight,
                "battery_pct": round(self.battery_pct, 2),
                "buffered_images": len(self.images),
                "downlinked_total": self.downlinked}


class NetworkSensor:
    """Passive network-analysis sensor. OBSERVE-ONLY BY DESIGN.

    The public API deliberately contains no method that sends traffic,
    modifies hosts, or exploits anything: scan (read counters), learn a
    baseline, and flag deviations. This is the cyber-analysis capability,
    and it cannot be turned into an offensive tool through this class.
    """

    KIND = "network_sensor"

    def __init__(self, machine_id: str, lock: SafetyInterlock,
                 seed: int = 0,
                 hosts: Optional[List[str]] = None) -> None:
        self.machine_id = machine_id
        self.lock = lock
        self.rng = random.Random(seed)
        self.hosts: List[str] = list(hosts or
                                     ["web-1", "db-1", "auth-1"])
        self.baseline: Dict[str, float] = {}
        self.alert_threshold = 2.0          # deviation multiple to alert
        self.scans: List[Dict[str, Any]] = []

    def register_hosts(self, hosts: List[str]) -> None:
        self.hosts = list(hosts)

    def command_scan(self, tick: int) -> Dict[str, Any]:
        """Read current simulated traffic levels for all known hosts."""
        readings = {h: round(10.0 + self.rng.random() * 5.0, 2)
                    for h in self.hosts}
        self.scans.append({"tick": tick, "readings": readings})
        return {"tick": tick, "readings": readings}

    def learn_baseline(self, last_n_scans: int = 5) -> Dict[str, float]:
        recent = self.scans[-last_n_scans:]
        baseline: Dict[str, float] = {}
        for host in self.hosts:
            values = [s["readings"].get(host, 0.0) for s in recent]
            baseline[host] = round(
                sum(values) / max(1, len(values)), 3)
        self.baseline = baseline
        return dict(baseline)

    def analyze(self) -> List[Dict[str, Any]]:
        """Flag hosts whose latest reading deviates beyond threshold."""
        if not self.scans or not self.baseline:
            return []
        latest = self.scans[-1]["readings"]
        alerts = []
        for host, expected in sorted(self.baseline.items()):
            actual = latest.get(host, expected)
            if expected > 0 and abs(actual - expected) \
                    > self.alert_threshold * expected:
                alerts.append({
                    "host": host, "expected": expected, "actual": actual,
                    "ratio": round(actual / expected, 3),
                })
        return alerts

    def telemetry(self) -> Dict[str, object]:
        return {"kind": self.KIND, "hosts": list(self.hosts),
                "scans_taken": len(self.scans),
                "baseline_hosts": len(self.baseline)}

    def step(self, tick: int) -> None:
        pass                                  # passive sensor: nothing to do

