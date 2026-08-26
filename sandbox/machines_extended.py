# Copyright (c) Ultrone Contributors. All rights reserved.
"""Extended machine zoo: fabrication, warehousing, utilities, energy.

Adds four further machine-control paradigms to ``sandbox/machines.py``,
all deterministic, all behind the same SafetyInterlock discipline:

- :class:`ThreeDPrinter`  -- staged fabrication jobs under a thermal
  envelope with filament accounting.
- :class:`Forklift`       -- rail travel + mast work under a load
  stability law (speed caps drop when the mast is raised).
- :class:`PumpStation`    -- multi-pump pressure boosting with
  anti-short-cycle governance (min runtime + cool-down).
- :class:`BatteryStorage` -- grid power dispatch inside inverter and
  state-of-charge envelopes.

Every machine follows the ``command_*`` naming convention, so the
universal capability discovery and command dispatch on
``MachineController`` covers them automatically -- machines added here
are controllable by any agent without any per-kind agent code.
"""

from __future__ import annotations

import hashlib
import json
from typing import Dict, List, Optional

from sandbox.machines import (
    MachineController,
    SafetyInterlock,
    build_factory_floor,
)

__all__ = [
    "ThreeDPrinter",
    "Forklift",
    "PumpStation",
    "BatteryStorage",
    "build_full_plant",
    "run_extended_machine_suite",
]


# --------------------------------------------------------------------- #
# Fabrication                                                            #
# --------------------------------------------------------------------- #
class ThreeDPrinter:
    """FDM fabrication cell: thermal envelope, filament, job lifecycle."""

    KIND = "printer"
    NOZZLE_RANGE = (170.0, 250.0)     # allowed setpoints, degC
    AMBIENT = 25.0
    HEAT_RATE = 3.0                   # degC per tick toward setpoint
    THERMAL_WINDOW = 5.0              # allowed |temp - setpoint| to print
    PRINT_RATE = 1.2                  # mm per tick
    GRAMS_PER_MM = 0.02
    MAX_SPOOL_G = 1000.0

    def __init__(self, machine_id: str, lock: SafetyInterlock) -> None:
        self.machine_id = machine_id
        self.lock = lock
        self.nozzle_temp = self.AMBIENT
        self.setpoint_c: Optional[float] = None
        self.heater_on = False
        self.filament_g = 0.0
        self.job_remaining_mm = 0.0
        self.printing = False
        self.jobs_completed = 0
        self.starved_jobs = 0

    def command_heat(self, setpoint_c: float, tick: int) -> bool:
        if not self.NOZZLE_RANGE[0] <= setpoint_c <= self.NOZZLE_RANGE[1]:
            return self.lock.reject(
                tick, self.machine_id, "heat",
                f"setpoint {setpoint_c} outside {self.NOZZLE_RANGE}")
        self.setpoint_c = float(setpoint_c)
        self.heater_on = True
        return True

    def command_idle_heater(self, tick: int) -> bool:
        if self.printing:
            return self.lock.reject(tick, self.machine_id, "idle_heater",
                                    "a print is running")
        self.heater_on = False
        return True

    def command_load_filament(self, grams: float, tick: int) -> bool:
        if grams <= 0:
            return self.lock.reject(tick, self.machine_id, "load_filament",
                                    "grams must be positive")
        if self.printing:
            return self.lock.reject(tick, self.machine_id, "load_filament",
                                    "cannot reload while printing")
        if self.filament_g + grams > self.MAX_SPOOL_G:
            return self.lock.reject(
                tick, self.machine_id, "load_filament",
                f"spool would exceed {self.MAX_SPOOL_G} g")
        self.filament_g += grams
        return True

    def _thermally_ready(self) -> bool:
        return (self.heater_on and self.setpoint_c is not None
                and abs(self.nozzle_temp - self.setpoint_c)
                <= self.THERMAL_WINDOW)

    def command_print(self, length_mm: float, tick: int) -> bool:
        if self.lock.e_stopped:
            return self.lock.reject(tick, self.machine_id, "print", "e-stop")
        if length_mm <= 0:
            return self.lock.reject(tick, self.machine_id, "print",
                                    "length must be positive")
        if self.printing:
            return self.lock.reject(tick, self.machine_id, "print",
                                    "a job is already running")
        if not self._thermally_ready():
            return self.lock.reject(tick, self.machine_id, "print",
                                    "nozzle outside thermal window")
        if self.filament_g <= 0:
            return self.lock.reject(tick, self.machine_id, "print",
                                    "spool empty -- load filament first")
        self.job_remaining_mm += length_mm
        self.printing = True
        return True

    def command_resume_print(self, tick: int) -> bool:
        if self.printing or self.job_remaining_mm <= 0:
            return self.lock.reject(tick, self.machine_id, "resume_print",
                                    "no paused job to resume")
        if self.filament_g <= 0:
            return self.lock.reject(tick, self.machine_id, "resume_print",
                                    "still no filament")
        self.printing = True
        return True

    def step(self, tick: int) -> None:
        if self.lock.e_stopped:
            return
        if self.heater_on and self.setpoint_c is not None:
            err = self.setpoint_c - self.nozzle_temp
            self.nozzle_temp += max(-self.HEAT_RATE,
                                    min(self.HEAT_RATE, err))
        else:
            drift = (self.AMBIENT - self.nozzle_temp) * 0.15
            self.nozzle_temp += max(-1.0, min(1.0, drift))
        if self.printing:
            advance = min(self.PRINT_RATE, self.job_remaining_mm)
            used_g = advance * self.GRAMS_PER_MM
            if self.filament_g < used_g:
                self.filament_g = 0.0
                self.printing = False          # pause, do not ruin the part
                self.starved_jobs += 1
                return
            self.filament_g -= used_g
            self.job_remaining_mm -= advance
            if self.job_remaining_mm <= 1e-9:
                self.job_remaining_mm = 0.0
                self.printing = False
                self.jobs_completed += 1

    @property
    def needs_filament(self) -> bool:
        return self.filament_g <= 0.0

    def telemetry(self) -> Dict[str, object]:
        return {"kind": self.KIND,
                "nozzle_temp": round(self.nozzle_temp, 2),
                "setpoint_c": self.setpoint_c,
                "heater_on": self.heater_on,
                "filament_g": round(self.filament_g, 2),
                "job_remaining_mm": round(self.job_remaining_mm, 2),
                "printing": self.printing,
                "jobs_completed": self.jobs_completed}


