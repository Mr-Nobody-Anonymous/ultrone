# Copyright (c) Ultrone Contributors. All rights reserved.
"""Power-grid node: dispatch generation against a demand profile."""

from __future__ import annotations

from typing import Any, Dict

from agents.commands import Command
from agents.infrastructure.base import InfrastructureNodeAgent


class PowerGridAgent(InfrastructureNodeAgent):
    """Simulated microgrid node balancing stored energy against demand."""

    MACHINE_KIND = "power_grid"

    def _build_subsystems(self) -> list:
        from agents.subsystems.computing import (ConfigurationSubsystem,
                                                 MonitoringSubsystem)
        from agents.subsystems.platform_subsystems import (
            CommunicationSubsystem, HealthSubsystem, PowerSubsystem,
            ResourceSubsystem)

        return [
            PowerSubsystem(battery_pct=100.0, generation_kw=8.0),
            ResourceSubsystem(capacities={"stored_energy": 500.0}),
            MonitoringSubsystem(),
            ConfigurationSubsystem(allowed_keys=("dispatch_mode",
                                                 "reserve_pct")),
            CommunicationSubsystem(),
            HealthSubsystem(wear_rate=0.005),
        ]

    def execute_mission(self, mission: Dict[str, Any]) -> Dict[str, Any]:
        demand_kw = max(0.0, float(mission.get("demand_kw", 5.0)))
        self.execute(Command("power", "set_load", {"kw": demand_kw}))
        # Draw one unit of stored energy per kW of demand this cycle.
        drawn = self.execute(Command("resource", "transfer_out",
                                     {"resource": "stored_energy",
                                      "amount": demand_kw}))
        supplied = float(drawn.value or 0.0)
        shortfall = demand_kw - supplied
        if shortfall > 0.01:
            self.execute(Command("monitoring", "raise_alert",
                                 {"kind": "supply_shortfall",
                                  "severity": min(1.0, shortfall / 10.0)}))
        status = self.execute(Command("power", "recharge", {"pct": 1.0}))
        return {
            "success": shortfall <= 0.01,
            "demand_kw": round(demand_kw, 3),
            "supplied_kw": round(supplied, 3),
            "battery_pct": round(float(status.value or 0.0), 3),
        }
