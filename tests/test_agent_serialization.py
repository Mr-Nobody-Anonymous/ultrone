import pytest
from data.entities import DomainType
from agents.base_agent import BaseAgent
from agents.air.drone_agent import DroneAgent

def test_agent_to_dict():
    agent = DroneAgent(unit_id="d1", position=(10.0, 20.0, 30.0), team="blue")
    agent.unit.health = 0.5
    data = agent.to_dict()
    
    assert data["unit_id"] == "d1"
    assert data["domain"] == DomainType.AIR.value
    assert data["team"] == "blue"
    assert data["position"]["x"] == 10.0
    assert data["position"]["y"] == 20.0
    assert data["position"]["z"] == 30.0
    assert data["health"] == 0.5

def test_agent_from_dict():
    data = {
        "unit_id": "d1",
        "domain": DomainType.AIR.value,
        "unit_type": "drone",
        "position": {"x": 10.0, "y": 20.0, "z": 30.0},
        "team": "blue",
        "health": 0.5
    }
    
    agent = DroneAgent.from_dict(data)
    assert isinstance(agent, DroneAgent)
    assert agent.unit.unit_id == "d1"
    assert agent.unit.domain == DomainType.AIR
    assert agent.unit.team == "blue"
    assert agent.unit.position == (10.0, 20.0, 30.0)
    assert agent.unit.health == 0.5

def test_agent_clone():
    agent = DroneAgent(unit_id="d1", position=(10.0, 20.0, 30.0), team="blue")
    agent.unit.health = 0.8
    
    clone_agent = agent.clone()
    assert isinstance(clone_agent, DroneAgent)
    assert clone_agent.unit.unit_id != "d1"
    assert clone_agent.unit.unit_id.startswith("d1_clone_")
    assert clone_agent.unit.team == "blue"
    assert clone_agent.unit.position == (10.0, 20.0, 30.0)
    assert clone_agent.unit.health == 0.8
    
    # Verify it is a deep copy (mutating clone doesn't mutate original)
    clone_agent.unit.health = 0.1
    assert agent.unit.health == 0.8
