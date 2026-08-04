# Copyright (c) Ultrone Contributors. All rights reserved.
"""Memory Systems module for multi-tier memory architecture.

Provides memory models beyond simple persistence:

- ``BaseMemory``: Abstract interface for memory systems
- ``EpisodicMemory``: Event-specific experience storage
- ``SemanticMemory``: General knowledge and concepts
- ``WorkingMemory``: Short-term active memory
- ``AssociativeMemory``: Pattern-based recall
- ``MemoryConsolidation``: Transfer between memory tiers
- ``ImportanceScorer``: Importance-based ranking of memories
- ``ForgettingEngine``: Decay & eviction policies
- ``MemoryCompressor``: Lossy memory compression
- ``MemorySummarizer``: Extractive summarization
- ``MemoryIndex``: Inverted index for retrieval
- ``RetrievalOptimizer``: Optimized retrieval with caching
"""

from .base import BaseMemory, MemoryConfig, MemoryItem
from .episodic_memory import EpisodicMemory, EpisodicConfig
from .semantic_memory import SemanticMemory, SemanticConfig
from .working_memory import WorkingMemory, WorkingMemoryConfig
from .associative_memory import AssociativeMemory, AssociativeConfig
from .memory_consolidation import MemoryConsolidation, ConsolidationConfig
from .importance import ImportanceScorer, ImportanceConfig
from .forgetting import ForgettingEngine, ForgettingConfig
from .compression import MemoryCompressor, CompressionConfig
from .summarization import MemorySummarizer, SummarizationConfig
from .memory_index import MemoryIndex, IndexConfig
from .retrieval_optimizer import RetrievalOptimizer, RetrievalConfig

__all__ = [
    "BaseMemory", "MemoryConfig", "MemoryItem",
    "EpisodicMemory", "EpisodicConfig",
    "SemanticMemory", "SemanticConfig",
    "WorkingMemory", "WorkingMemoryConfig",
    "AssociativeMemory", "AssociativeConfig",
    "MemoryConsolidation", "ConsolidationConfig",
    "ImportanceScorer", "ImportanceConfig",
    "ForgettingEngine", "ForgettingConfig",
    "MemoryCompressor", "CompressionConfig",
    "MemorySummarizer", "SummarizationConfig",
    "MemoryIndex", "IndexConfig",
    "RetrievalOptimizer", "RetrievalConfig",
]
