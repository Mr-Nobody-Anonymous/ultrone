# Copyright (c) Ultrone Contributors. All rights reserved.
"""Multi-Agent Coordination algorithms module.

Provides interchangeable coordination protocols:

- ``BaseCoordinator``: Abstract interface for coordination algorithms
- ``ConsensusProtocol``: Distributed consensus for agreement
- ``TaskAllocation``: Distributed task allocation (auction-based)
- ``ContractNet``: Contract Net Protocol for delegation
- ``CoalitionFormation``: Dynamic coalition formation
- ``BlackboardSystem``: Shared blackboard architecture
- ``RoleAssignment``: Dynamic role assignment
- ``FormationControl``: Formation control for swarms
- ``SwarmCoordination``: Emergent swarm coordination
- ``TeamReasoning``: Shared mental models for teams
- ``DynamicLeadership``: Dynamic leadership election
- ``EmergentBehavior``: Emergent behavior analysis

All coordinators implement the ``BaseCoordinator`` interface.
"""

from .base import BaseCoordinator, CoordinationConfig, CoordinationMessage
from .consensus import ConsensusProtocol, ConsensusConfig
from .task_allocation import TaskAllocation, TaskAllocationConfig
from .contract_net import ContractNet, ContractNetConfig
from .coalition import CoalitionFormation, CoalitionConfig
from .blackboard import BlackboardSystem, BlackboardConfig
from .role_assignment import RoleAssignment, RoleConfig
from .formation_control import FormationControl, FormationConfig
from .swarm_coordination import SwarmCoordination, SwarmConfig
from .team_reasoning import TeamReasoning, TeamReasoningConfig
from .dynamic_leadership import DynamicLeadership, LeadershipConfig
from .emergent_behavior import EmergentBehavior, EmergentBehaviorConfig

__all__ = [
    "BaseCoordinator", "CoordinationConfig", "CoordinationMessage",
    "ConsensusProtocol", "ConsensusConfig",
    "TaskAllocation", "TaskAllocationConfig",
    "ContractNet", "ContractNetConfig",
    "CoalitionFormation", "CoalitionConfig",
    "BlackboardSystem", "BlackboardConfig",
    "RoleAssignment", "RoleConfig",
    "FormationControl", "FormationConfig",
    "SwarmCoordination", "SwarmConfig",
    "TeamReasoning", "TeamReasoningConfig",
    "DynamicLeadership", "LeadershipConfig",
    "EmergentBehavior", "EmergentBehaviorConfig",
]
