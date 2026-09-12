# Copyright (c) Ultrone Contributors. All rights reserved.
"""Structured command interface for simulated platforms.

Every machine operation is expressed as::

    Command(subsystem="propulsion", action="set_throttle",
            parameters={"value": 0.65})

and routed through a :class:`CommandBus` to the owning subsystem. The bus
returns a :class:`CommandResult` (never raises for domain failures), so
callers get uniform success/error semantics across every platform kind.

Simulation boundary: commands drive sandbox machines only. There is no
adapter here -- and intentionally no path -- toward real hardware,
weapons, vehicles, infrastructure, or networks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class Command:
    subsystem: str
    action: str
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CommandResult:
    success: bool
    subsystem: str
    action: str
    value: Any = None
    reason: str = ""

    @classmethod
    def ok(cls, cmd: Command, value: Any = None) -> "CommandResult":
        return cls(True, cmd.subsystem, cmd.action, value=value)

    @classmethod
    def fail(cls, cmd: Command, reason: str) -> "CommandResult":
        return cls(False, cmd.subsystem, cmd.action, reason=reason)


class UnknownSubsystemError(KeyError):
    pass


class CommandBus:
    """Routes Commands to registered subsystems."""

    def __init__(self) -> None:
        self._registry: Dict[str, Any] = {}

    def register(self, subsystem) -> None:
        if subsystem.name in self._registry:
            raise ValueError(
                f"subsystem '{subsystem.name}' already registered")
        self._registry[subsystem.name] = subsystem

    def get(self, name: str):
        return self._registry[name]

    def names(self) -> List[str]:
        return sorted(self._registry)

    def execute(self, command: Command) -> CommandResult:
        # Platform-level safety gate -- THE reason there is one command
        # path: an engaged safety interlock blocks every actuation from
        # every caller (agents, UCL controllers, scenario scripts) here,
        # exactly once. Commands addressed to "safety" itself stay
        # allowed so the interlock can be released.
        safety = self._registry.get("safety")
        if (safety is not None and getattr(safety, "estopped", False)
                and command.subsystem != "safety"):
            return CommandResult.fail(command, "e-stop engaged")
        subsystem = self._registry.get(command.subsystem)
        if subsystem is None:
            return CommandResult.fail(
                command, f"unknown subsystem '{command.subsystem}'")
        try:
            value = subsystem.handle(command.action, command.parameters)
        except KeyError as exc:
            return CommandResult.fail(command, f"unknown action: {exc}")
        except RuntimeError as exc:
            return CommandResult.fail(command, str(exc))
        return CommandResult.ok(command, value)
