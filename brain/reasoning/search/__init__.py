# Copyright (c) Ultrone Contributors. All rights reserved.
"""Search and Planning algorithms module.

Provides 12 planning algorithms with a common ``Planner`` interface:

- ``MCTS``: Monte Carlo Tree Search
- ``HTNPlanner``: Hierarchical Task Networks
- ``AStar``, ``DLite``, ``LPAStar``: A* and incremental variants
- ``MAPFPlanner``: Multi-Agent Path Finding (Conflict-Based Search)
- ``BeamSearch``: Beam Search
- ``BidirectionalSearch``: Bidirectional heuristic search
- ``PDDLPlanner``: STRIPS/PDDL planner
- ``AnytimePlanner``: Anytime planning wrapper
- ``RecedingHorizonPlanner``: Receding Horizon Control
- ``DPPlanner``: Dynamic Programming-based planning
- ``PRMPlanner``: Probabilistic Roadmap
- ``RRTPlanner``: Rapidly-exploring Random Trees
"""

from .base import (
    Planner, PlanningAction, PlanningDomain, PlanningGoal, PlanningResult,
)
from .mcts import MCTS, MCTSConfig
from .htn import HTNPlanner, HTNConfig, Task, Method, PrimitiveTask, CompoundTask
from .astar import AStar, DLite, LPAStar, AStarConfig
from .mapf import MAPFPlanner, MAPFConfig, ConflictBasedSearch
from .beam_search import BeamSearch, BeamSearchConfig
from .bidirectional import BidirectionalSearch, BidirectionalConfig
from .pddl_interface import PDDLPlanner, PDDLDomain, PDDLProblem, PDDLConfig
from .anytime_planning import AnytimePlanner, AnytimeConfig
from .receding_horizon import RecedingHorizonPlanner, RecedingHorizonConfig
from .dynamic_programming import DPPlanner, DPConfig
from .prm import PRMPlanner, PRMConfig
from .rrt import RRTPlanner, RRTConfig

__all__ = [
    "Planner", "PlanningAction", "PlanningDomain", "PlanningGoal", "PlanningResult",
    "MCTS", "MCTSConfig",
    "HTNPlanner", "HTNConfig", "Task", "Method", "PrimitiveTask", "CompoundTask",
    "AStar", "DLite", "LPAStar", "AStarConfig",
    "MAPFPlanner", "MAPFConfig", "ConflictBasedSearch",
    "BeamSearch", "BeamSearchConfig",
    "BidirectionalSearch", "BidirectionalConfig",
    "PDDLPlanner", "PDDLDomain", "PDDLProblem", "PDDLConfig",
    "AnytimePlanner", "AnytimeConfig",
    "RecedingHorizonPlanner", "RecedingHorizonConfig",
    "DPPlanner", "DPConfig",
    "PRMPlanner", "PRMConfig",
    "RRTPlanner", "RRTConfig",
]
