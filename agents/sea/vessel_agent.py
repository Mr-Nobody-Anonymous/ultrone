from ..base_agent import BaseAgent, AgentCapability
from ...data.entities import DomainType

class VesselAgent(BaseAgent):
    """Ship: CRUISE/COMBAT_STATION/AA/ASW/SHORE_BOMB states."""
    def __init__(self, unit_id, position, team="blue"):
        super().__init__(unit_id, DomainType.SEA, "vessel", position, team,
            [AgentCapability.SENSE, AgentCapability.MOVE, AgentCapability.ENGAGE])
    def take_turn(self, world_state, messages): return []
    def execute_mission(self, mission): return {"status": "ready"}

class SubmarineAgent(BaseAgent):
    """Sub: SUBMERGED/PD/ATTACK_DEPTH/EVASIVE/SURFACED states."""
    def __init__(self, unit_id, position, team="blue"):
        super().__init__(unit_id, DomainType.SEA, "submarine", position, team,
            [AgentCapability.SENSE, AgentCapability.MOVE, AgentCapability.ENGAGE])

class NavalAirAgent(BaseAgent):
    """Carrier air: similar to fighter + deck cycle."""
    def __init__(self, unit_id, position, team="blue"):
        super().__init__(unit_id, DomainType.AIR, "naval_aircraft", position, team,
            [AgentCapability.SENSE, AgentCapability.MOVE, AgentCapability.ENGAGE])