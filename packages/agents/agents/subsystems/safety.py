# Copyright (c) Ultrone Contributors. All rights reserved.
"""Safety-interlock subsystem: platform-level e-stop on the command path.

When an interlock is composed onto a platform and engaged, ALL actuation
through that platform's single command path is refused except commands
addressed to the safety subsystem itself (so it can be released).

Enforcement is centralized in ``CommandBus.execute``
(``agents.commands``): agents, UCL controllers, and scenario scripts all
issue commands through that one method, so there is exactly one gate
because there is exactly one command path.
"""

from __future__ import annotations

from typing import Any, Dict

from agents.subsystems.base import Subsystem, command


class SafetyInterlockSubsystem(Subsystem):
    """E-stop / release plus configurable operating-envelope limits."""

    name = "safety"

    def __init__(self) -> None:
        super().__init__()
        self.estopped = False
        self.limits: Dict[str, float] = {}
        self.engagements = 0

    @command("engage_estop")
    def engage_estop(self, reason: str = "operator") -> Dict[str, Any]:
        if not self.estopped:
            self.estopped = True
            self.engagements += 1
            self.record_fault(f"e-stop engaged ({reason})")
        return {"estopped": True, "reason": reason}

    @command("release_estop")
    def release_estop(self) -> bool:
        self.estopped = False
        return True

    @command("set_limit")
    def set_limit(self, key: str = "", value: float = 0.0) -> float:
        if not key:
            raise RuntimeError("limit key required")
        value = float(value)
        if value < 0:
            raise RuntimeError("limits must be non-negative")
        self.limits[key] = value
        return value

    @command("get_limits")
    def get_limits(self) -> Dict[str, float]:
        return dict(sorted(self.limits.items()))

    @property
    def allows_actuation(self) -> bool:
        return not self.estopped

    def status(self) -> Dict[str, Any]:
        return {**super().status(),
                "estopped": self.estopped,
                "engagements": self.engagements,
                "limits": dict(sorted(self.limits.items()))}
