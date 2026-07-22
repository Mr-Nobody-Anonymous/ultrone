# Copyright (c) Ultrone Contributors. All rights reserved.
"""Fighter aircraft agent."""

import logging
import random
from typing import Dict, List, Any, Tuple

from ..base_agent import BaseAgent, AgentCapability
from ...data.entities import DomainType, Contact, AgentState, ThreatLevel
from ...comms.protocol import Message, MessageType, Priority

logger = logging.getLogger("Ultrone.Agents.Air.Fighter")


class FighterAgent(BaseAgent):
    """Fighter: PATROL/INTERCEPT/BVR/WVR/DEFENSIVE/RTB states."""
    
    class FighterState(AgentState):
        PATROL = "patrol"
        INTERCEPT = "intercept"
        BVR = "bvr"  # Beyond Visual Range
        WVR = "wvr"  # Within Visual Range
        DEFENSIVE = "defensive"
    
    def __init__(self, unit_id: str, position: Tuple[float, float, float], team: str = "blue"):
        super().__init__(unit_id, DomainType.AIR, "fighter_jet", position, team,
            [AgentCapability.SENSE, AgentCapability.MOVE, AgentCapability.ENGAGE])
        self.target_contact: Contact = None
    
    def take_turn(self, world_state, messages: List[Message]) -> List[Message]:
        responses = []
        for msg in messages:
            resp = self.handle_message(msg)
            if resp:
                responses.append(resp)
        
        if self.state == self.FighterState.PATROL:
            self._patrol(world_state, responses)
        elif self.state == self.FighterState.INTERCEPT:
            self._intercept(world_state, responses)
        elif self.state in [self.FighterState.BVR, self.FighterState.WVR]:
            result = self._engage(world_state)
            if result:
                responses.append(result)
        
        return responses
    
    def _patrol(self, world_state, responses) -> None:
        contacts = world_state.get_contacts_in_range(self.unit.position, self.unit.sensor_range, DomainType.AIR)
        for contact in contacts:
            if contact.threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
                self.target_contact = contact
                self.state = self.FighterState.INTERCEPT
                break
    
    def _intercept(self, world_state, responses) -> None:
        if self.target_contact and self.unit.consume_ammunition():
            self.state = self.FighterState.BVR if random.random() > 0.3 else self.FighterState.WVR
    
    def _engage(self, world_state) -> Message:
        hit = random.random() > 0.15
        return self.create_message(MessageType.ENGAGEMENT,
            content={"action": "engage", "target": self.target_contact.contact_id, "hit": hit},
            priority=Priority.IMMEDIATE)
    
    def execute_mission(self, mission: Dict[str, Any]) -> Dict[str, Any]:
        action = mission.get("action")
        if action in ["intercept", "patrol", "engage"]:
            self.state = getattr(self.FighterState, action.upper(), self.FighterState.PATROL)
        return {"status": "executing" if action else "no_action"}
    
    def get_stats(self) -> dict:
        return {"unit_id": self.unit.unit_id, "state": self.state, "ammo": self.unit.ammunition}