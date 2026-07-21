# Copyright (c) Ultrone Contributors. All rights reserved.
"""Mobile SAM agent - land domain."""
from ..base_agent import BaseAgent, AgentCapability
from ...data.entities import DomainType

class MobileMissileAgent(BaseAgent):
    """SAM: RECON/LAUNCH/RELOCATE/RELOAD/HIDE states."""
    def __init__(self, unit_id, position, team="blue"):
        super().__init__(unit_id, DomainType.LAND, "mobile_sam", position, team,
            [AgentCapability.SENSE, AgentCapability.MOVE, AgentCapability.ENGAGE])
    def take_turn(self, world_state, messages): return []
    def execute_mission(self, mission): return {"status": "ready"}