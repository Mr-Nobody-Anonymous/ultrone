# Copyright (c) Ultrone Contributors. All rights reserved.
"""Resource subsystem: generic named resource pools with capacity limits."""

from __future__ import annotations

from typing import Any, Dict, Optional

from agents.subsystems.base import Subsystem, command


class ResourceSubsystem(Subsystem):
    """Generic named resource pools with transfer and capacity limits."""

    name = "resource"

    def __init__(self, capacities: Optional[Dict[str, float]] = None) -> None:
        super().__init__()
        self.capacities = dict(capacities or {"water": 100.0})
        self.levels: Dict[str, float] = {
            k: v for k, v in self.capacities.items()}

    @command("transfer_out")
    def transfer_out(self, resource: str = "", amount: float = 0.0
                     ) -> float:
        level = self.levels.get(resource, 0.0)
        moved = min(level, max(0.0, amount))
        self.levels[resource] = level - moved
        return round(moved, 3)

    @command("transfer_in")
    def transfer_in(self, resource: str = "", amount: float = 0.0
                    ) -> float:
        cap = self.capacities.get(resource)
        if cap is None:
            raise RuntimeError(f"unknown resource '{resource}'")
        accepted = min(float(amount),
                       max(0.0, cap - self.levels.get(resource, 0.0)))
        self.levels[resource] = self.levels.get(resource, 0.0) + accepted
        return round(accepted, 3)

    def status(self) -> Dict[str, Any]:
        return {**super().status(),
                "levels": {k: round(v, 3)
                           for k, v in sorted(self.levels.items())}}
