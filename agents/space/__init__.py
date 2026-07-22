from ..base_agent import BaseAgent, AgentCapability
from ...data.entities import DomainType

class SatelliteAgent(BaseAgent):
    """Satellite: ORBIT/IMAGE/COMMS/MANEUVER states."""
    def __init__(self, unit_id, position=(0,0,0), team="blue"):
        super().__init__(unit_id, DomainType.SPACE, "satellite", position, team,
            [AgentCapability.SENSE, AgentCapability.COMMUNICATE])

class OrbitalAgent(BaseAgent):
    """Orbital agent: orbital mechanics, ground track prediction."""
    def __init__(self, unit_id, position=(0,0,0), team="blue"):
        super().__init__(unit_id, DomainType.SPACE, "orbital", position, team,
            [AgentCapability.SENSE, AgentCapability.MOVE])

class SpaceWeaponAgent(BaseAgent):
    """Space weapon: TARGET/CHARGE/FIRE/COOLDOWN states."""
    def __init__(self, unit_id, position=(0,0,0), team="blue"):
        super().__init__(unit_id, DomainType.SPACE, "space_weapon", position, team,
            [AgentCapability.ENGAGE, AgentCapability.MOVE])