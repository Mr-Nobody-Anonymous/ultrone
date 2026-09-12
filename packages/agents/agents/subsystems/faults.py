# Copyright (c) Ultrone Contributors. All rights reserved.
"""Fault injection over the subsystem architecture.

Research-grade simulation must test failures, not just success:

- ``fail_subsystem``   -- disables a subsystem (commands refused);
- ``engine_failure``   -- propulsion auto-stops and cannot restart;
- ``fuel_leak``        -- ongoing per-tick fuel drain until sealed;
- ``sensor_blind``     -- scans return degraded/empty readings;
- ``communication_blackout`` -- transmissions refused;
- ``power_depletion``  -- battery driven to zero;
- ``overheat``         -- thermal temperature forced past the limit;
- ``degrade``          -- health wear increased;
- conflicting commands -- detected via :class:`ConflictMonitor`.

All effects are deterministic and reversible where meaningful
(``seal_leak``, ``enable_subsystem``, ``repair``).
"""

from __future__ import annotations

from typing import Any, Dict, List

from agents.commands import Command, CommandBus


class FaultInjector:
    """Applies deterministic faults to registered subsystems."""

    def __init__(self, bus: CommandBus) -> None:
        self.bus = bus
        self.injected_log: List[Dict[str, Any]] = []

    # -- generic ------------------------------------------------------------- #
    def fail_subsystem(self, name: str, reason: str = "injected failure"
                       ) -> bool:
        sub = self.bus.get(name)
        sub.enabled = False
        sub.record_fault(reason)
        self._log(name, "fail", reason)
        return True

    def enable_subsystem(self, name: str) -> bool:
        self.bus.get(name).enabled = True
        self._log(name, "enable", "restored")
        return True

    # -- specific -------------------------------------------------------------- #
    def engine_failure(self) -> bool:
        prop = self.bus.get("propulsion")
        prop.handle("stop_engine")
        self.fail_subsystem("propulsion", "engine failure injected")
        return True

    def sensor_blind(self) -> bool:
        sensors = self.bus.get("sensors")
        original = sensors.scan

        def blind_scan(targets: int = 0):
            return {"mode": sensors.mode, "readings": {},
                    "degraded": True}

        sensors.scan = blind_scan                # type: ignore[method-assign]
        sensors.record_fault("sensor blinded")
        self._log("sensors", "blind", "readings suppressed")
        return True

    def communication_blackout(self) -> bool:
        comms = self.bus.get("communications")
        comms.enabled = False
        self.fail_subsystem("communications",
                            "communication blackout")
        return True

    def power_depletion(self) -> None:
        power = self.bus.get("power")
        power.battery_pct = 0.0
        power.record_fault("battery depleted (injected)")
        self._log("power", "depletion", "battery to zero")

    def navigation_failure(self) -> None:
        nav = self.bus.get("navigation")
        nav.destination = None
        self.fail_subsystem("navigation", "navigation failure injected")

    def overheat(self, temperature: float = 95.0) -> None:
        thermal = self.bus.get("thermal")
        thermal.temperature = float(temperature)
        thermal.lock_in_overheat()
        self._log("thermal", "overheat", f"forced {temperature}")

    def degrade(self, amount: float = 25.0) -> None:
        health = self.bus.get("health")
        health.wear = min(100.0, health.wear + amount)
        # Degradation must be OBSERVABLE, not silent: record it so the
        # unified state's active_faults / fault counts reflect reality.
        health.record_fault(f"degradation injected (+{amount})")
        self._log("health", "degrade", f"wear={round(health.wear, 2)}")

    def fuel_leak(self, rate: float = 1.5) -> None:
        """Ongoing effect: call :meth:`tick` each simulated tick."""
        self.leak_rate = rate
        self._log("propulsion", "fuel_leak", f"rate={rate}")

    def seal_leak(self) -> None:
        self.leak_rate = 0.0

    leak_rate = 0.0

    def tick(self, tick: int) -> None:
        if getattr(self, "leak_rate", 0.0) > 0 \
                and "propulsion" in self.bus.names():
            prop = self.bus.get("propulsion")
            prop.fuel = max(0.0, prop.fuel - self.leak_rate)

    # -- conflicting commands ---------------------------------------------- #
    def detect_conflicts(self, history: List[Command]) -> List[Dict[str, Any]]:
        """Same subsystem+action issued twice within adjacent entries with
        contradictory parameters (simple opposite-sign detection)."""
        conflicts: List[Dict[str, Any]] = []
        for prev, curr in zip(history, history[1:]):
            if prev.subsystem != curr.subsystem or prev.action != curr.action:
                continue
            for key in set(prev.parameters) & set(curr.parameters):
                a, b = prev.parameters[key], curr.parameters[key]
                if isinstance(a, (int, float)) and isinstance(b, (int, float)) \
                        and a * b < 0:
                    conflicts.append({
                        "subsystem": prev.subsystem,
                        "action": prev.action,
                        "parameter": key,
                        "values": [a, b],
                    })
        return conflicts

    # -- internal ------------------------------------------------------------ #
    def _log(self, subsystem: str, kind: str, detail: str) -> None:
        self.injected_log.append({"subsystem": subsystem,
                                  "kind": kind, "detail": detail})