# Copyright (c) Ultrone Contributors. All rights reserved.
"""Agent registry and factory for creating domain-specific agents."""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional, Type
from dataclasses import dataclass, field

from data.entities import DomainType
from agents.config import AgentConfig, AgentStatus

logger = logging.getLogger("Ultrone.Agents.Registry")


class AgentRegistryError(Exception):
    """Base exception for agent registry errors."""
    pass


class AgentConfigurationError(AgentRegistryError):
    """Raised when agent configuration is invalid."""
    pass


class InvalidAgentTypeError(AgentRegistryError):
    """Raised when an unknown agent type is requested."""
    pass


@dataclass
class AgentRegistration:
    """Registration metadata for an agent type."""
    agent_class: Type[Any]
    domain: DomainType
    description: str
    config_class: Optional[Type[AgentConfig]] = None
    capabilities: List[str] = field(default_factory=list)


class AgentRegistry:
    """
    Central registry for agent types.
    
    Supports plugin-style registration of new agent types without modifying
    the base architecture.
    """
    
    def __init__(self) -> None:
        self._agents: Dict[str, AgentRegistration] = {}
        self._domain_index: Dict[DomainType, List[str]] = {}
        self._factories: Dict[str, Callable] = {}
    
    def register(
        self,
        agent_type: str,
        agent_class: Type[Any],
        domain: DomainType,
        description: str = "",
        config_class: Optional[Type[AgentConfig]] = None,
        capabilities: Optional[List[str]] = None,
    ) -> None:
        """
        Register an agent type.
        
        Args:
            agent_type: Unique identifier for the agent type (e.g., "drone", "tank")
            agent_class: The agent class
            domain: Domain this agent belongs to
            description: Human-readable description
            config_class: Configuration dataclass for this agent type
            capabilities: List of capability names
        """
        if agent_type in self._agents:
            logger.warning(f"Agent type '{agent_type}' already registered. Overwriting.")
        
        registration = AgentRegistration(
            agent_class=agent_class,
            domain=domain,
            description=description,
            config_class=config_class,
            capabilities=capabilities or [],
        )
        
        self._agents[agent_type] = registration
        
        # Update domain index
        if domain not in self._domain_index:
            self._domain_index[domain] = []
        if agent_type not in self._domain_index[domain]:
            self._domain_index[domain].append(agent_type)
        
        logger.info(f"Registered agent type: {agent_type} (domain={domain.value})")
    
    def unregister(self, agent_type: str) -> None:
        """Remove an agent type from the registry."""
        if agent_type not in self._agents:
            raise InvalidAgentTypeError(f"Agent type '{agent_type}' not registered")
        
        registration = self._agents[agent_type]
        domain = registration.domain
        
        del self._agents[agent_type]
        
        if domain in self._domain_index and agent_type in self._domain_index[domain]:
            self._domain_index[domain].remove(agent_type)
        
        logger.info(f"Unregistered agent type: {agent_type}")
    
    def get(self, agent_type: str) -> AgentRegistration:
        """Get registration info for an agent type."""
        if agent_type not in self._agents:
            raise InvalidAgentTypeError(
                f"Unknown agent type: '{agent_type}'. "
                f"Registered types: {list(self._agents.keys())}"
            )
        return self._agents[agent_type]
    
    def get_agent_class(self, agent_type: str) -> Type[Any]:
        """Get the class for an agent type."""
        return self.get(agent_type).agent_class
    
    def list_agent_types(self, domain: Optional[DomainType] = None) -> List[str]:
        """
        List all registered agent types.
        
        Args:
            domain: Optional domain filter
            
        Returns:
            List of agent type identifiers
        """
        if domain is None:
            return list(self._agents.keys())
        
        if domain not in self._domain_index:
            return []
        
        return list(self._domain_index[domain])
    
    def list_domains(self) -> List[DomainType]:
        """List all domains that have registered agents."""
        return list(self._domain_index.keys())
    
    def get_capabilities(self, agent_type: str) -> List[str]:
        """Get capabilities for an agent type."""
        return self.get(agent_type).capabilities
    
    def has_type(self, agent_type: str) -> bool:
        """Check if an agent type is registered."""
        return agent_type in self._agents
    
    def clear(self) -> None:
        """Remove all registrations."""
        self._agents.clear()
        self._domain_index.clear()
        self._factories.clear()


