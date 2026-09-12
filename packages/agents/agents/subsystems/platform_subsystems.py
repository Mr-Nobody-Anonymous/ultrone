# Copyright (c) Ultrone Contributors. All rights reserved.
"""Concrete simulated subsystems (deterministic, interlock-friendly).

Propulsion / Power / Navigation / Sensors / Communication /
Payload / Health / Autonomy. Each is self-contained: state + declared
commands (via the ``@command`` decorator) + a ``tick`` dynamics hook.
Platforms compose them; nothing here knows about specific platforms.
"""

from __future__ import annotations

import random
from collections import deque
from typing import Any, Dict, Optional

from agents.subsystems.base import Subsystem, command


class PropulsionSubsystem(Subsystem):
    """Engine state, throttle, fuel burn."""

    name = "propulsion"

    def __init__(self, fuel_capacity: float = 100.0,
                 burn_per_tick_at_full: float = 0.5,
                 max_speed: float = 3.0, seed: int = 0) -> None:
        super().__init__()
        self.engine_on = False
        self.throttle = 0.0
        self.fuel_capacity = fuel_capacity
        self.fuel = fuel_capacity
        self.max_speed = max_speed

    @command("start_engine")
    def start_engine(self) -> bool:
        if self.fuel <= 0:
            self.record_fault("start refused: no fuel")
            return False
        self.engine_on = True
        return True

    @command("stop_engine")
    def stop_engine(self) -> bool:
        self.engine_on = False
        self.throttle = 0.0
        return True

    @command("set_throttle")
    def set_throttle(self, value: float = 0.0) -> float:
        if not self.engine_on:
            raise RuntimeError("engine off -- start_engine first")
        self.throttle = min(1.0, max(0.0, float(value)))
        if self.fuel <= 0 and self.throttle > 0:
            self.record_fault("throttle refused: no fuel")
            self.throttle = 0.0
        return self.throttle

    @command("refuel")
    def refuel(self, amount: float = 0.0) -> float:
        take = amount if amount > 0 else self.fuel_capacity - self.fuel
        self.fuel = min(self.fuel_capacity, self.fuel + float(take))
        return round(self.fuel, 3)

    def tick(self, tick: int) -> None:
        if not self.engine_on or self.throttle <= 0:
            return
        self.fuel = max(0.0, self.fuel - self.throttle * 0.5)
        if self.fuel <= 0:
            self.record_fault("fuel exhausted: engine auto-stop")
            self.stop_engine()

    @property
    def speed_available(self) -> float:
        return self.max_speed * self.throttle

    def status(self) -> Dict[str, Any]:
        return {**super().status(), "engine_on": self.engine_on,
                "throttle": round(self.throttle, 3),
                "fuel": round(self.fuel, 3),
                "speed_available": round(self.speed_available, 3)}


class PowerSubsystem(Subsystem):
    name = "power"

    def __init__(self, battery_pct: float = 100.0,
                 generation_kw: float = 2.0) -> None:
        super().__init__()
        self.battery_pct = battery_pct
        self.generation_kw = generation_kw
        self.load_kw = 0.5

    @command("set_load")
    def set_load(self, kw: float = 0.5) -> float:
        self.load_kw = max(0.0, float(kw))
        return self.load_kw

    @command("recharge")
    def recharge(self, pct: float = 25.0) -> float:
        self.battery_pct = min(100.0, self.battery_pct + float(pct))
        return round(self.battery_pct, 3)

    def tick(self, tick: int) -> None:
        net = (self.generation_kw - self.load_kw) / 10.0
        self.battery_pct = min(100.0, max(0.0, self.battery_pct + net))
        if self.battery_pct <= 0.0:
            self.record_fault("battery depleted")

    def status(self) -> Dict[str, Any]:
        return {**super().status(),
                "battery_pct": round(self.battery_pct, 3),
                "load_kw": round(self.load_kw, 3)}


class NavigationSubsystem(Subsystem):
    name = "navigation"

    def __init__(self, x: float = 0.0, y: float = 0.0,
                 heading_deg: float = 0.0) -> None:
        super().__init__()
        self.x, self.y = x, y
        self.heading_deg = heading_deg % 360.0
        self.destination: Optional[Dict[str, float]] = None

    @command("set_destination")
    def set_destination(self, position: List[float] = None
                        ) -> Dict[str, float]:
        px, py = (position or [self.x, self.y])[:2]
        self.destination = {"x": float(px), "y": float(py)}
        return dict(self.destination)

    @command("set_heading")
    def set_heading(self, deg: float = 0.0) -> float:
        self.heading_deg = deg % 360.0
        return self.heading_deg

    def distance_to_destination(self) -> float:
        if not self.destination:
            return 0.0
        dx = self.destination["x"] - self.x
        dy = self.destination["y"] - self.y
        return (dx * dx + dy * dy) ** 0.5

    def status(self) -> Dict[str, Any]:
        return {**super().status(), "x": round(self.x, 3),
                "y": round(self.y, 3),
                "heading": round(self.heading_deg, 3),
                "destination": self.destination}


