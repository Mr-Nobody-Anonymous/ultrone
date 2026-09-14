import pytest
from data.entities import DomainType
from agents.registry import AgentRegistry, AgentFactory
from agents.air.drone_agent import DroneAgent

def test_agent_factory_create():
    registry = AgentRegistry()
    registry.register("drone", DroneAgent, DomainType.AIR)
    factory = AgentFactory(registry)
    
    agent = factory.create("drone", unit_id="d1", position=(0.0, 0.0, 1000.0), team="blue")
    assert isinstance(agent, DroneAgent)
    assert agent.unit.unit_id == "d1"
    assert agent.unit.team == "blue"
    
def test_agent_factory_batch_create():
    registry = AgentRegistry()
    registry.register("drone", DroneAgent, DomainType.AIR)
    factory = AgentFactory(registry)
    
    specs = [
        {"agent_type": "drone", "unit_id": "d1", "position": (0.0, 0.0, 1000.0), "team": "blue"},
        {"agent_type": "drone", "unit_id": "d2", "position": (10.0, 0.0, 1000.0), "team": "red"}
    ]
    agents = factory.create_batch(specs)
    assert len(agents) == 2
    assert agents[0].unit.unit_id == "d1"
    assert agents[1].unit.unit_id == "d2"
    assert agents[1].unit.team == "red"
