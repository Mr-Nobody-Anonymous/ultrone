"""AI Architecture Patterns for agent decision-making.

Provides alternative decision-making architectures beyond
the standard OODA loop:

- ``BehaviorTree``: Behavior Trees for modular agent control
- ``GOAP``: Goal-Oriented Action Planning
- ``UtilityAI``: Utility-based AI for nuanced decisions
- ``BDIAgent``: Belief–Desire–Intention architecture
- ``FSM``: Finite State Machines
- ``HierarchicalFSM``: Hierarchical State Machines
- ``BlackboardSystem``: Blackboard-based coordination
- ``ReactivePlanner``: Reactive planning systems
"""

from .base import AIArchitecture, AIArchitectureConfig
from .behavior_tree import BehaviorTree, BTConfig, Sequence, Selector, Action, Condition
from .goap import GOAP, GOAPConfig, GOAPAction, GOAPGoal
from .utility_ai import UtilityAI, UtilityAIConfig, Consideration, Option
from .bdi_agent import BDIAgent, BDIConfig, Belief, Desire, Intention
from .fsm import FSM, FSMConfig, State, Transition
from .hierarchical_fsm import HierarchicalFSM, HFSMConfig
from .blackboard_system import BlackboardSystem, BlackboardEntry
from .reactive_planning import ReactivePlanner, ReactivePlanConfig

__all__ = [
    "AIArchitecture", "AIArchitectureConfig",
    "BehaviorTree", "BTConfig", "Sequence", "Selector", "Action", "Condition",
    "GOAP", "GOAPConfig", "GOAPAction", "GOAPGoal",
    "UtilityAI", "UtilityAIConfig", "Consideration", "Option",
    "BDIAgent", "BDIConfig", "Belief", "Desire", "Intention",
    "FSM", "FSMConfig", "State", "Transition",
    "HierarchicalFSM", "HFSMConfig",
    "BlackboardSystem", "BlackboardEntry",
    "ReactivePlanner", "ReactivePlanConfig",
]
