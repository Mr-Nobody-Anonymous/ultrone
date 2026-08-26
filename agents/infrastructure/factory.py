# Copyright (c) Ultrone Contributors. All rights reserved.
"""Factory and registry wiring for infrastructure-domain node agents."""

from __future__ import annotations

from typing import Optional

from agents.infrastructure.communications_agent import (
    CommsInfrastructureAgent)
from agents.infrastructure.industrial_agent import IndustrialPlantAgent
from agents.infrastructure.power_agent import PowerGridAgent
from agents.infrastructure.transportation_agent import TransitNetworkAgent
from agents.registry import AgentRegistry, _default_registry
from data.entities import DomainType


def register_infrastructure_agents(registry: Optional[AgentRegistry] = None
                                   ) -> None:
    """Register every infrastructure node with a global/default registry."""
    reg = registry or _default_registry
    registrations = (
        ("infra_power", PowerGridAgent,
         "Microgrid dispatch node (simulation-only; non-weaponized)"),
        ("infra_comms", CommsInfrastructureAgent,
         "Backbone relay node (simulation-only; non-weaponized)"),
        ("infra_industrial", IndustrialPlantAgent,
         "Batch production plant (simulation-only; non-weaponized)"),
        ("infra_transit", TransitNetworkAgent,
         "Scheduled transit segment (simulation-only; non-weaponized)"),
    )
    for agent_type, agent_class, description in registrations:
        reg.register(
            agent_type=agent_type,
            agent_class=agent_class,
            domain=DomainType.GENERAL,
            description=description,
        )


def create_power_grid(unit_id: str, **kwargs) -> PowerGridAgent:
    return PowerGridAgent(unit_id=unit_id, **kwargs)


def create_comms_node(unit_id: str, **kwargs) -> CommsInfrastructureAgent:
    return CommsInfrastructureAgent(unit_id=unit_id, **kwargs)


def create_industrial_plant(unit_id: str, **kwargs) -> IndustrialPlantAgent:
    return IndustrialPlantAgent(unit_id=unit_id, **kwargs)


def create_transit_segment(unit_id: str, **kwargs) -> TransitNetworkAgent:
    return TransitNetworkAgent(unit_id=unit_id, **kwargs)


# Auto-register on import (mirrors the other domain factories).
register_infrastructure_agents()
