# Copyright (c) Ultrone Contributors. All rights reserved.
"""Industrial plant node: batch production with thermal management."""

from __future__ import annotations

from typing import Any, Dict

from agents.commands import Command
from agents.infrastructure.base import InfrastructureNodeAgent


class IndustrialPlantAgent(InfrastructureNodeAgent):
    """Simulated plant: raw material in, thermal-managed production out."""

    MACHINE_KIND = "industrial_plant"

    def _build_subsystems(self) -> list:
        from agents.subsystems.computing import (ComputeSubsystem,
                                                 ConfigurationSubsystem,
                                                 MonitoringSubsystem)
        from agents.subsystems.platform_subsystems import (
            AutonomySubsystem, CommunicationSubsystem, HealthSubsystem,
            ResourceSubsystem, ThermalSubsystem)

        return [
            ComputeSubsystem(),
            ThermalSubsystem(ambient=25.0, overheat_limit=80.0),
            ResourceSubsystem(capacities={"raw_material": 200.0}),
            MonitoringSubsystem(),
            ConfigurationSubsystem(allowed_keys=("batch_size", "safety_mode")),
            CommunicationSubsystem(),
            HealthSubsystem(wear_rate=0.006),
            AutonomySubsystem(),
        ]

    def execute_mission(self, mission: Dict[str, Any]) -> Dict[str, Any]:
        units = max(0, int(mission.get("units", 5)))
        self.execute(Command("thermal", "set_cooling", {"on": True}))
        produced = 0
        for _ in range(units):
            drawn = self.execute(Command("resource", "transfer_out",
                                         {"resource": "raw_material",
                                          "amount": 1.0}))
            if float(drawn.value or 0.0) < 1.0:
                self.execute(Command("monitoring", "raise_alert",
                                     {"kind": "material_starved",
                                      "severity": 0.8}))
                break
            thermal = self.get_subsystem("thermal")
            thermal.add_heat(3.0)
            if thermal.is_overheating():
                self.execute(Command("monitoring", "raise_alert",
                                     {"kind": "overheat",
                                      "severity": 0.9}))
            produced += 1
        return {
            "success": produced == units,
            "units_requested": units,
            "units_produced": produced,
            "overheating": self.get_subsystem("thermal").is_overheating(),
        }