class AgentFactory:
    """
    Factory for creating agent instances.
    
    Uses the registry to instantiate agents with proper configuration.
    """
    
    def __init__(self, registry: Optional[AgentRegistry] = None) -> None:
        self.registry = registry or _default_registry
    
    def create(
        self,
        agent_type: str,
        unit_id: str,
        position: tuple,
        team: str = "blue",
        config: Optional[AgentConfig] = None,
        **kwargs,
    ) -> Any:
        """
        Create an agent instance.
        
        Args:
            agent_type: Type of agent to create
            unit_id: Unique identifier for the agent
            position: Initial position (x, y, z)
            team: Team affiliation
            config: Optional configuration object
            **kwargs: Additional arguments passed to agent constructor
            
        Returns:
            Agent instance
            
        Raises:
            InvalidAgentTypeError: If agent type is not registered
            AgentConfigurationError: If configuration is invalid
        """
        try:
            registration = self.registry.get(agent_type)
        except InvalidAgentTypeError:
            raise InvalidAgentTypeError(
                f"Cannot create agent of unknown type '{agent_type}'. "
                f"Available types: {self.registry.list_agent_types()}"
            )
        
        # Build configuration
        if config is None:
            if registration.config_class:
                config = registration.config_class(
                    agent_id=unit_id,
                    team=team,
                    domain=registration.domain,
                )
            else:
                from agents.config import get_config_for_domain
                config = get_config_for_domain(registration.domain)
                config.agent_id = unit_id
                config.team = team
        else:
            # Ensure consistency
            config.agent_id = unit_id
            config.team = team
            config.domain = registration.domain
        
        # Validate configuration
        try:
            config.validate()
        except (ValueError, AttributeError) as e:
            raise AgentConfigurationError(
                f"Invalid configuration for {agent_type}: {e}"
            )
        
        # Create agent instance
        try:
            agent = registration.agent_class(
                unit_id=unit_id,
                position=position,
                team=team,
                config=config,
                **kwargs,
            )
            logger.info(f"Created {agent_type} agent: {unit_id}")
            return agent
        except Exception as e:
            raise AgentConfigurationError(
                f"Failed to instantiate {agent_type}: {e}"
            )
    
    def create_from_config(
        self,
        agent_type: str,
        config: AgentConfig,
        **kwargs,
    ) -> Any:
        """Create an agent from a configuration object."""
        if not config.agent_id:
            raise AgentConfigurationError("config.agent_id must be set")
        
        return self.create(
            agent_type=agent_type,
            unit_id=config.agent_id,
            position=kwargs.get("position", (0.0, 0.0, 0.0)),
            team=config.team,
            config=config,
            **{k: v for k, v in kwargs.items() if k != "position"},
        )
    
    def register_factory(self, agent_type: str, factory: Callable) -> None:
        """Register a custom factory function for an agent type."""
        self._factories[agent_type] = factory
        logger.debug(f"Registered custom factory for {agent_type}")
    
    def create_batch(
        self,
        specifications: List[Dict[str, Any]],
    ) -> List[Any]:
        """
        Create multiple agents from a list of specifications.
        
        Args:
            specifications: List of dicts with keys: agent_type, unit_id, position, team, config
            
        Returns:
            List of agent instances
        """
        agents = []
        for spec in specifications:
            agent = self.create(
                agent_type=spec["agent_type"],
                unit_id=spec["unit_id"],
                position=spec.get("position", (0.0, 0.0, 0.0)),
                team=spec.get("team", "blue"),
                config=spec.get("config"),
            )
            agents.append(agent)
        return agents


# Global default registry
_default_registry = AgentRegistry()


def register_agent(
    agent_type: str,
    agent_class: Type[Any],
    domain: DomainType,
    description: str = "",
    config_class: Optional[Type[AgentConfig]] = None,
    capabilities: Optional[List[str]] = None,
) -> None:
    """Register an agent type in the global registry."""
    _default_registry.register(
        agent_type=agent_type,
        agent_class=agent_class,
        domain=domain,
        description=description,
        config_class=config_class,
        capabilities=capabilities,
    )


def create_agent(
    agent_type: str,
    unit_id: str,
    position: tuple,
    team: str = "blue",
    config: Optional[AgentConfig] = None,
    **kwargs,
) -> Any:
    """Create an agent using the global registry."""
    factory = AgentFactory(_default_registry)
    return factory.create(
        agent_type=agent_type,
        unit_id=unit_id,
        position=position,
        team=team,
        config=config,
        **kwargs,
    )


def list_agent_types(domain: Optional[DomainType] = None) -> List[str]:
    """List all registered agent types."""
    return _default_registry.list_agent_types(domain)


def get_agent_class(agent_type: str) -> Type[Any]:
    """Get the class for a registered agent type."""
    return _default_registry.get_agent_class(agent_type)


# Import base agent for type hints
from agents.base_agent import BaseAgent