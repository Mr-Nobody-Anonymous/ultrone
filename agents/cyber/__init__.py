from ..base_agent import BaseAgent, AgentCapability
from ...data.entities import DomainType

class ReconAgent(BaseAgent):
    """Recon: SCAN/ANALYZE/REPORT states."""
    def __init__(self, unit_id, position=(0,0,0), team="blue"):
        super().__init__(unit_id, DomainType.CYBER, "recon", position, team,
            [AgentCapability.SENSE, AgentCapability.ENGAGE])

class ExploitAgent(BaseAgent):
    """Exploit: PREPARE/EXECUTE/EXFIL/CLEANUP states."""
    def __init__(self, unit_id, position=(0,0,0), team="blue"):
        super().__init__(unit_id, DomainType.CYBER, "exploit", position, team,
            [AgentCapability.ENGAGE, AgentCapability.STEALTH])

class DefendAgent(BaseAgent):
    """Defend: MONITOR/DETECT/ISOLATE/COUNTER states."""
    def __init__(self, unit_id, position=(0,0,0), team="blue"):
        super().__init__(unit_id, DomainType.CYBER, "defend", position, team,
            [AgentCapability.SENSE, AgentCapability.ENGAGE])