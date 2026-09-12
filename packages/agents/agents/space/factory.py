# Copyright (c) Ultrone Contributors. All rights reserved.
"""Factory functions for space domain agents."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

from agents.space.satellite_agent import SatelliteAgent
from agents.space.orbital_agent import OrbitalAgent
from agents.space.space_weapon_agent import SpaceWeaponAgent
from agents.space.base import SpaceAgent
from agents.config import SpaceAgentConfig
from agents.registry import register_agent, AgentRegistry
from data.entities import DomainType

logger = logging.getLogger("Ultrone.Agents.Space.Factory")


def register_space_agents(registry: Optional[AgentRegistry] = None) -> None:
    """
    Register all space domain agent types.
    
    Args:
        registry: Agent registry to register with (uses default if None)
    """
    if registry is None:
        from agents.registry import _default_registry
        registry = _default_registry
    
    registry.register(
        agent_type="satellite",
        agent_class=SatelliteAgent,
        domain=DomainType.SPACE,
        description="Satellite for orbital ISR and communications",
        config_class=SpaceAgentConfig,
        capabilities=["sense", "move", "communicate"],
    )
    
    registry.register(
        agent_type="orbital",
        agent_class=OrbitalAgent,
        domain=DomainType.SPACE,
        description="Orbital vehicle for space maneuver and rendezvous",
        config_class=SpaceAgentConfig,
        capabilities=["sense", "move", "communicate"],
    )
    
    registry.register(
        agent_type="space_weapon",
        agent_class=SpaceWeaponAgent,
        domain=DomainType.SPACE,
        description="Space-based weapon system for orbital defense",
        config_class=SpaceAgentConfig,
        capabilities=["sense", "move", "engage"],
    )
    
    logger.info("Space domain agents registered")


def create_satellite(
    unit_id: str,
    position: Tuple[float, float, float],
    team: str = "blue",
    config: Optional[SpaceAgentConfig] = None,
    **kwargs: Any,
) -> SatelliteAgent:
    """Create a satellite agent."""
    return SatelliteAgent(
        unit_id=unit_id,
        position=position,
        team=team,
        **kwargs,
    )


def create_orbital(
    unit_id: str,
    position: Tuple[float, float, float],
    team: str = "blue",
    config: Optional[SpaceAgentConfig] = None,
    **kwargs: Any,
) -> OrbitalAgent:
    """Create an orbital agent."""
    return OrbitalAgent(
        unit_id=unit_id,
        position=position,
        team=team,
        **kwargs,
    )


def create_space_weapon(
    unit_id: str,
    position: Tuple[float, float, float],
    team: str = "blue",
    config: Optional[SpaceAgentConfig] = None,
    **kwargs: Any,
) -> SpaceWeaponAgent:
    """Create a space weapon agent."""
    return SpaceWeaponAgent(
        unit_id=unit_id,
        position=position,
        team=team,
        **kwargs,
    )


# Auto-register on import
register_space_agents()