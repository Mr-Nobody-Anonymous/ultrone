# Copyright (c) Ultrone Contributors. All rights reserved.
"""Missile agent - ephemeral."""

import logging
import random
from typing import Dict, List, Any, Tuple

from ..base_agent import BaseAgent, AgentCapability
from ...data.entities import DomainType, AgentState
from ...comms.protocol import Message

logger = logging.getLogger("Ultrone.Agents.Air.Missile")


class MissileAgent(BaseAgent):
    """Missile: LAUNCHED/MIDCOURSE/TERMINAL/IMPACT/MISS states."""
    
    class MissileState(AgentState):
        LAUNCHED = "launched"
        MIDCOURSE = "midcourse"
        TERMINAL = "terminal"
        IMPACT = "impact"
        MISS = "miss"
    
    def __init__(self, unit_id: str, position: Tuple[float, float, float], target_id: str, team: str = "blue"):
        super().__init__(unit_id, DomainType.AIR, "missile", position, team,
            [AgentCapability.MOVE, AgentCapability.ENGAGE])
        self.target_id = target_id
        self.state = self.MissileState.LAUNCHED
    
    def take_turn(self, world_state, messages: List[Message]) -> List[Message]:
        responses = []
        
        # Quick state progression
        if self.state == self.MissileState.LAUNCHED:
            self.state = self.MissileState.MIDCOURSE
        elif self.state == self.MissileState.MIDCOURSE:
            self.state = self.MissileState.TERMINAL
        elif self.state == self.MissileState.TERMINAL:
            self.state = self.MissileState.IMPACT if random.random() > 0.2 else self.MissileState.MISS
        # Once impact/miss, stays there
        
        return responses
    
    def execute_mission(self, mission: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "in_flight", "target": self.target_id}
    
    def get_stats(self) -> dict:
        return {"unit_id": self.unit.unit_id, "state": self.state, "target": self.target_id}