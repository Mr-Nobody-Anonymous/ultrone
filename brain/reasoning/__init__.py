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

__all__ = [
    "TacticalEngine",
    "KillChain", "KillChainPhase", "KillChainStateMachine",
    "KillChainCapsule", "ActiveEvolutionManager",
    "CompositeKillChain", "CompositePhase", "DomainEngagement",
    "CourseOfAction", "COAGenerator", "COAScorer", "Action",
    "ResourceAllocator", "Allocation",
    "EvolutionaryGenome", "EvolutionaryCOAGenerator",
]