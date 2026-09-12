# Copyright (c) Ultrone Contributors. All rights reserved.
"""Advanced reasoning engines for state-of-the-art AI performance.

Implements:
- Tree of Thoughts (ToT)
- Graph of Thoughts (GoT)
- Beam Search Reasoner
- Self-Consistency Voting
- Multi-Agent Debate
- Constitutional Critique
- Chain of Thought (CoT)
- ReAct (Reasoning + Acting)
"""

from __future__ import annotations

from .tree_of_thoughts import TreeOfThoughts, ToTConfig, ThoughtNode
from .graph_of_thoughts import GraphOfThoughts, GoTConfig, ThoughtGraph
from .beam_search_reasoner import BeamSearchReasoner, BeamSearchConfig
from .self_consistency import SelfConsistencyVoting, ConsistencyConfig
from .multi_agent_debate import MultiAgentDebate, DebateConfig
from .constitutional_critique import ConstitutionalCritique, CritiqueConfig
from .chain_of_thought import ChainOfThought, CoTConfig
from .react_agent import ReActAgent, ReActConfig

__all__ = [
    "TreeOfThoughts", "ToTConfig", "ThoughtNode",
    "GraphOfThoughts", "GoTConfig", "ThoughtGraph",
    "BeamSearchReasoner", "BeamSearchConfig",
    "SelfConsistencyVoting", "ConsistencyConfig",
    "MultiAgentDebate", "DebateConfig",
    "ConstitutionalCritique", "CritiqueConfig",
    "ChainOfThought", "CoTConfig",
    "ReActAgent", "ReActConfig",
]