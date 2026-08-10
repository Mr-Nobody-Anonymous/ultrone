# Copyright (c) Ultrone Contributors. All rights reserved.
"""Factory functions for air domain agents."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

from agents.air.drone_agent import DroneAgent
from agents.air.fighter_agent import FighterAgent
from agents.air.missile_agent import MissileAgent
from agents.air.base import AirAgent
from agents.config import AirAgentConfig
from agents.registry import register_agent, AgentRegistry
from data.entities import DomainType

logger = logging.getLogger("Ultrone.Agents.Air.Factory")


def register_air_agents(registry: Optional[AgentRegistry] = None) -> None:
    """
    Register all air domain agent types.
    
    Args:
        registry: Agent registry to register with (uses default if None)
    """
    if registry is None:
        from agents.registry import _default_registry
        registry = _default_registry
    
    registry.register(
        agent_type="drone",
        agent_class=DroneAgent,
        domain=DomainType.AIR,
        description="Unmanned Aerial Vehicle for ISR and strike",
        config_class=AirAgentConfig,
        capabilities=["sense", "move", "engage", "recon"],
    )
    
    registry.register(
        agent_type="fighter",
        agent_class=FighterAgent,
        domain=DomainType.AIR,
        description="Fighter aircraft for air superiority and interception",
        config_class=AirAgentConfig,
        capabilities=["sense", "move", "engage"],
    )
    
    registry.register(
        agent_type="missile",
        agent_class=MissileAgent,
        domain=DomainType.AIR,
        description="Air-to-air or air-to-ground missile",
        config_class=AirAgentConfig,
        capabilities=["move", "engage"],
    )
    
    logger.info("Air domain agents registered")


def create_drone(
    unit_id: str,
    position: Tuple[float, float, float],
    team: str = "blue",
    config: Optional[AirAgentConfig] = None,
    **kwargs: Any,
) -> DroneAgent:
    """
    Create a drone agent.
    
    Args:
        unit_id: Unique identifier
        position: (x, y, z) position tuple
        team: Team affiliation
        config: Optional configuration
        **kwargs: Additional arguments
        
    Returns:
        DroneAgent instance
    """
    return DroneAgent(
        unit_id=unit_id,
        position=position,
        team=team,
        **kwargs,
    )


def create_fighter(
    unit_id: str,
    position: Tuple[float, float, float],
    team: str = "blue",
    config: Optional[AirAgentConfig] = None,
    **kwargs: Any,
) -> FighterAgent:
    """
    Create a fighter agent.
    
    Args:
        unit_id: Unique identifier
        position: (x, y, z) position tuple
        team: Team affiliation
        config: Optional configuration
        **kwargs: Additional arguments
        
    Returns:
        FighterAgent instance
    """
    return FighterAgent(
        unit_id=unit_id,
        position=position,
        team=team,
        **kwargs,
    )


def create_missile(
    unit_id: str,
    position: Tuple[float, float, float],
    target_id: str,
    team: str = "blue",
    config: Optional[AirAgentConfig] = None,
    **kwargs: Any,
) -> MissileAgent:
    """
    Create a missile agent.
    
    Args:
        unit_id: Unique identifier
        position: (x, y, z) position tuple
        target_id: Target unit identifier
        team: Team affiliation
        config: Optional configuration
        **kwargs: Additional arguments
        
    Returns:
        MissileAgent instance
    """
    return MissileAgent(
        unit_id=unit_id,
        position=position,
        target_id=target_id,
        team=team,
        **kwargs,
    )


# Auto-register on import
register_air_agents()