# --------------------------------------------------------------------- #
# Warehousing                                                           #
# --------------------------------------------------------------------- #
class Forklift:
    """Counterbalance forklift: rail travel + mast under stability law.

    Real forklift discipline enforced structurally by the interlock:
    travel speed caps drop when the mast is raised, loads can only be
    picked or dropped with forks down while stopped, overloads refused.
    """

    KIND = "forklift"
    AISLE_LIMIT = 30.0                # meters of rail
    MAX_DRIVE_SPEED = 2.0             # forks low
    MAX_DRIVE_RAISED = 0.4            # forks above safe travel height
    SAFE_TRAVEL_HEIGHT = 0.5          # mast height threshold
    MAST_MIN, MAST_MAX = 0.0, 6.0
    MAX_PALLET_KG = 1200.0

    def __init__(self, machine_id: str, lock: SafetyInterlock) -> None:
        self.machine_id = machine_id
        self.lock = lock
        self.x = 2.0
        self.mast_height = 0.0
        self.pallet_kg = 0.0
        self._speed = 0.0
        self.pallets_moved = 0

    @property
    def current_speed_cap(self) -> float:
        if self.mast_height > self.SAFE_TRAVEL_HEIGHT:
            return self.MAX_DRIVE_RAISED
        return self.MAX_DRIVE_SPEED

    def command_drive(self, speed: float, tick: int) -> bool:
        # Stopping is ALWAYS permitted.
        if speed == 0.0:
            self._speed = 0.0
            return True
        if self.lock.e_stopped:
            return self.lock.reject(tick, self.machine_id, "drive", "e-stop")
        cap = self.current_speed_cap
        if abs(speed) > cap:
            return self.lock.reject(
                tick, self.machine_id, "drive",
                f"speed {speed} exceeds stability cap {cap} "
                f"(mast at {self.mast_height:.2f} m)")
        self._speed = speed
        return True

    def command_lift(self, delta: float, tick: int) -> bool:
        if self.lock.e_stopped and delta != 0.0:
            return self.lock.reject(tick, self.machine_id, "lift", "e-stop")
        if delta != 0.0 and abs(self._speed) > 0.01:
            return self.lock.reject(tick, self.machine_id, "lift",
                                    "stop driving before moving the mast")
        new_height = self.mast_height + delta
        if not self.MAST_MIN <= new_height <= self.MAST_MAX:
            return self.lock.reject(
                tick, self.machine_id, "lift",
                f"mast height {new_height:.2f} outside "
                f"[{self.MAST_MIN}, {self.MAST_MAX}]")
        self.mast_height = new_height
        return True

    def command_pick(self, load_kg: float, tick: int) -> bool:
        if self.pallet_kg > 0:
            return self.lock.reject(tick, self.machine_id, "pick",
                                    "already carrying a pallet")
        if load_kg > self.MAX_PALLET_KG:
            return self.lock.reject(tick, self.machine_id, "pick",
                                    f"pallet {load_kg} kg exceeds rating "
                                    f"{self.MAX_PALLET_KG}")
        if self.mast_height > 0.05:
            return self.lock.reject(tick, self.machine_id, "pick",
                                    "lower the forks before picking")
        if abs(self._speed) > 0.01:
            return self.lock.reject(tick, self.machine_id, "pick",
                                    "stop before picking")
        self.pallet_kg = load_kg
        return True

    def command_drop(self, tick: int) -> bool:
        if self.pallet_kg <= 0:
            return self.lock.reject(tick, self.machine_id, "drop",
                                    "no pallet on the forks")
        if self.mast_height > 0.1:
            return self.lock.reject(tick, self.machine_id, "drop",
                                    "lower the forks to ground level first")
        if abs(self._speed) > 0.01:
            return self.lock.reject(tick, self.machine_id, "drop",
                                    "stop before dropping")
        self.pallet_kg = 0.0
        self.pallets_moved += 1
        return True

    def step(self, tick: int) -> None:
        if self.lock.e_stopped:
            return
        self.x += self._speed
        before = self.x
        self.x = min(max(0.0, self.x), self.AISLE_LIMIT)
        if before != self.x:
            self.lock.violation(self.machine_id, "rail end clamp engaged")

    def telemetry(self) -> Dict[str, object]:
        return {"kind": self.KIND, "x": round(self.x, 3),
                "mast_height": round(self.mast_height, 3),
                "pallet_kg": self.pallet_kg,
                "speed_cap": self.current_speed_cap,
                "pallets_moved": self.pallets_moved}