class SensorSubsystem(Subsystem):
    name = "sensors"
    MODES = ("visual", "thermal", "acoustic")

    def __init__(self, seed: int = 0) -> None:
        super().__init__()
        self.mode = "visual"
        self.rng = random.Random(seed)
        self.last_scan: Optional[Dict[str, Any]] = None

    @command("set_mode")
    def set_mode(self, mode: str = "visual") -> str:
        if mode not in self.MODES:
            raise RuntimeError(f"unknown sensor mode '{mode}'")
        self.mode = mode
        return self.mode

    @command("scan")
    def scan(self, targets: int = 3) -> Dict[str, Any]:
        self.last_scan = {"mode": self.mode,
                          "readings": {f"contact_{i}":
                                       round(self.rng.random() * 100, 2)
                                       for i in range(max(1, targets))}}
        return dict(self.last_scan)


class CommunicationSubsystem(Subsystem):
    name = "communications"

    def __init__(self, bandwidth_units: int = 10) -> None:
        super().__init__()
        self.bandwidth_units = bandwidth_units
        self.outbox: deque = deque()

    @command("transmit")
    def transmit(self, recipient: str = "",
                 content: Any = None) -> bool:
        if not recipient:
            raise RuntimeError("recipient required")
        self.outbox.append({"recipient": recipient,
                            "content": content})
        return True

    def drain_outbox(self) -> List[Dict[str, Any]]:
        items = list(self.outbox)
        self.outbox.clear()
        return items


class PayloadSubsystem(Subsystem):
    name = "payload"

    def __init__(self, capacity_kg: float = 50.0) -> None:
        super().__init__()
        self.capacity_kg = capacity_kg
        self.carried_kg = 0.0

    @command("load")
    def load(self, kg: float = 0.0) -> float:
        kg = float(kg)
        if kg < 0 or self.carried_kg + kg > self.capacity_kg:
            raise RuntimeError(
                f"payload exceeds capacity ({self.capacity_kg} kg)")
        self.carried_kg += kg
        return round(self.carried_kg, 3)

    @command("unload")
    def unload(self) -> float:
        moved = self.carried_kg
        self.carried_kg = 0.0
        return round(moved, 3)

    def status(self) -> Dict[str, Any]:
        return {**super().status(),
                "carried_kg": round(self.carried_kg, 3),
                "capacity_kg": self.capacity_kg}


class HealthSubsystem(Subsystem):
    name = "health"

    def __init__(self, wear_rate: float = 0.05) -> None:
        super().__init__()
        self.wear = 0.0
        self.wear_rate = wear_rate

    @command("run_diagnostics")
    def run_diagnostics(self) -> Dict[str, Any]:
        return {"wear": round(self.wear, 3), "service_due":
                self.wear >= 80.0}

    @command("repair")
    def repair(self) -> float:
        self.wear = 0.0
        return self.wear

    def tick(self, tick: int) -> None:
        self.wear = min(100.0, self.wear + self.wear_rate)


class AutonomySubsystem(Subsystem):
    name = "autonomy"

    def __init__(self) -> None:
        super().__init__()
        self.mode = "manual"
        self.task_queue: deque = deque()

    @command("set_mode")
    def set_mode(self, mode: str = "manual") -> str:
        if mode not in ("manual", "auto"):
            raise RuntimeError(f"unknown autonomy mode '{mode}'")
        self.mode = mode
        return self.mode

    @command("enqueue_task")
    def enqueue_task(self, task: Dict[str, Any] = None) -> int:
        task = task or {}
        self.task_queue.append(task)
        return len(self.task_queue)

    @command("pop_task")
    def pop_task(self) -> Optional[Dict[str, Any]]:
        return self.task_queue.popleft() if self.task_queue else None


# --------------------------------------------------------------------- #
# Compatibility re-exports                                                #
#                                                                         #
# These four subsystems now live in their own focused modules             #
# (thermal.py / attitude.py / environment.py / resource.py). They are     #
# re-imported here so every historical import path keeps working.         #
# --------------------------------------------------------------------- #
from agents.subsystems.attitude import AttitudeSubsystem        # noqa: E402
from agents.subsystems.environment import EnvironmentSubsystem  # noqa: E402
from agents.subsystems.resource import ResourceSubsystem        # noqa: E402
from agents.subsystems.thermal import ThermalSubsystem          # noqa: E402
