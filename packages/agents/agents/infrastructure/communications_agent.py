# Copyright (c) Ultrone Contributors. All rights reserved.
"""Communication backbone node: link management and fan-out delivery."""

from __future__ import annotations

from typing import Any, Dict, List

from agents.commands import Command
from agents.infrastructure.base import InfrastructureNodeAgent


class CommsInfrastructureAgent(InfrastructureNodeAgent):
    """Simulated backbone router: connect, relay, report delivery."""

    MACHINE_KIND = "comms_infrastructure"

    def _build_subsystems(self) -> list:
        from agents.subsystems.computing import (
            ConfigurationSubsystem, MonitoringSubsystem,
            NetworkInterfaceSubsystem)
        from agents.subsystems.platform_subsystems import (
            CommunicationSubsystem, HealthSubsystem, PowerSubsystem)

        return [
            NetworkInterfaceSubsystem(bandwidth_mbps=250.0),
            CommunicationSubsystem(bandwidth_units=20),
            PowerSubsystem(),
            MonitoringSubsystem(),
            ConfigurationSubsystem(allowed_keys=("routing_policy",
                                                 "log_level")),
            HealthSubsystem(wear_rate=0.004),
        ]

    def execute_mission(self, mission: Dict[str, Any]) -> Dict[str, Any]:
        recipients: List[str] = [str(r) for r in
                                 mission.get("recipients", [])]
        content = mission.get("message")
        if not recipients:
            return {"success": False, "reason": "no recipients"}
        linked = self.execute(Command("network", "connect",
                                      {"reserve_mbps": 50.0}))
        if not linked.success:
            return {"success": False, "reason": linked.reason}
        delivered = 0
        for recipient in recipients:
            sent = self.execute(Command("communications", "transmit",
                                        {"recipient": recipient,
                                         "content": content}))
            if sent.success:
                delivered += 1
        comms = self.get_subsystem("communications")
        drained = comms.drain_outbox()
        self.execute(Command("network", "disconnect"))
        return {
            "success": delivered == len(recipients)
                       and len(drained) == len(recipients),
            "recipients_total": len(recipients),
            "accepted": delivered,
            "relayed": len(drained),
        }
