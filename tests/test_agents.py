# Copyright (c) Ultrone Contributors. All rights reserved.
"""Comprehensive tests for the agents package."""

import pytest
import copy
from typing import Any

from agents.base_agent import BaseAgent, AgentCapability
from agents.config import (
    AgentConfig, AgentStatus, AirAgentConfig, LandAgentConfig,
    SeaAgentConfig, SpaceAgentConfig, CyberAgentConfig
)
from agents.registry import AgentRegistry, AgentFactory, create_agent, register_agent
from agents.air.base import AirAgent
from agents.land.base import LandAgent
from agents.sea.base import SeaAgent
from agents.space.base import SpaceAgent
from agents.cyber.base import CyberAgent
from data.entities import DomainType, AgentState


class TestBaseAgent:
    """Test BaseAgent functionality."""
    
    def test_base_agent_initialization(self):
        """Test basic agent initialization."""
        agent = BaseAgent(
            unit_id="test-agent-1",
            domain=DomainType.LAND,
            unit_type="test_unit",
            position=(10.0, 20.0, 0.0),
            team="blue",
        )
        assert agent.unit.unit_id == "test-agent-1"
        assert agent.unit.domain == DomainType.LAND
        assert agent.unit.team == "blue"
        assert agent.unit.position == (10.0, 20.0, 0.0)
    
    def test_agent_capabilities(self):
        """Test agent capabilities."""
        agent = BaseAgent(
            unit_id="test-1",
            domain=DomainType.AIR,
            unit_type="drone",
            position=(0.0, 0.0, 100.0),
            capabilities=[AgentCapability.SENSE, AgentCapability.MOVE],
        )
        assert agent.can_perform(AgentCapability.SENSE) is True
        assert agent.can_perform(AgentCapability.MOVE) is True
        assert agent.can_perform(AgentCapability.ENGAGE) is False
    
    def test_agent_position_update(self):
        """Test position updates."""
        agent = BaseAgent(
            unit_id="test-1",
            domain=DomainType.LAND,
            unit_type="tank",
            position=(0.0, 0.0, 0.0),
        )
        agent.set_position(100.0, 200.0, 0.0)
        assert agent.unit.position == (100.0, 200.0, 0.0)
    
    def test_agent_damage(self):
        """Test damage application."""
        agent = BaseAgent(
            unit_id="test-1",
            domain=DomainType.LAND,
            unit_type="tank",
            position=(0.0, 0.0, 0.0),
        )
        assert agent.unit.health == 1.0
        destroyed = agent.take_damage(0.5)
        assert destroyed is False
        assert agent.unit.health == 0.5
        destroyed = agent.take_damage(0.6)
        assert destroyed is True
        assert agent.unit.state == AgentState.OFFLINE
    
    def test_agent_serialization(self):
        """Test agent serialization."""
        agent = BaseAgent(
            unit_id="test-1",
            domain=DomainType.LAND,
            unit_type="tank",
            position=(10.0, 20.0, 0.0),
            team="red",
        )
        data = agent.to_dict()
        assert data["unit_id"] == "test-1"
        assert data["team"] == "red"
        assert data["domain"] == "land"
    
    def test_agent_message_bus_integration(self):
        """Test message bus integration."""
        callbacks = []
        
        def callback(msg):
            callbacks.append(msg)
        
        agent = BaseAgent(
            unit_id="test-1",
            domain=DomainType.LAND,
            unit_type="tank",
            position=(0.0, 0.0, 0.0),
            message_bus=None,  # Simplified for testing
        )
        agent.add_sensor_callback(callback)
        
        from data.entities import Contact, ThreatLevel
        contact = Contact(
            contact_id="contact-1",
            domain=DomainType.AIR,
            position=(100.0, 100.0, 100.0),
            threat_level=ThreatLevel.HIGH,
        )
        agent.notify_sensors(contact)
        assert len(callbacks) == 1


class TestConfigs:
    """Test configuration dataclasses."""
    
    def test_base_config_defaults(self):
        """Test default configuration values."""
        config = AgentConfig()
        assert config.team == "blue"
        assert config.max_health == 1.0
        assert config.sensor_range == 50000.0
        assert config.deterministic is True
    
    def test_base_config_validation(self):
        """Test configuration validation."""
        config = AgentConfig(max_health=-1.0)
        with pytest.raises(ValueError):
            config.validate()
    
    def test_air_config(self):
        """Test air domain configuration."""
        config = AirAgentConfig()
        assert config.domain == DomainType.AIR
        assert config.max_altitude == 10000.0
        assert config.max_speed == 300.0
    
    def test_land_config(self):
        """Test land domain configuration."""
        config = LandAgentConfig()
        assert config.domain == DomainType.LAND
        assert config.max_speed == 50.0
        assert "road" in config.terrain_compatibility
    
    def test_sea_config(self):
        """Test sea domain configuration."""
        config = SeaAgentConfig()
        assert config.domain == DomainType.SEA
        assert config.max_depth == 500.0
        assert config.sonar_range == 50000.0
    
    def test_space_config(self):
        """Test space domain configuration."""
        config = SpaceAgentConfig()
        assert config.domain == DomainType.SPACE
        assert config.orbital_altitude_km == 500.0
        assert config.delta_v_capacity == 1000.0
    
    def test_cyber_config(self):
        """Test cyber domain configuration."""
        config = CyberAgentConfig()
        assert config.domain == DomainType.CYBER
        assert config.compute_nodes == 4
        assert 0.0 <= config.exploit_success_rate <= 1.0


