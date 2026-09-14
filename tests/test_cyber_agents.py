import pytest
from data.entities import DomainType
from agents.cyber.recon_agent import ReconAgent
from agents.cyber.exploit_agent import ExploitAgent
from agents.cyber.defend_agent import DefendAgent

def test_recon_agent_initialization():
    agent = ReconAgent(unit_id="cr_1", position=(0.0, 0.0, 0.0), team="blue")
    assert agent.unit.unit_id == "cr_1"
    assert agent.unit.domain == DomainType.CYBER
    assert agent.unit.unit_type == "cyber_recon"

def test_exploit_agent_initialization():
    agent = ExploitAgent(unit_id="ce_1", position=(0.0, 0.0, 0.0), team="red")
    assert agent.unit.unit_id == "ce_1"
    assert agent.unit.domain == DomainType.CYBER
    assert agent.unit.unit_type == "cyber_exploit"

def test_defend_agent_initialization():
    agent = DefendAgent(unit_id="cd_1", position=(0.0, 0.0, 0.0), team="blue")
    assert agent.unit.unit_id == "cd_1"
    assert agent.unit.domain == DomainType.CYBER
    assert agent.unit.unit_type == "cyber_defend"
