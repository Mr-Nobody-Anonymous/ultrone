# Copyright (c) Ultrone Contributors. All rights reserved.
"""Memory Systems module for multi-tier memory architecture.

Provides memory models beyond simple persistence:

- ``BaseMemory``: Abstract interface for memory systems
- ``EpisodicMemory``: Event-specific experience storage
- ``SemanticMemory``: General knowledge and concepts
- ``WorkingMemory``: Short-term active memory
- ``AssociativeMemory``: Pattern-based recall
- ``MemoryConsolidation``: Transfer between memory tiers
"""

from .base import BaseMemory, MemoryConfig, MemoryItem
from .episodic_memory import EpisodicMemory, EpisodicConfig
from .semantic_memory import SemanticMemory, SemanticConfig
from .working_memory import WorkingMemory, WorkingMemoryConfig
from .associative_memory import AssociativeMemory, AssociativeConfig
from .memory_consolidation import MemoryConsolidation, ConsolidationConfig

__all__ = [
    "BaseMemory", "MemoryConfig", "MemoryItem",
    "EpisodicMemory", "EpisodicConfig",
    "SemanticMemory", "SemanticConfig",
    "WorkingMemory", "WorkingMemoryConfig",
    "AssociativeMemory", "AssociativeConfig",
    "MemoryConsolidation", "ConsolidationConfig",
]