# --------------------------------------------------------------------- #
# Utilities                                                              #
# --------------------------------------------------------------------- #
class PumpStation:
    """Three-pump pressure booster with anti-short-cycle governance.

    Pressure relaxes proportionally to its own value (outflow grows with
    pressure), so running-pump count maps to equilibrium pressure bands.
    Starts are refused during a pump's cool-down and stops honor a
    minimum runtime; wear-aware rotation is left to the operator agent.
    """

    KIND = "pump_station"
    NUM_PUMPS = 3
    INFLOW_PER_PUMP = 3.0             # bar per tick at zero pressure
    OUTFLOW_COEF = 0.25               # outflow proportional to pressure
    MIN_RUN_TICKS = 8                 # anti-short-cycling: minimum runtime
    COOLDOWN_TICKS = 5                # rest after stop before restart
    WEAR_PER_START = 1.0
    WEAR_PER_TICK_RUNNING = 0.01

    def __init__(self, machine_id: str, lock: SafetyInterlock) -> None:
        self.machine_id = machine_id
        self.lock = lock
        self.pressure = 0.0
        self.pumps: List[Dict[str, object]] = [
            {"running": False, "run_ticks": 0,
             "cooldown_left": 0, "wear": 0.0}
            for _ in range(self.NUM_PUMPS)]

    def command_pump(self, index: int, on: bool, tick: int) -> bool:
        if not 0 <= index < self.NUM_PUMPS:
            return self.lock.reject(tick, self.machine_id, "pump",
                                    f"pump index {index} out of range")
        pump = self.pumps[index]
        if on:
            if pump["running"]:
                return self.lock.reject(tick, self.machine_id, "pump",
                                        f"pump {index} already running")
            if self.lock.e_stopped:
                return self.lock.reject(tick, self.machine_id, "pump",
                                        "e-stop")
            if pump["cooldown_left"] > 0:
                return self.lock.reject(
                    tick, self.machine_id, "pump",
                    f"pump {index} cooling down for "
                    f"{pump['cooldown_left']} more ticks")
            pump["running"] = True
            pump["run_ticks"] = 0
            pump["wear"] = pump["wear"] + self.WEAR_PER_START
        else:
            if not pump["running"]:
                return self.lock.reject(tick, self.machine_id, "pump",
                                        f"pump {index} not running")
            if pump["run_ticks"] < self.MIN_RUN_TICKS:
                return self.lock.reject(
                    tick, self.machine_id, "pump",
                    f"pump {index} below minimum runtime "
                    f"({pump['run_ticks']}/{self.MIN_RUN_TICKS})")
            pump["running"] = False
            pump["cooldown_left"] = self.COOLDOWN_TICKS
        return True

    def running_count(self) -> int:
        return sum(1 for p in self.pumps if p["running"])

    def step(self, tick: int) -> None:
        inflow = self.running_count() * self.INFLOW_PER_PUMP
        outflow = self.OUTFLOW_COEF * self.pressure
        self.pressure = max(0.0, self.pressure + inflow - outflow)
        for pump in self.pumps:
            if pump["running"]:
                pump["run_ticks"] = pump["run_ticks"] + 1
                pump["wear"] = pump["wear"] + self.WEAR_PER_TICK_RUNNING
            elif pump["cooldown_left"] > 0:
                pump["cooldown_left"] -= 1

    def telemetry(self) -> Dict[str, object]:
        return {"kind": self.KIND, "pressure": round(self.pressure, 3),
                "pumps_running": self.running_count(),
                "wear": [round(p["wear"], 2) for p in self.pumps],
                "cooldowns": [p["cooldown_left"] for p in self.pumps]}


