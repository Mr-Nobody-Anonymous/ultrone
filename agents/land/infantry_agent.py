# Copyright (c) Ultrone Contributors. All rights reserved.
"""Infantry agent - land domain."""

from ..base_agent import BaseAgent, AgentCapability
from ...data.entities import DomainType

class InfantryAgent(BaseAgent):
    """Squad: MOVING/COVER/ASSAULT/DEFEND/CALLING_FIRE states."""
    def __init__(self, unit_id, position, team="blue"):
        super().__init__(unit_id, DomainType.LAND, "infantry_squad", position, team,
            [AgentCapability.SENSE, AgentCapability.MOVE, AgentCapability.ENGAGE])
    def take_turn(self, world_state, messages): return []
    def execute_mission(self, mission): return {"status": "ready"}
    def get_stats(self): return {"unit_id": self.unit.unit_id, "state": self.state}