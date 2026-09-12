# Copyright (c) Ultrone Contributors. All rights reserved.
"""Factory functions for land domain agents."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

from agents.land.tank_agent import TankAgent
from agents.land.infantry_agent import InfantryAgent
from agents.land.mobile_missile_agent import MobileMissileAgent
from agents.land.base import LandAgent
from agents.config import LandAgentConfig
from agents.registry import register_agent, AgentRegistry
from data.entities import DomainType

logger = logging.getLogger("Ultrone.Agents.Land.Factory")


def register_land_agents(registry: Optional[AgentRegistry] = None) -> None:
    """
    Register all land domain agent types.
    
    Args:
        registry: Agent registry to register with (uses default if None)
    """
    if registry is None:
        from agents.registry import _default_registry
        registry = _default_registry
    
    registry.register(
        agent_type="tank",
        agent_class=TankAgent,
        domain=DomainType.LAND,
        description="Armored fighting vehicle for direct fire engagement",
        config_class=LandAgentConfig,
        capabilities=["sense", "move", "engage"],
    )
    
    registry.register(
        agent_type="infantry",
        agent_class=InfantryAgent,
        domain=DomainType.LAND,
        description="Infantry squad for dismounted operations",
        config_class=LandAgentConfig,
        capabilities=["sense", "move", "engage"],
    )
    
    registry.register(
        agent_type="mobile_missile",
        agent_class=MobileMissileAgent,
        domain=DomainType.LAND,
        description="Mobile surface-to-air missile system",
        config_class=LandAgentConfig,
        capabilities=["sense", "move", "engage"],
    )
    
    logger.info("Land domain agents registered")


def create_tank(
    unit_id: str,
    position: Tuple[float, float, float],
    team: str = "blue",
    config: Optional[LandAgentConfig] = None,
    **kwargs: Any,
) -> TankAgent:
    """Create a tank agent."""
    return TankAgent(
        unit_id=unit_id,
        position=position,
        team=team,
        **kwargs,
    )


def create_infantry(
    unit_id: str,
    position: Tuple[float, float, float],
    team: str = "blue",
    config: Optional[LandAgentConfig] = None,
    **kwargs: Any,
) -> InfantryAgent:
    """Create an infantry agent."""
    return InfantryAgent(
        unit_id=unit_id,
        position=position,
        team=team,
        **kwargs,
    )


def create_mobile_missile(
    unit_id: str,
    position: Tuple[float, float, float],
    team: str = "blue",
    config: Optional[LandAgentConfig] = None,
    **kwargs: Any,
) -> MobileMissileAgent:
    """Create a mobile missile agent."""
    return MobileMissileAgent(
        unit_id=unit_id,
        position=position,
        team=team,
        **kwargs,
    )


# Auto-register on import
register_land_agents()