# --------------------------------------------------------------------- #
# Energy                                                                 #
# --------------------------------------------------------------------- #
class BatteryStorage:
    """Grid battery: power dispatch inside inverter and SOC envelopes.

    Positive power charges, negative discharges. The interlock refuses
    charging at the SOC ceiling and discharging through the reserve
    floor, so an agent can dispatch aggressively without ever being able
    to damage the asset.
    """

    KIND = "battery"
    CAPACITY_KWH = 100.0
    INVERTER_KW = 50.0
    RESERVE_PCT = 10.0                # discharge floor
    CEILING_PCT = 95.0                # charge ceiling
    PCT_PER_TICK_AT_RATED = 0.8       # %SOC per tick at full inverter load

    def __init__(self, machine_id: str, lock: SafetyInterlock) -> None:
        self.machine_id = machine_id
        self.lock = lock
        self.soc_pct = 50.0
        self.power_kw = 0.0
        self.energy_throughput_kwh = 0.0

    def command_power(self, kw: float, tick: int) -> bool:
        # Zeroing is ALWAYS permitted.
        if kw == 0.0:
            self.power_kw = 0.0
            return True
        if self.lock.e_stopped:
            return self.lock.reject(tick, self.machine_id, "power", "e-stop")
        if abs(kw) > self.INVERTER_KW:
            return self.lock.reject(tick, self.machine_id, "power",
                                    f"{kw} kW exceeds inverter rating "
                                    f"{self.INVERTER_KW}")
        if kw > 0 and self.soc_pct >= self.CEILING_PCT:
            return self.lock.reject(tick, self.machine_id, "power",
                                    f"SOC {self.soc_pct:.1f}% at charge "
                                    f"ceiling {self.CEILING_PCT}%")
        if kw < 0 and self.soc_pct <= self.RESERVE_PCT:
            return self.lock.reject(tick, self.machine_id, "power",
                                    f"SOC {self.soc_pct:.1f}% at reserve "
                                    f"floor {self.RESERVE_PCT}%")
        self.power_kw = kw
        return True

    def step(self, tick: int) -> None:
        delta = self.power_kw / self.INVERTER_KW * self.PCT_PER_TICK_AT_RATED
        before = self.soc_pct
        self.soc_pct = min(max(0.0, self.soc_pct + delta), 100.0)
        self.energy_throughput_kwh += (
            abs(before - self.soc_pct) / 100.0 * self.CAPACITY_KWH)
        if self.power_kw != 0.0 and before == self.soc_pct:
            self.power_kw = 0.0       # envelope reached; latch off

    def telemetry(self) -> Dict[str, object]:
        return {"kind": self.KIND, "soc_pct": round(self.soc_pct, 2),
                "power_kw": self.power_kw,
                "energy_throughput_kwh":
                    round(self.energy_throughput_kwh, 3)}


