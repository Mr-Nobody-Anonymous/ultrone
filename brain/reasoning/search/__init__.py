# Copyright (c) Ultrone Contributors. All rights reserved.
"""Search & Planning algorithms module.

Provides interchangeable planners for tactical decision-making:

- ``MCTS``: Monte Carlo Tree Search for stochastic planning
- ``HTN``: Hierarchical Task Networks for structured decomposition
- ``AStar`` / ``DLite``: Classic heuristic search with incremental replanning
- ``LPAStar``: Lifelong Planning A* for dynamic environments
- ``MAPF``: Multi-Agent Path Finding with Conflict-Based Search
- ``BeamSearch``: Width-limited heuristic search
- ``BestFirstSearch``: Priority-queue-based informed search
- ``BidirectionalSearch``: Symmetric forward-backward search
- ``PDDLPlanner``: STRIPS/PDDL grounded action planning
- ``RRTPlanner``: RRT/RRT* for sampling-based motion planning 🆕
- ``PRMPlanner``: Probabilistic Roadmap for multi-query planning 🆕

All planners implement the ``Planner`` abstract base class and are
interchangeable via dependency injection in :class:`~brain.reasoning.tactical_engine.TacticalEngine`.
"""

from .base import Planner, PlanningDomain, PlanningGoal, PlanningResult, PlanningAction
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
from .rrt import RRTPlanner, RRTConfig
from .prm import PRMPlanner, PRMConfig

__all__ = [
    # Base
    "Planner", "PlanningDomain", "PlanningGoal", "PlanningResult", "PlanningAction",
    # MCTS
    "MCTS", "MCTSConfig",
    # HTN
    "HTNPlanner", "HTNConfig", "Task", "Method", "PrimitiveTask", "CompoundTask",
    # A* / D* / LPA*
    "AStar", "DLite", "LPAStar", "AStarConfig",
    # MAPF
    "MAPFPlanner", "MAPFConfig", "ConflictBasedSearch",
    # Beam / Best-First
    "BeamSearch", "BeamSearchConfig",
    "BidirectionalSearch", "BidirectionalConfig",
    # PDDL
    "PDDLPlanner", "PDDLDomain", "PDDLProblem", "PDDLConfig",
    # Anytime / Receding Horizon / DP
    "AnytimePlanner", "AnytimeConfig",
    "RecedingHorizonPlanner", "RecedingHorizonConfig",
    "DPPlanner", "DPConfig",
    # RRT / PRM
    "RRTPlanner", "RRTConfig",
    "PRMPlanner", "PRMConfig",
]
