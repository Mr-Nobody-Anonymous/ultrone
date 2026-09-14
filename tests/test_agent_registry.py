import pytest
from data.entities import DomainType
from agents.config import AgentConfig
from agents.registry import AgentRegistry, AgentFactory, InvalidAgentTypeError, AgentConfigurationError
from agents.air.drone_agent import DroneAgent

def test_agent_registry_registration():
    registry = AgentRegistry()
    registry.register("drone_test", DroneAgent, DomainType.AIR)
    
    assert registry.has_type("drone_test")
    assert "drone_test" in registry.list_agent_types()
    assert registry.get_agent_class("drone_test") == DroneAgent
    
    registry.unregister("drone_test")
    assert not registry.has_type("drone_test")

def test_agent_registry_get_invalid():
    registry = AgentRegistry()
    with pytest.raises(InvalidAgentTypeError):
        registry.get("nonexistent")
