# Copyright (c) Ultrone Contributors. All rights reserved.
"""Tank agent - land domain."""

import logging
import random
from typing import Dict, List, Any, Tuple

from ..base_agent import BaseAgent, AgentCapability
from ...data.entities import DomainType, AgentState
from ...comms.protocol import Message, MessageType

logger = logging.getLogger("Ultrone.Agents.Land.Tank")


class TankAgent(BaseAgent):
    """Tank: HULL_DOWN/MOVING/FIRING/SUPPRESSING/RETREATING states."""
    
    class TankState(AgentState):
        HULL_DOWN = "hull_down"
        MOVING = "moving"
        FIRING = "firing"
        SUPPRESSING = "suppressing"
        RETREATING = "retreating"
    
    def __init__(self, unit_id: str, position: Tuple[float, float, float], team: str = "blue"):
        super().__init__(unit_id, DomainType.LAND, "tank", position, team,
            [AgentCapability.SENSE, AgentCapability.MOVE, AgentCapability.ENGAGE])
    
    def take_turn(self, world_state, messages: List[Message]) -> List[Message]:
        return []
    
    def execute_mission(self, mission: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "ready"}
    
    def get_stats(self) -> dict:
        return {"unit_id": self.unit.unit_id, "state": self.state, "ammo": self.unit.ammunition}