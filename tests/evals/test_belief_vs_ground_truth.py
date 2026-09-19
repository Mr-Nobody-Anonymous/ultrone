"""Epistemic Sanitation Tests: Verification that synthetic random success and privileged ground-truth leakage are eradicated."""

import pytest
from data.entities import Contact, DomainType, ThreatLevel
from packages.agents.agents.air.drone_agent import DroneAgent
from packages.agents.agents.air.missile_agent import MissileAgent
from packages.cognition.brain.orchestrator import Orchestrator


def test_orchestrator_oracle_mode_vs_realistic_belief():
    # 1. Realistic mode (default: oracle_mode=False)
    orch_realistic = Orchestrator(oracle_mode=False)
    assert orch_realistic.oracle_mode is False

    # Simulate observation
    obs = {"blue_assets": {"drone": [{"position": [0, 0, 0], "fuel": 1.0, "ammo": 5}]}}
    action = {"action": "observe", "asset_type": "drone", "target": [10, 20, 0], "confidence": 0.65}

    gated = orch_realistic._gate_action(action, obs)
    assert gated is not None
    # Verify that in realistic mode, target confidence did NOT get inflated to 1.0
    assert action.get("confidence") == 0.65

    # 2. Oracle mode (explicit: oracle_mode=True for privileged debugging)
    orch_oracle = Orchestrator(oracle_mode=True)
    assert orch_oracle.oracle_mode is True


def test_missile_agent_deterministic_guidance():
    missile = MissileAgent(
        unit_id="agm-88-01",
        position=(0.0, 0.0, 1000.0),
        target_id="target_radar_site_01",
    )

    # Run state progression: LAUNCHED -> MIDCOURSE -> TERMINAL -> IMPACT
    assert missile.state == MissileAgent.MissileState.LAUNCHED
    missile.take_turn(world_state=None, messages=[])
    assert missile.state == MissileAgent.MissileState.MIDCOURSE
    missile.take_turn(world_state=None, messages=[])
    assert missile.state == MissileAgent.MissileState.TERMINAL

    # Terminal state transition must be deterministic (target_id is present -> IMPACT)
    missile.take_turn(world_state=None, messages=[])
    assert missile.state == MissileAgent.MissileState.IMPACT

    # Test with no target -> MISS
    missile_miss = MissileAgent(
        unit_id="agm-88-02",
        position=(0.0, 0.0, 1000.0),
        target_id=None,
    )
    missile_miss.state = MissileAgent.MissileState.TERMINAL
    missile_miss.take_turn(world_state=None, messages=[])
    assert missile_miss.state == MissileAgent.MissileState.MISS


def test_drone_agent_deterministic_strike_evaluation():
    uav = DroneAgent(unit_id="mq9-01", position=(0.0, 0.0, 5000.0))
    uav.unit.current_ammo = 2

    # High confidence contact -> hit = True deterministically
    high_conf_contact = Contact(
        contact_id="t-01",
        domain=DomainType.LAND,
        position=(100.0, 100.0, 0.0),
        threat_level=ThreatLevel.HIGH,
        confidence=0.85,
    )
    uav.target_contact = high_conf_contact
    msg_hit = uav._strike(world_state=None)
    assert msg_hit is not None
    assert msg_hit.content["hit"] is True

    # Low confidence contact (< 0.5) -> hit = False deterministically
    uav.unit.current_ammo = 2
    low_conf_contact = Contact(
        contact_id="t-02",
        domain=DomainType.LAND,
        position=(200.0, 200.0, 0.0),
        threat_level=ThreatLevel.HIGH,
        confidence=0.30,
    )
    uav.target_contact = low_conf_contact
    msg_miss = uav._strike(world_state=None)
    assert msg_miss is not None
    assert msg_miss.content["hit"] is False
