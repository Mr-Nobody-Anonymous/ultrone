# Copyright (c) Ultrone Contributors. All rights reserved.
"""Infrastructure node agents composed from simulated subsystems.

Stationary simulated infrastructure -- power grids, communication
backbones, industrial plants, transit networks -- modeled as subsystem
compositions driven through the structured Command interface.

Hard design rules (enforced by test):

1. Capabilities are ``[SENSE, COMMUNICATE]`` only -- no ENGAGE anywhere.
2. All actuation flows through the node's CommandBus; out-of-envelope
   commands fail cleanly via CommandResult.
3. Everything operates sandboxed simulation state exclusively. These
   nodes model infrastructure control surfaces for research; they have no
   connection to real-world systems.
"""

from __future__ import annotations

from typing import Any, Dict, List

from agents.base_agent import AgentCapability
from agents.platform_agent import SubsystemControlledAgent
from data.entities import DomainType

#: Infrastructure nodes sense and report; they never engage.
INFRA_CAPABILITIES = [AgentCapability.SENSE, AgentCapability.COMMUNICATE]

INFRA_LEAVES = ("routing", "transmit", "receive", "distribution",
                "storage", "diagnostics", "faults", "task_execution")


class InfrastructureNodeAgent(SubsystemControlledAgent):
    """Common wiring for every infrastructure-domain node agent."""

    MACHINE_KIND = "infrastructure_node"

    def __init__(self, unit_id: str, **kwargs: Any) -> None:
        kwargs.setdefault("position", (0.0, 0.0, 0.0))
        kwargs.setdefault("team", "civilian")
        super().__init__(
            unit_id=unit_id,
            domain=DomainType.GENERAL,
            unit_type=self.MACHINE_KIND,
            capabilities=list(INFRA_CAPABILITIES),
            **kwargs,
        )

    def _capability_leaves(self) -> tuple:
        return INFRA_LEAVES

    # -- framework --------------------------------------------------------- #
    def take_turn(self, world_state: Any,
                  messages: List[Any]) -> List[Any]:
        tick = world_state.get("tick", 0) if isinstance(world_state, dict) else 0
        self.tick_platform(tick)
        replies: List[Any] = []
        for message in messages:
            reply = self.handle_message(message)
            if reply is not None:
                replies.append(reply)
        return replies
