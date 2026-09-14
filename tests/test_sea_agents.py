import pytest
from data.entities import DomainType
from agents.sea.vessel_agent import VesselAgent
from agents.sea.submarine_agent import SubmarineAgent
from agents.sea.naval_air_agent import NavalAirAgent

def test_vessel_agent_initialization():
    agent = VesselAgent(unit_id="ship_1", position=(0.0, 0.0, 0.0), team="blue")
    assert agent.unit.unit_id == "ship_1"
    assert agent.unit.domain == DomainType.SEA
    assert agent.unit.unit_type == "vessel"

def test_submarine_agent_initialization():
    agent = SubmarineAgent(unit_id="sub_1", position=(0.0, 0.0, -100.0), team="red")
    assert agent.unit.unit_id == "sub_1"
    assert agent.unit.domain == DomainType.SEA
    assert agent.unit.unit_type == "submarine"

def test_naval_air_agent_initialization():
    agent = NavalAirAgent(unit_id="n_air_1", position=(0.0, 0.0, 1000.0), team="blue")
    assert agent.unit.unit_id == "n_air_1"
    assert agent.unit.domain == DomainType.SEA
    assert agent.unit.unit_type == "naval_air"