class TestRegistry:
    """Test agent registry and factory."""
    
    def test_registry_registration(self):
        """Test agent type registration."""
        registry = AgentRegistry()
        
        class TestAgent(BaseAgent):
            def __init__(self, **kwargs):
                super().__init__(
                    unit_id=kwargs.get("unit_id", "test"),
                    domain=DomainType.LAND,
                    unit_type="test",
                    position=(0.0, 0.0, 0.0),
                )
            def take_turn(self, world_state, messages):
                return []
            def execute_mission(self, mission):
                return {}
        
        registry.register(
            agent_type="test_agent",
            agent_class=TestAgent,
            domain=DomainType.LAND,
            description="Test agent",
        )
        assert registry.has_type("test_agent")
        assert "test_agent" in registry.list_agent_types()
        assert "test_agent" in registry.list_agent_types(DomainType.LAND)
    
    def test_registry_unregistration(self):
        """Test agent type unregistration."""
        registry = AgentRegistry()
        
        class TestAgent(BaseAgent):
            def __init__(self, **kwargs):
                super().__init__(
                    unit_id=kwargs.get("unit_id", "test"),
                    domain=DomainType.LAND,
                    unit_type="test",
                    position=(0.0, 0.0, 0.0),
                )
            def take_turn(self, world_state, messages):
                return []
            def execute_mission(self, mission):
                return {}
        
        registry.register("test_agent", TestAgent, DomainType.LAND)
        registry.unregister("test_agent")
        assert not registry.has_type("test_agent")
    
    def test_registry_invalid_type(self):
        """Test error on invalid agent type."""
        registry = AgentRegistry()
        with pytest.raises(Exception):
            registry.get("nonexistent_agent")
    
    def test_factory_creation(self):
        """Test agent factory creation."""
        registry = AgentRegistry()
        
        class TestAgent(BaseAgent):
            def __init__(self, **kwargs):
                config = kwargs.get("config")
                super().__init__(
                    unit_id=kwargs.get("unit_id", "test"),
                    domain=DomainType.LAND,
                    unit_type="test",
                    position=kwargs.get("position", (0.0, 0.0, 0.0)),
                    team=config.team if config else "blue",
                )
                self.config = config
            def take_turn(self, world_state, messages):
                return []
            def execute_mission(self, mission):
                return {}
        
        registry.register(
            agent_type="test_agent",
            agent_class=TestAgent,
            domain=DomainType.LAND,
            config_class=AgentConfig,
        )
        
        factory = AgentFactory(registry)
        agent = factory.create(
            agent_type="test_agent",
            unit_id="factory-test-1",
            position=(10.0, 20.0, 0.0),
            team="red",
        )
        assert agent.unit.unit_id == "factory-test-1"
        assert agent.unit.team == "red"


class TestDomainAgents:
    """Test domain-specific agents."""
    
    def test_air_agent_creation(self):
        """Test air agent creation."""
        agent = AirAgent(
            unit_id="air-1",
            position=(0.0, 0.0, 5000.0),
            team="blue",
        )
        assert agent.unit.domain == DomainType.AIR
        assert agent.altitude == 5000.0
        assert agent.max_altitude == 10000.0
    
    def test_land_agent_creation(self):
        """Test land agent creation."""
        agent = LandAgent(
            unit_id="land-1",
            position=(100.0, 200.0, 0.0),
            team="blue",
        )
        assert agent.unit.domain == DomainType.LAND
        assert agent.max_speed == 50.0
        assert agent.armor_rating == 1.0
    
    def test_sea_agent_creation(self):
        """Test sea agent creation."""
        agent = SeaAgent(
            unit_id="sea-1",
            position=(0.0, 0.0, -50.0),
            team="blue",
        )
        assert agent.unit.domain == DomainType.SEA
        assert agent.depth == 50.0
        assert agent.max_depth == 500.0
    
    def test_space_agent_creation(self):
        """Test space agent creation."""
        agent = SpaceAgent(
            unit_id="space-1",
            position=(5000.0, 0.0, 0.0),
            team="blue",
        )
        assert agent.unit.domain == DomainType.SPACE
        assert agent.orbital_altitude_km == 500.0
        assert agent.power_level == 1.0
    
    def test_cyber_agent_creation(self):
        """Test cyber agent creation."""
        agent = CyberAgent(
            unit_id="cyber-1",
            position=(0.0, 0.0, 0.0),
            team="blue",
        )
        assert agent.unit.domain == DomainType.CYBER
        assert agent.compute_nodes == 4
        assert agent.bandwidth_mbps == 1000.0


