import pytest
from data.entities import DomainType, AgentState, Contact, ThreatLevel
from agents.air.drone_agent import DroneAgent
from agents.air.fighter_agent import FighterAgent
from agents.air.missile_agent import MissileAgent

def test_drone_agent_initialization():
    agent = DroneAgent(unit_id="uav_1", position=(0.0, 0.0, 5000.0), team="blue")
    assert agent.unit.unit_id == "uav_1"
    assert agent.unit.domain == DomainType.AIR
    assert agent.unit.team == "blue"
    assert agent.unit.unit_type == "drone"
    assert agent.state == AgentState.STANDBY

def test_drone_agent_loiter_transition():
    class DummyWorldState:
        def get_contacts_in_range(self, pos, ran, dom):
            c = Contact("c1", DomainType.LAND, (10.0, 10.0, 0.0))
            c.threat_level = ThreatLevel.HIGH
            return [c]
    
    agent = DroneAgent(unit_id="uav_1", position=(0.0, 0.0, 5000.0))
    agent.state = DroneAgent.UAVState.LOITER
    agent._loiter(DummyWorldState())
    assert agent.state == AgentState.ENGAGED
    assert agent.target_contact is not None

def test_fighter_agent_initialization():
    agent = FighterAgent(unit_id="f22_1", position=(0.0, 0.0, 10000.0), team="blue")
    assert agent.unit.unit_id == "f22_1"
    assert agent.unit.domain == DomainType.AIR
    assert agent.unit.team == "blue"
    assert agent.unit.unit_type == "fighter_jet"

def test_missile_agent_initialization():
    agent = MissileAgent(unit_id="aim_1", position=(0.0, 0.0, 8000.0), team="blue", target_id="t1")
    assert agent.unit.unit_id == "aim_1"
    assert agent.unit.domain == DomainType.AIR
    assert agent.unit.team == "blue"
    assert agent.unit.unit_type == "missile"
