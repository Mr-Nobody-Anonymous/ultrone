# Copyright (c) Ultrone Contributors. All rights reserved.
"""Brain reasoning module - tactical analysis and decision making."""

from __future__ import annotations

from .tactical_engine import TacticalEngine
from .kill_chain import KillChain, KillChainPhase, KillChainStateMachine
from .kill_chain_capsule import KillChainCapsule, ActiveEvolutionManager
from .composite_kill_chain import CompositeKillChain, CompositePhase, DomainEngagement
from .course_of_action import CourseOfAction, COAGenerator, COAScorer, Action
from .resource_allocator import ResourceAllocator, Allocation
from .evolutionary_coagen import EvolutionaryGenome, EvolutionaryCOAGenerator

# Lazy-import search planners to keep startup fast
_SEARCH_IMPORTED = False

_search_mod = None

def _import_search():
    global _SEARCH_IMPORTED, _search_mod
    if not _SEARCH_IMPORTED:
        from . import search as _search_mod
        _SEARCH_IMPORTED = True
    return _search_mod

__all__ = [
    "TacticalEngine",
    "KillChain", "KillChainPhase", "KillChainStateMachine",
    "KillChainCapsule", "ActiveEvolutionManager",
    "CompositeKillChain", "CompositePhase", "DomainEngagement",
    "CourseOfAction", "COAGenerator", "COAScorer", "Action",
    "ResourceAllocator", "Allocation",
    "EvolutionaryGenome", "EvolutionaryCOAGenerator",
    # Search planners
    "Planner", "PlanningAction", "PlanningDomain", "PlanningGoal", "PlanningResult",
    "MCTS", "MCTSConfig",
    "HTNPlanner", "HTNConfig",
    "AStar", "DLite", "LPAStar", "AStarConfig",
    "MAPFPlanner", "MAPFConfig", "ConflictBasedSearch",
    "BeamSearch", "BeamSearchConfig",
    "BidirectionalSearch", "BidirectionalConfig",
    "PDDLPlanner", "PDDLDomain", "PDDLProblem", "PDDLConfig",
    "AnytimePlanner", "AnytimeConfig",
    "RecedingHorizonPlanner", "RecedingHorizonConfig",
    "DPPlanner", "DPConfig",
]


def __getattr__(name: str):
    """Lazy-load search planners when accessed."""
    search_names = {
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
    }
    if name in search_names:
        mod = _import_search()
        return getattr(mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
