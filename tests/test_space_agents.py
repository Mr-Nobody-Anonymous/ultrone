import pytest
from data.entities import DomainType
from agents.space.satellite_agent import SatelliteAgent
from agents.space.orbital_agent import OrbitalAgent
from agents.space.space_weapon_agent import SpaceWeaponAgent

def test_satellite_agent_initialization():
    agent = SatelliteAgent(unit_id="sat_1", position=(0.0, 0.0, 400000.0), team="blue")
    assert agent.unit.unit_id == "sat_1"
    assert agent.unit.domain == DomainType.SPACE
    assert agent.unit.unit_type == "satellite"

def test_orbital_agent_initialization():
    agent = OrbitalAgent(unit_id="orb_1", position=(0.0, 0.0, 500000.0), team="red")
    assert agent.unit.unit_id == "orb_1"
    assert agent.unit.domain == DomainType.SPACE
    assert agent.unit.unit_type == "orbital"

def test_space_weapon_agent_initialization():
    agent = SpaceWeaponAgent(unit_id="sw_1", position=(0.0, 0.0, 600000.0), team="red")
    assert agent.unit.unit_id == "sw_1"
    assert agent.unit.domain == DomainType.SPACE
    assert agent.unit.unit_type == "space_weapon"
