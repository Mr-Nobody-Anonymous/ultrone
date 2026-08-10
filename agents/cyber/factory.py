# Copyright (c) Ultrone Contributors. All rights reserved.
"""Factory functions for cyber domain agents."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

from agents.cyber.recon_agent import ReconAgent
from agents.cyber.exploit_agent import ExploitAgent
from agents.cyber.defend_agent import DefendAgent
from agents.cyber.base import CyberAgent
from agents.config import CyberAgentConfig
from agents.registry import register_agent, AgentRegistry
from data.entities import DomainType

logger = logging.getLogger("Ultrone.Agents.Cyber.Factory")


def register_cyber_agents(registry: Optional[AgentRegistry] = None) -> None:
    """
    Register all cyber domain agent types.
    
    Args:
        registry: Agent registry to register with (uses default if None)
    """
    if registry is None:
        from agents.registry import _default_registry
        registry = _default_registry
    
    registry.register(
        agent_type="recon",
        agent_class=ReconAgent,
        domain=DomainType.CYBER,
        description="Cyber reconnaissance for network scanning and surveillance",
        config_class=CyberAgentConfig,
        capabilities=["sense", "communicate"],
    )
    
    registry.register(
        agent_type="exploit",
        agent_class=ExploitAgent,
        domain=DomainType.CYBER,
        description="Cyber exploitation for offensive operations",
        config_class=CyberAgentConfig,
        capabilities=["sense", "communicate"],
    )
    
    registry.register(
        agent_type="defense",
        agent_class=DefendAgent,
        domain=DomainType.CYBER,
        description="Cyber defense for network protection",
        config_class=CyberAgentConfig,
        capabilities=["sense", "communicate"],
    )
    
    logger.info("Cyber domain agents registered")


def create_recon(
    unit_id: str,
    position: Tuple[float, float, float],
    team: str = "blue",
    config: Optional[CyberAgentConfig] = None,
    **kwargs: Any,
) -> ReconAgent:
    """Create a cyber recon agent."""
    return ReconAgent(
        unit_id=unit_id,
        position=position,
        team=team,
        **kwargs,
    )


def create_exploit(
    unit_id: str,
    position: Tuple[float, float, float],
    team: str = "blue",
    config: Optional[CyberAgentConfig] = None,
    **kwargs: Any,
) -> ExploitAgent:
    """Create a cyber exploit agent."""
    return ExploitAgent(
        unit_id=unit_id,
        position=position,
        team=team,
        **kwargs,
    )


def create_defense(
    unit_id: str,
    position: Tuple[float, float, float],
    team: str = "blue",
    config: Optional[CyberAgentConfig] = None,
    **kwargs: Any,
) -> DefendAgent:
    """Create a cyber defense agent."""
    return DefendAgent(
        unit_id=unit_id,
        position=position,
        team=team,
        **kwargs,
    )


# Auto-register on import
register_cyber_agents()