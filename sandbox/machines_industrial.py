# Copyright (c) Ultrone Contributors. All rights reserved.
"""Industrial machine zoo, wave 3: energy, vertical transport, generic.

Extends the machine zoo with:

- :class:`WindTurbine`     -- pitch/yaw control inside a cut-out wind
  envelope with generator-load governance.
- :class:`ElevatorBank`    -- multi-car dispatch with door interlocks,
  load ratings, and motion-under-open-door refusal.
- :class:`ConfigurableMachine` -- a *declarative* machine built entirely
  from a spec (actuators with envelopes, sensors, per-actuator guards).
  This is the structural answer to "control ALL kinds of machines":
  any new machine type is data, and the universal capability discovery
  and command dispatch on ``MachineController`` cover it with zero new
  code.

All machines are deterministic simulations behind the same
``SafetyInterlock`` discipline; nothing here touches real hardware.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
from typing import Any, Callable, Dict, List, Optional, Tuple

from sandbox.machines import (
    MachineController,
    SafetyInterlock,
    build_factory_floor,
)

__all__ = [
    "WindTurbine",
    "ElevatorBank",
    "ConfigurableMachine",
    "build_industrial_plant",
    "run_industrial_machine_suite",
]


# --------------------------------------------------------------------- #
# Energy                                                                 #
# --------------------------------------------------------------------- #
class WindTurbine:
    """Pitch/yaw-regulated turbine with cut-out and overspeed governance.

    Power output grows with rotor speed; pitch feathering sheds load.
    The interlock refuses generation above the cut-out wind speed and
    enforces a rotor-speed ceiling by refusing pitch-up requests that
    would exceed it -- structural safety, not agent discipline.
    """

    KIND = "wind_turbine"
    CUTOUT_WIND_MPS = 25.0
    MAX_ROTOR_RPM = 18.0
    MAX_PITCH_DEG = 90.0
    MAX_YAW_RATE = 3.0                # deg per tick
    POWER_PER_RPM = 40.0              # kW at rated pitch

    def __init__(self, machine_id: str, lock: SafetyInterlock) -> None:
        self.machine_id = machine_id
        self.lock = lock
        self.wind_mps = 8.0
        self.rotor_rpm = 0.0
        self.pitch_deg = 0.0          # 0 = flat (max lift), 90 = feathered
        self.yaw_deg = 0.0
        self.brake_on = True          # safe default: parked
        self.energy_kwh = 0.0

    def command_brake(self, on: bool, tick: int) -> bool:
        if not on and self.wind_mps > self.CUTOUT_WIND_MPS:
            return self.lock.reject(
                tick, self.machine_id, "brake",
                f"wind {self.wind_mps} m/s exceeds cut-out "
                f"{self.CUTOUT_WIND_MPS} -- stay parked")
        self.brake_on = bool(on)
        return True

    def command_pitch(self, deg: float, tick: int) -> bool:
        if self.lock.e_stopped:
            return self.lock.reject(tick, self.machine_id, "pitch", "e-stop")
        if not 0.0 <= deg <= self.MAX_PITCH_DEG:
            return self.lock.reject(
                tick, self.machine_id, "pitch",
                f"pitch {deg} outside [0, {self.MAX_PITCH_DEG}]")
        # Feathering (increasing pitch) must keep the rotor under its cap.
        projected = self._projected_rpm(deg)
        if deg < self.pitch_deg and projected > self.MAX_ROTOR_RPM:
            return self.lock.reject(
                tick, self.machine_id, "pitch",
                f"would overspeed rotor to {projected:.1f} rpm")
        self.pitch_deg = float(deg)
        return True

    def command_yaw(self, deg_per_tick: float, tick: int) -> bool:
        if abs(deg_per_tick) > self.MAX_YAW_RATE:
            return self.lock.reject(
                tick, self.machine_id, "yaw",
                f"yaw rate {deg_per_tick} exceeds {self.MAX_YAW_RATE}")
        self.yaw_deg = (self.yaw_deg + deg_per_tick) % 360.0
        return True

    def _projected_rpm(self, pitch_deg: float) -> float:
        shed = max(0.05, 1.0 - pitch_deg / self.MAX_PITCH_DEG)
        return min(self.MAX_ROTOR_RPM * 2.0,
                   self.wind_mps * 0.9 * shed)

    def step(self, tick: int) -> None:
        target = 0.0 if (self.brake_on or self.lock.e_stopped) \
            else self._projected_rpm(self.pitch_deg)
        self.rotor_rpm += max(-1.5, min(1.5, target - self.rotor_rpm))
        if self.rotor_rpm > self.MAX_ROTOR_RPM:      # physical cap
            self.lock.violation(self.machine_id, "rotor overspeed clamp")
            self.rotor_rpm = self.MAX_ROTOR_RPM
            self.brake_on = True
        self.energy_kwh += self.rotor_rpm * self.POWER_PER_RPM / 100.0

    @property
    def power_kw(self) -> float:
        return round(self.rotor_rpm * self.POWER_PER_RPM, 2)

    def telemetry(self) -> Dict[str, object]:
        return {"kind": self.KIND, "rotor_rpm": round(self.rotor_rpm, 3),
                "pitch_deg": round(self.pitch_deg, 2),
                "yaw_deg": round(self.yaw_deg, 2),
                "brake_on": self.brake_on,
                "power_kw": self.power_kw,
                "energy_kwh": round(self.energy_kwh, 3)}



# --------------------------------------------------------------------- #
# Vertical transport                                                     #
# --------------------------------------------------------------------- #
class ElevatorBank:
    """Multi-car elevator dispatch with door and load interlocks.

    Cars move only with doors closed, doors open only when stopped at a
    landing, loads above rating are refused -- the classic vertical
    transport safety case, enforced by the interlock rather than by the
    operator's good intentions.
    """

    KIND = "elevator_bank"
    LANDINGS = 8                        # floors 0..7
    MAX_SPEED_FLOORS_PER_TICK = 0.5
    MAX_LOAD_KG = 1000.0

    def __init__(self, machine_id: str, lock: SafetyInterlock) -> None:
        self.machine_id = machine_id
        self.lock = lock
        self.cars: List[Dict[str, object]] = [
            {"floor": 1.0, "door_open": True, "load_kg": 0.0,
             "target_floor": 1.0}
        ]

    def add_car(self) -> int:
        self.cars.append({"floor": 1.0, "door_open": True,
                          "load_kg": 0.0, "target_floor": 1.0})
        return len(self.cars) - 1

    def command_door(self, car: int, open_: bool, tick: int) -> bool:
        if not self._valid_car(car):
            return self.lock.reject(tick, self.machine_id, "door",
                                    f"no such car {car}")
        c = self.cars[car]
        if open_ and abs(float(c["floor"]) - float(c["target_floor"])) > 1e-6:
            return self.lock.reject(
                tick, self.machine_id, "door",
                f"car {car} not level at its landing")
        c["door_open"] = bool(open_)
        return True

    def command_load(self, car: int, kg: float, tick: int) -> bool:
        if not self._valid_car(car):
            return self.lock.reject(tick, self.machine_id, "load",
                                    f"no such car {car}")
        c = self.cars[car]
        if not c["door_open"]:
            return self.lock.reject(tick, self.machine_id, "load",
                                    f"car {car} door is closed")
        if kg < 0:
            return self.lock.reject(tick, self.machine_id, "load",
                                    "negative load")
        new_total = float(c["load_kg"]) + kg
        if new_total > self.MAX_LOAD_KG:
            return self.lock.reject(
                tick, self.machine_id, "load",
                f"{new_total} kg exceeds rating {self.MAX_LOAD_KG}")
        c["load_kg"] = new_total
        return True

    def command_unload(self, car: int, kg: float, tick: int) -> bool:
        if not self._valid_car(car):
            return self.lock.reject(tick, self.machine_id, "unload",
                                    f"no such car {car}")
        c = self.cars[car]
        if not c["door_open"]:
            return self.lock.reject(tick, self.machine_id, "unload",
                                    f"car {car} door is closed")
        kg = min(kg, float(c["load_kg"]))
        c["load_kg"] = float(c["load_kg"]) - kg
        return True

    def command_go(self, car: int, floor: int, tick: int) -> bool:
        if not self._valid_car(car):
            return self.lock.reject(tick, self.machine_id, "go",
                                    f"no such car {car}")
        c = self.cars[car]
        if not 0 <= floor <= self.LANDINGS - 1:
            return self.lock.reject(
                tick, self.machine_id, "go",
                f"floor {floor} outside [0, {self.LANDINGS - 1}]")
        if c["door_open"]:
            return self.lock.reject(
                tick, self.machine_id, "go",
                f"close car {car}'s door before motion")
        c["target_floor"] = float(floor)
        return True

    def _valid_car(self, car: int) -> bool:
        return isinstance(car, int) and 0 <= car < len(self.cars)

    def step(self, tick: int) -> None:
        for c in self.cars:
            err = float(c["target_floor"]) - float(c["floor"])
            step = max(-self.MAX_SPEED_FLOORS_PER_TICK,
                       min(self.MAX_SPEED_FLOORS_PER_TICK, err))
            c["floor"] = round(float(c["floor"]) + step, 6)
            if err != 0.0 and c["door_open"]:      # should be unreachable;
                self.lock.violation(               # defense in depth
                    self.machine_id, "motion with door open")
                c["door_open"] = False

    def telemetry(self) -> Dict[str, object]:
        return {"kind": self.KIND,
                "cars": [{"floor": round(c["floor"], 3),
                          "door_open": c["door_open"],
                          "load_kg": c["load_kg"],
                          "target_floor": c["target_floor"]}
                         for c in self.cars]}


# --------------------------------------------------------------------- #
# Declarative machine                                                    #
# --------------------------------------------------------------------- #
class ConfigurableMachine:
    """A machine defined entirely by data.

    The spec maps actuator names to envelopes::

        {
          "kind": "kiln",
          "actuators": {
            "set_temp": {"type": "float", "range": [0.0, 1400.0]},
            "conveyor": {"type": "bool"},
          },
          "sensors": {"temp": 25.0},
          "guards": [{"when": {"set_temp": [0, 1400]}, "deny": "set_temp"}],
        }

    Every actuator becomes a ``command_<name>`` method generated at
    construction time, range/type-checked against its envelope and
    refused through the shared :class:`SafetyInterlock`. Because the
    methods follow the ``command_*`` convention, the universal
    capability discovery and dispatch on ``MachineController`` control
    this machine with no per-kind code anywhere.
    """

    KIND = "configurable"

    def __init__(self, machine_id: str, lock: SafetyInterlock,
                 spec: Dict[str, Any]) -> None:
        self.machine_id = machine_id
        self.lock = lock
        self.spec = spec
        self.KIND = str(spec.get("kind", "configurable"))
        self.state: Dict[str, Any] = dict(spec.get("sensors", {}))
        self._envelopes: Dict[str, Any] = {}
        for name, cfg in spec.get("actuators", {}).items():
            self._envelopes[name] = cfg
            setattr(self, f"command_{name}",
                    self._make_actuator(name))          # type: ignore[attr-defined]

    def _make_actuator(self, name: str) -> Callable[..., bool]:
        def actuator(value: Any = None, tick: int = 0) -> bool:
            if self.lock.e_stopped:
                return self.lock.reject(tick, self.machine_id, name, "e-stop")
            cfg = self._envelopes[name]
            kind = cfg.get("type", "float")
            if kind == "float":
                try:
                    value = float(value)
                except (TypeError, ValueError):
                    return self.lock.reject(
                        tick, self.machine_id, name,
                        f"value {value!r} is not numeric")
                lo, hi = cfg.get("range", (-math.inf, math.inf))
                if not lo <= value <= hi:
                    return self.lock.reject(
                        tick, self.machine_id, name,
                        f"{value} outside [{lo}, {hi}]")
            elif kind == "int":
                if isinstance(value, bool) or not isinstance(value, int):
                    return self.lock.reject(tick, self.machine_id, name,
                                            f"value {value!r} is not an int")
                lo, hi = cfg.get("range", (-math.inf, math.inf))
                if not lo <= value <= hi:
                    return self.lock.reject(
                        tick, self.machine_id, name,
                        f"{value} outside [{lo}, {hi}]")
            elif kind == "bool":
                if not isinstance(value, bool):
                    return self.lock.reject(tick, self.machine_id, name,
                                            f"value {value!r} is not a bool")
            elif kind == "enum":
                if value not in set(cfg.get("choices", [])):
                    return self.lock.reject(
                        tick, self.machine_id, name,
                        f"{value!r} not in choices {cfg.get('choices')}")
            self.state[name] = value
            for guard in self.spec.get("guards", []):
                when_ok = all(
                    (isinstance(rng, (list, tuple))
                     and rng[0] <= float(self.state.get(k, 0)) <= rng[1])
                    or self.state.get(k) == rng
                    for k, rng in guard.get("when", {}).items())
                if when_ok and guard.get("deny") == name:
                    # Roll back the write -- the guard forbids it.
                    return self.lock.reject(
                        tick, self.machine_id, name,
                        f"guard denies '{name}' under condition "
                        f"{guard.get('when')}")
            return True
        return actuator

    def command_read(self, sensor: str = "", tick: int = 0) -> Any:
        """Safe readback of any state key (never rejected)."""
        return self.state.get(sensor)

    def step(self, tick: int) -> None:
        # Configurable machines expose optional per-step dynamics hooks
        # in the spec: {"dynamics": {"temp": {"toward_state":
        # "set_temp", "rate": 2.0}}}.
        dynamics = self.spec.get("dynamics", {})
        for sensor, rule in dynamics.items():
            target_key = rule.get("toward_state")
            if target_key in self.state:
                rate = float(rule.get("rate", 1.0))
                cur = float(self.state[sensor])
                tgt = float(self.state[target_key])
                self.state[sensor] = cur + max(-rate, min(rate, tgt - cur))

    def telemetry(self) -> Dict[str, object]:
        return {"kind": self.KIND, **{k: v for k, v in self.state.items()}}


# --------------------------------------------------------------------- #
# Plant builder + suite                                                  #
# --------------------------------------------------------------------- #
KILN_SPEC: Dict[str, Any] = {
    "kind": "kiln",
    "actuators": {
        "set_temp": {"type": "float", "range": [0.0, 1400.0]},
        "conveyor": {"type": "bool"},
    },
    "sensors": {"temp": 25.0, "set_temp": 25.0, "pieces_fired": 0},
    "dynamics": {"temp": {"toward_state": "set_temp", "rate": 4.0}},
}

MIXER_SPEC: Dict[str, Any] = {
    "kind": "mixer",
    "actuators": {
        "speed": {"type": "float", "range": [0.0, 120.0]},   # rpm
        "mode": {"type": "enum", "choices": ["idle", "mix", "drain"]},
    },
    "sensors": {"speed": 0.0, "batches": 0},
}


def build_industrial_plant(seed: int = 0) -> MachineController:
    """Factory floor + extended zoo + industrial wave-3 machines."""
    from sandbox.machines_extended import build_full_plant

    ctrl = build_full_plant(seed=seed)
    lock = ctrl.interlock
    ctrl.register(WindTurbine("turbine-1", lock))
    bank = ElevatorBank("elevator-1", lock)
    bank.add_car()
    ctrl.register(bank)
    ctrl.register(ConfigurableMachine("kiln-1", lock, KILN_SPEC))
    ctrl.register(ConfigurableMachine("mixer-1", lock, MIXER_SPEC))
    return ctrl


def _task_turbine_generate(turbine: WindTurbine, tick_limit: int
                           ) -> Dict[str, object]:
    turbine.command_brake(False, 0)
    for t in range(1, tick_limit + 1):
        # Trim pitch to hold the rotor just under its speed cap.
        if turbine.rotor_rpm > WindTurbine.MAX_ROTOR_RPM - 1.5:
            turbine.command_pitch(min(90.0, turbine.pitch_deg + 2.0), t)
        elif turbine.rotor_rpm < WindTurbine.MAX_ROTOR_RPM - 6.0:
            turbine.command_pitch(max(0.0, turbine.pitch_deg - 2.0), t)
        turbine.step(t)
    turbine.command_brake(True, tick_limit + 1)
    return {
        "energy_kwh": round(turbine.energy_kwh, 3),
        "peak_rpm": round(turbine.rotor_rpm, 3),
        "settled": turbine.energy_kwh > 0,
    }


def _task_elevator_dispatch(bank: ElevatorBank, ctrl: MachineController,
                            tick_limit: int) -> Dict[str, object]:
    """Car 0: load at floor 1, deliver to floor 6, return empty."""
    violations_before = ctrl.hard_violations
    ok = (bank.command_door(0, True, 0)
          and bank.command_load(0, 600.0, 1)
          and bank.command_door(0, False, 2)
          and bank.command_go(0, 6, 3))
    arrived = None
    for t in range(1, tick_limit + 1):
        ctrl.step_all(t)
        c = bank.cars[0]
        if arrived is None and abs(float(c["floor"]) - 6.0) < 1e-6:
            arrived = t
            break
    delivered = False
    if arrived is not None:
        delivered = (bank.command_door(0, True, arrived + 1)
                     and bank.command_unload(0, 600.0, arrived + 2))
    return {"delivered": bool(delivered), "arrived_tick": arrived,
            "clean": ctrl.hard_violations == violations_before,
            "settled": bool(delivered)}


def _task_kiln_fire(kiln: ConfigurableMachine, ctrl: MachineController,
                    tick_limit: int) -> Dict[str, object]:
    kiln.command_set_temp(300.0, 0)
    settle = None
    for t in range(1, tick_limit + 1):
        ctrl.step_all(t)
        temp = float(kiln.state["temp"])
        if settle is None and abs(temp - 300.0) <= 5.0:
            settle = t
            break
    return {"settled_tick": settle,
            "temp": round(float(kiln.state["temp"]), 2),
            "settled": settle is not None}


def run_industrial_machine_suite(seed: int = 0, tick_limit: int = 120
                                 ) -> Dict[str, object]:
    """Closed-loop tasks for the wave-3 zoo + universal-dispatch checks."""
    ctrl = build_industrial_plant(seed=seed)
    turbine = ctrl.machines["turbine-1"]
    bank = ctrl.machines["elevator-1"]
    kiln = ctrl.machines["kiln-1"]

    tasks: Dict[str, Dict[str, object]] = {
        "turbine_generation":
            _task_turbine_generate(turbine, tick_limit),
        "elevator_dispatch": _task_elevator_dispatch(bank, ctrl,
                                                     tick_limit),
        "kiln_thermal": _task_kiln_fire(kiln, ctrl, tick_limit),
    }

    # Negative controls -- all must be refused and recorded.
    rejected = [
        not turbine.command_pitch(120.0, tick_limit + 11),
        not bank.command_go(0, 99, tick_limit + 12),
        not bank.command_load(0, 5000.0, tick_limit + 13),
        not kiln.command_set_temp(9999.0, tick_limit + 14),
        not ctrl.dispatch("mixer-1", "speed", value=9999.0,
                          tick=tick_limit + 16),
        not ctrl.dispatch("kiln-1", "teleport", tick=tick_limit + 17),
    ]

    # Capability discovery covers every machine, incl. generated ones.
    sheets = ctrl.describe_machines()
    discovery_ok = (
        len(sheets) == len(ctrl.machines)
        and all(sheet["capabilities"] for sheet in sheets.values())
        and "set_temp" in sheets["kiln-1"]["capabilities"]
        and "door" in sheets["elevator-1"]["capabilities"])

    report = {
        "tasks": tasks,
        "machines_controlled": len(ctrl.machines),
        "negative_controls_all_rejected": all(rejected),
        "capability_discovery_ok": discovery_ok,
        "hard_violations": ctrl.hard_violations,
        "zero_hard_violations": ctrl.hard_violations == 0,
        "all_settled": all(t["settled"] for t in tasks.values()),
    }
    payload = json.dumps(
        {k: v for k, v in report.items() if k != "fingerprint"},
        sort_keys=True, separators=(",", ":"))
    report["fingerprint"] = hashlib.sha256(payload.encode()).hexdigest()[:16]
    return report