class TestSerialization:
    """Test agent serialization."""
    
    def test_air_agent_serialization(self):
        """Test air agent serialization."""
        agent = AirAgent(
            unit_id="air-1",
            position=(0.0, 0.0, 5000.0),
            team="blue",
        )
        agent.target_altitude = 6000.0
        agent.heading = 90.0
        
        data = agent.to_dict()
        assert data["unit_id"] == "air-1"
        assert data["altitude"] == 5000.0
        assert data["target_altitude"] == 6000.0
        assert data["heading"] == 90.0
    
    def test_land_agent_serialization(self):
        """Test land agent serialization."""
        agent = LandAgent(
            unit_id="land-1",
            position=(100.0, 200.0, 0.0),
            team="blue",
        )
        agent.speed = 25.0
        agent.movement_state = "moving"
        
        data = agent.to_dict()
        assert data["unit_id"] == "land-1"
        assert data["speed"] == 25.0
        assert data["movement_state"] == "moving"
    
    def test_sea_agent_serialization(self):
        """Test sea agent serialization."""
        agent = SeaAgent(
            unit_id="sea-1",
            position=(0.0, 0.0, -100.0),
            team="blue",
        )
        agent.depth = 100.0
        agent.stealth_mode = True
        
        data = agent.to_dict()
        assert data["unit_id"] == "sea-1"
        assert data["depth"] == 100.0
        assert data["stealth_mode"] is True
    
    def test_space_agent_serialization(self):
        """Test space agent serialization."""
        agent = SpaceAgent(
            unit_id="space-1",
            position=(5000.0, 0.0, 0.0),
            team="blue",
        )
        agent.power_level = 0.8
        agent.velocity = (7.5, 0.0, 0.0)
        
        data = agent.to_dict()
        assert data["unit_id"] == "space-1"
        assert data["power_level"] == 0.8
        assert data["velocity"] == (7.5, 0.0, 0.0)
    
    def test_cyber_agent_serialization(self):
        """Test cyber agent serialization."""
        agent = CyberAgent(
            unit_id="cyber-1",
            position=(0.0, 0.0, 0.0),
            team="blue",
        )
        agent.access_level = 0.7
        agent.detection_risk = 0.3
        
        data = agent.to_dict()
        assert data["unit_id"] == "cyber-1"
        assert data["access_level"] == 0.7
        assert data["detection_risk"] == 0.3


class TestDomainBehaviors:
    """Test domain-specific behaviors."""
    
    def test_air_altitude_management(self):
        """Test air agent altitude management."""
        agent = AirAgent(
            unit_id="air-1",
            position=(0.0, 0.0, 1000.0),
            team="blue",
        )
        agent.set_altitude(2000.0)
        assert agent.target_altitude == 2000.0
        agent.climb(rate=500.0)
        assert agent.altitude == 1500.0
    
    def test_land_movement(self):
        """Test land agent movement."""
        agent = LandAgent(
            unit_id="land-1",
            position=(0.0, 0.0, 0.0),
            team="blue",
        )
        agent.move_to((100.0, 100.0, 0.0), speed=25.0)
        assert agent.target_position == (100.0, 100.0, 0.0)
        assert agent.speed == 25.0
        assert agent.movement_state == "moving"
    
    def test_sea_depth_management(self):
        """Test sea agent depth management."""
        agent = SeaAgent(
            unit_id="sea-1",
            position=(0.0, 0.0, 0.0),
            team="blue",
        )
        agent.submerge(depth=200.0)
        assert agent.target_depth == 200.0
        assert agent.movement_state == "submerged"
        agent.surface()
        assert agent.target_depth == 0.0
    
    def test_space_delta_v(self):
        """Test space agent delta-v."""
        agent = SpaceAgent(
            unit_id="space-1",
            position=(5000.0, 0.0, 0.0),
            team="blue",
        )
        initial_delta_v = agent.delta_v_remaining
        success = agent.apply_delta_v(100.0, "prograde")
        assert success is True
        assert agent.delta_v_remaining < initial_delta_v
    
    def test_cyber_stealth(self):
        """Test cyber agent stealth."""
        agent = CyberAgent(
            unit_id="cyber-1",
            position=(0.0, 0.0, 0.0),
            team="blue",
        )
        agent.detection_risk = 0.5
        agent.enable_stealth()
        assert agent.stealth_factor == 0.9
        assert agent.detection_risk < 0.5


class TestRegistry:
    """Test agent registry functionality."""
    
    def test_list_domains(self):
        """Test listing domains."""
        registry = AgentRegistry()
        # Should have domains after registering agents
        domains = registry.list_domains()
        assert isinstance(domains, list)


class TestReproducibility:
    """Test deterministic behavior."""
    
    def test_agent_creation_reproducibility(self):
        """Test that agents can be created reproducibly."""
        agent1 = LandAgent(
            unit_id="repro-1",
            position=(100.0, 200.0, 0.0),
            team="blue",
        )
        agent2 = LandAgent(
            unit_id="repro-1",
            position=(100.0, 200.0, 0.0),
            team="blue",
        )
        assert agent1.unit.unit_id == agent2.unit.unit_id
        assert agent1.unit.position == agent2.unit.position
        assert agent1.unit.team == agent2.unit.team


if __name__ == "__main__":
    pytest.main([__file__, "-v"])