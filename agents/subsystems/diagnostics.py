# Copyright (c) Ultrone Contributors. All rights reserved.
"""Diagnostics subsystem: platform-wide fault/wear aggregation.

The platform-level face of fault management: sibling subsystems are
registered with it, and one sweep reports enabled state, wear, and fault
counts across the whole machine. Read-mostly by design -- injecting
faults stays the job of ``agents.subsystems.faults.FaultInjector``.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from agents.subsystems.base import Subsystem, command


class DiagnosticsSubsystem(Subsystem):
    """Aggregate health reporting across registered sibling subsystems."""

    name = "diagnostics"

    def __init__(self, history_size: int = 20) -> None:
        super().__init__()
        self._components: List[Any] = []
        self._history: List[Dict[str, Any]] = []
        self._history_size = int(history_size)

    @command("register_component")
    def register_component(self, component: Any = None) -> int:
        if component is None or not hasattr(component, "status"):
            raise RuntimeError("component must expose status()")
        if component not in self._components:
            self._components.append(component)
        return len(self._components)

    @command("run_full_sweep")
    def run_full_sweep(self) -> Dict[str, Any]:
        report: Dict[str, Any] = {}
        worst_wear = 0.0
        total_faults = 0
        for component in self._components:
            status = component.status()
            name = str(status.get("subsystem",
                                  type(component).__name__))
            faults = len(getattr(component, "faults", []))
            wear = float(status.get("wear", 0.0)) \
                if isinstance(status.get("wear"), (int, float)) else 0.0
            report[name] = {
                "enabled": bool(status.get("enabled", True)),
                "faults": faults,
                "wear": round(wear, 3),
            }
            total_faults += faults
            worst_wear = max(worst_wear, wear)
        entry = {"total_faults": total_faults,
                 "worst_wear": round(worst_wear, 3),
                 "components": len(report)}
        self._history.append(entry)
        del self._history[:-self._history_size]
        return {**entry, "per_subsystem": report}

    @command("clear_history")
    def clear_history(self) -> int:
        count = len(self._history)
        self._history.clear()
        return count

    def watch_bus(self, bus) -> int:
        """Convenience: register every subsystem already on a CommandBus."""
        for name in bus.names():
            self.register_component(bus.get(name))
        return len(self._components)

    def status(self) -> Dict[str, Any]:
        return {**super().status(),
                "components": len(self._components),
                "sweeps_run": len(self._history)}
