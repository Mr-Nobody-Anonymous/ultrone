import pytest
from data.entities import DomainType
from agents.land.tank_agent import TankAgent
from agents.land.infantry_agent import InfantryAgent
from agents.land.mobile_missile_agent import MobileMissileAgent

def test_tank_agent_initialization():
    agent = TankAgent(unit_id="tank_1", position=(100.0, 100.0, 0.0), team="red")
    assert agent.unit.unit_id == "tank_1"
    assert agent.unit.domain == DomainType.LAND
    assert agent.unit.team == "red"
    assert agent.unit.unit_type == "tank"

def test_infantry_agent_initialization():
    agent = InfantryAgent(unit_id="inf_1", position=(110.0, 110.0, 0.0), team="blue")
    assert agent.unit.unit_id == "inf_1"
    assert agent.unit.domain == DomainType.LAND
    assert agent.unit.unit_type == "infantry_squad"

def test_mobile_missile_agent_initialization():
    agent = MobileMissileAgent(unit_id="sam_1", position=(150.0, 150.0, 0.0), team="red")
    assert agent.unit.unit_id == "sam_1"
    assert agent.unit.domain == DomainType.LAND
    assert agent.unit.unit_type == "mobile_sam"