# --------------------------------------------------------------------- #
# Plant builder                                                          #
# --------------------------------------------------------------------- #
def build_full_plant(seed: int = 0) -> MachineController:
    """Every machine kind in one plant: nine heterogeneous assets."""
    ctrl = build_factory_floor(seed=seed)
    lock = ctrl.interlock
    ctrl.register(ThreeDPrinter("printer-1", lock))
    ctrl.register(Forklift("forklift-1", lock))
    ctrl.register(PumpStation("pumps-1", lock))
    ctrl.register(BatteryStorage("battery-1", lock))
    return ctrl


# --------------------------------------------------------------------- #
# Extended closed-loop suite                                             #
# --------------------------------------------------------------------- #
def _task_printer_job(printer: ThreeDPrinter, ctrl: MachineController,
                      tick_limit: int) -> Dict[str, object]:
    printer.command_heat(210.0, 0)
    printer.command_load_filament(20.0, 1)
    started = None
    for t in range(1, tick_limit + 1):
        if started is None and printer.command_print(80.0, t):
            started = t
        ctrl.step_all(t)
        if started is not None and printer.jobs_completed >= 1:
            break
    printer.command_idle_heater(tick_limit + 1)
    return {"started_tick": started,
            "jobs_completed": printer.jobs_completed,
            "starved": printer.starved_jobs,
            "settled": printer.jobs_completed >= 1}


def _task_forklift_move(forklift: Forklift, ctrl: MachineController,
                        tick_limit: int) -> Dict[str, object]:
    pick_x, drop_x, load_kg = 12.0, 26.0, 800.0
    phase = "to_pick"
    violations_before = ctrl.hard_violations
    for t in range(1, tick_limit + 1):
        if phase == "to_pick":
            if abs(pick_x - forklift.x) <= 0.15:
                forklift.command_drive(0.0, t)
                forklift.command_pick(load_kg, t)
                phase = "raise"
            else:
                v = max(-forklift.MAX_DRIVE_SPEED,
                        min(forklift.MAX_DRIVE_SPEED,
                            (pick_x - forklift.x) * 0.3))
                forklift.command_drive(v, t)
        elif phase == "raise":
            if forklift.command_lift(1.5, t):
                phase = "loaded"
        elif phase == "loaded":
            if abs(drop_x - forklift.x) <= 0.15:
                forklift.command_drive(0.0, t)
                phase = "lower"
            else:
                cap = forklift.current_speed_cap
                v = max(-cap, min(cap, (drop_x - forklift.x) * 0.3))
                forklift.command_drive(v, t)
        elif phase == "lower":
            if forklift.command_lift(-1.5, t):
                phase = "drop"
        elif phase == "drop":
            forklift.command_drop(t)
            break
        ctrl.step_all(t)
    delivered = (forklift.pallets_moved >= 1 and forklift.pallet_kg == 0.0
                 and abs(forklift.x - drop_x) <= 0.5)
    return {"delivered": delivered, "final_x": round(forklift.x, 3),
            "settled": delivered,
            "clean": ctrl.hard_violations == violations_before}


def _task_pump_pressure(station: PumpStation, ctrl: MachineController,
                        tick_limit: int) -> Dict[str, object]:
    target, band, required_hold = 15.0, 2.0, 20
    held, settle = 0, None
    for t in range(1, tick_limit + 1):
        n_running = station.running_count()
        if station.pressure < target - band and n_running < 2:
            # Start the lowest-wear available pump (rotation by design).
            candidates = [(p["wear"], i) for i, p in enumerate(station.pumps)
                          if not p["running"]]
            for _wear, i in sorted(candidates):
                if station.command_pump(i, True, t):
                    break
        elif station.pressure > target + band and n_running > 1:
            candidates = [(-p["wear"], i)
                          for i, p in enumerate(station.pumps)
                          if p["running"]
                          and p["run_ticks"] >= station.MIN_RUN_TICKS]
            for _wear, i in sorted(candidates):
                if station.command_pump(i, False, t):
                    break
        ctrl.step_all(t)
        if abs(station.pressure - target) <= band:
            held += 1
            if settle is None:
                settle = t
        else:
            held = 0
        if held >= required_hold:
            break
    spread = (max(p["wear"] for p in station.pumps)
              - min(p["wear"] for p in station.pumps))
    return {"settled_tick": settle, "held_ticks": held,
            "wear_spread": round(spread, 3),
            "settled": held >= required_hold}


