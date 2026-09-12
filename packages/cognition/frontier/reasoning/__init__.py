# Copyright (c) Ultrone Contributors. All rights reserved.
"""Frontier Reasoning Strategies.

A collection of state-of-the-art LLM reasoning strategies, provided as
pluggable, backend-agnostic components. Each strategy accepts a ``Solver``
(a callable that maps a prompt to a solution) and optional ``Verifier``/
callables, making them usable with any LLM provider or test double.

Implemented strategies
----------------------
- Tree of Thoughts (ToT)
- Graph of Thoughts (GoT)
- Self-Consistency voting
- Multi-Agent Debate
- Constitutional Critique
- Beam Search Reasoner
"""

from .base import (
    ReasoningResult,
    ReasoningStrategy,
    ReasoningTrace,
    Solver,
    Verification,
    Verifier,
)
from .tree_of_thoughts import TreeOfThoughts, ToTConfig
from .graph_of_thoughts import GraphOfThoughts, GoTConfig
from .self_consistency import SelfConsistency, SelfConsistencyConfig
from .multi_agent_debate import MultiAgentDebate, DebateConfig
from .constitutional_critique import ConstitutionalCritique, ConstitutionalCritiqueConfig
from .beam_search_reasoner import BeamSearchReasoner, BeamSearchConfig

__all__ = [
    "Solver",
    "Verifier",
    "Verification",
    "ReasoningResult",
    "ReasoningTrace",
    "ReasoningStrategy",
    "TreeOfThoughts",
    "ToTConfig",
    "GraphOfThoughts",
    "GoTConfig",
    "SelfConsistency",
    "SelfConsistencyConfig",
    "MultiAgentDebate",
    "DebateConfig",
    "ConstitutionalCritique",
    "ConstitutionalCritiqueConfig",
    "BeamSearchReasoner",
    "BeamSearchConfig",
]
