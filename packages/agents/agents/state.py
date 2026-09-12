# Copyright (c) Ultrone Contributors. All rights reserved.
"""Unified platform state view over an agent's CommandBus.

Gives higher-level AI a single read model of a simulated machine::

    agent.platform_state.get()          # full snapshot
    agent.platform_state.subsystem("propulsion")
    agent.platform_state.resources()
    agent.platform_state.faults()

Named ``platform_state`` rather than ``state`` because ``BaseAgent.state``
already carries the discrete mission-state enum; this is the continuous
subsystem-level read model.
"""

from __future__ import annotations

from typing import Any, Dict, List


def _build_state(bus, tick: int = 0) -> Dict[str, Any]:
    # Imported lazily: platform_control pulls in sandbox.ucl, which must
    # never sit on agents' import path at package-import time.
    from agents.platform_control import build_platform_state

    return build_platform_state(bus, tick)


class PlatformStateView:
    """Read-only facade over the registered subsystems of one platform."""

    def __init__(self, bus) -> None:
        self._bus = bus

    def get(self, tick: int = 0) -> Dict[str, Any]:
        """Full standardized snapshot across every subsystem."""
        return _build_state(self._bus, tick)

    def subsystem(self, name: str) -> Dict[str, Any]:
        """Status dictionary of one subsystem (KeyError if absent)."""
        return self._bus.get(name).status()

    def resources(self) -> Dict[str, Any]:
        return self.get().get("resources", {})

    def faults(self) -> List[Dict[str, Any]]:
        faults: List[Dict[str, Any]] = []
        for name in self._bus.names():
            subsystem = self._bus.get(name)
            for entry in getattr(subsystem, "faults", []):
                faults.append({"subsystem": name, **entry})
        return faults