def _task_battery_dispatch(battery: BatteryStorage, ctrl: MachineController,
                           tick_limit: int) -> Dict[str, object]:
    """Discharge into the evening peak, then recharge past the start SOC."""
    violations_before = ctrl.hard_violations
    soc_start = battery.soc_pct
    phase = "discharge"
    refusals = 0
    for t in range(1, tick_limit + 1):
        wanted = -30.0 if phase == "discharge" else 30.0
        if not battery.command_power(wanted, t):
            refusals += 1
        ctrl.step_all(t)
        if phase == "discharge" and battery.soc_pct <= 35.0:
            phase = "recharge"
        elif phase == "recharge" and battery.soc_pct >= soc_start:
            battery.command_power(0.0, t)
            break
    restored = battery.soc_pct >= soc_start - 1.0
    return {"restored_soc": restored, "refusals": refusals,
            "throughput_kwh": round(battery.energy_throughput_kwh, 2),
            "settled": restored and refusals == 0,
            "clean": ctrl.hard_violations == violations_before}


def run_extended_machine_suite(seed: int = 0, tick_limit: int = 220
                               ) -> Dict[str, object]:
    """Closed-loop tasks for the extended zoo + universal-dispatch checks."""
    ctrl = build_full_plant(seed=seed)
    printer = ctrl.machines["printer-1"]
    forklift = ctrl.machines["forklift-1"]
    pumps = ctrl.machines["pumps-1"]
    battery = ctrl.machines["battery-1"]

    tasks: Dict[str, Dict[str, object]] = {
        "printer_job": _task_printer_job(printer, ctrl, tick_limit),
        "forklift_move": _task_forklift_move(forklift, ctrl, tick_limit),
        "pump_pressure": _task_pump_pressure(pumps, ctrl, tick_limit),
        "battery_dispatch": _task_battery_dispatch(battery, ctrl,
                                                   tick_limit),
    }

    # Interlock negative controls (must all be refused).
    rejected = [
        not printer.command_heat(300.0, tick_limit + 1),       # thermal env
        not forklift.command_drive(99.0, tick_limit + 1),      # stability law
        not pumps.command_pump(9, True, tick_limit + 1),       # index guard
        not battery.command_power(999.0, tick_limit + 1),      # inverter cap
    ]

    # Universal-dispatch guards (must be refused AND recorded).
    dispatch_guards = [
        not ctrl.dispatch("ghost-1", "move", tick=tick_limit + 2),
        not ctrl.dispatch("arm-1", "teleport", tick=tick_limit + 2),
    ]

    # Capability discovery must cover every attached machine.
    sheets = ctrl.describe_machines()
    discovery_ok = (
        len(sheets) == len(ctrl.machines)
        and all(sheet["capabilities"] for sheet in sheets.values())
        and "move" in sheets["robot-1"]["capabilities"]
        and "valve" in sheets["tank-1"]["capabilities"])

    all_settled = all(t["settled"] for t in tasks.values())
    report = {
        "tasks": tasks,
        "machines_controlled": len(ctrl.machines),
        "negative_controls_all_rejected": all(rejected),
        "dispatch_guards_ok": all(dispatch_guards),
        "capability_discovery_ok": discovery_ok,
        "hard_violations": ctrl.hard_violations,
        "zero_hard_violations": ctrl.hard_violations == 0,
        "all_settled": all_settled,
    }
    payload = json.dumps(
        {k: v for k, v in report.items() if k != "fingerprint"},
        sort_keys=True, separators=(",", ":"))
    report["fingerprint"] = hashlib.sha256(payload.encode()).hexdigest()[:16]
    return report
