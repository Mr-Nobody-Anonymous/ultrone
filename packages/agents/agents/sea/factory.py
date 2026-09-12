# Copyright (c) Ultrone Contributors. All rights reserved.
"""Factory functions for sea domain agents."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

from agents.sea.vessel_agent import VesselAgent
from agents.sea.submarine_agent import SubmarineAgent
from agents.sea.naval_air_agent import NavalAirAgent
from agents.sea.base import SeaAgent
from agents.config import SeaAgentConfig
from agents.registry import register_agent, AgentRegistry
from data.entities import DomainType

logger = logging.getLogger("Ultrone.Agents.Sea.Factory")


def register_sea_agents(registry: Optional[AgentRegistry] = None) -> None:
    """
    Register all sea domain agent types.
    
    Args:
        registry: Agent registry to register with (uses default if None)
    """
    if registry is None:
        from agents.registry import _default_registry
        registry = _default_registry
    
    registry.register(
        agent_type="vessel",
        agent_class=VesselAgent,
        domain=DomainType.SEA,
        description="Surface vessel for maritime operations",
        config_class=SeaAgentConfig,
        capabilities=["sense", "move", "engage"],
    )
    
    registry.register(
        agent_type="submarine",
        agent_class=SubmarineAgent,
        domain=DomainType.SEA,
        description="Submarine for underwater warfare and stealth operations",
        config_class=SeaAgentConfig,
        capabilities=["sense", "move", "engage"],
    )
    
    registry.register(
        agent_type="naval_air",
        agent_class=NavalAirAgent,
        domain=DomainType.SEA,
        description="Naval aviation for carrier-based operations",
        config_class=SeaAgentConfig,
        capabilities=["sense", "move", "engage"],
    )
    
    logger.info("Sea domain agents registered")


def create_vessel(
    unit_id: str,
    position: Tuple[float, float, float],
    team: str = "blue",
    config: Optional[SeaAgentConfig] = None,
    **kwargs: Any,
) -> VesselAgent:
    """Create a vessel agent."""
    return VesselAgent(
        unit_id=unit_id,
        position=position,
        team=team,
        **kwargs,
    )


def create_submarine(
    unit_id: str,
    position: Tuple[float, float, float],
    team: str = "blue",
    config: Optional[SeaAgentConfig] = None,
    **kwargs: Any,
) -> SubmarineAgent:
    """Create a submarine agent."""
    return SubmarineAgent(
        unit_id=unit_id,
        position=position,
        team=team,
        **kwargs,
    )


def create_naval_air(
    unit_id: str,
    position: Tuple[float, float, float],
    team: str = "blue",
    config: Optional[SeaAgentConfig] = None,
    **kwargs: Any,
) -> NavalAirAgent:
    """Create a naval air agent."""
    return NavalAirAgent(
        unit_id=unit_id,
        position=position,
        team=team,
        **kwargs,
    )


# Auto-register on import
register_sea_agents()