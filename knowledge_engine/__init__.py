# Copyright (c) Ultrone Contributors. All rights reserved.
"""Knowledge Engine — multi-layer knowledge system for the autonomous research platform.

Provides layered memory (semantic, episodic, working, procedural, research,
algorithm, project, experiment, long-term), knowledge graph, vector memory,
ontology, entity linking, citation database, RAG pipeline, cross-referencing,
and consolidation.

This package **extends** (never replaces) the existing ``brain/memory`` and
``brain/perception/knowledge`` modules by providing research-platform-aware
memory abstractions on top of them.
"""

from .base import KnowledgeEntry, KnowledgeSource, KnowledgeCategory, ConfidenceLevel
from .semantic_memory import SemanticKnowledgeMemory
from .episodic_memory import EpisodicKnowledgeMemory
from .working_memory import WorkingKnowledgeMemory
from .procedural_memory import ProceduralMemory
from .research_memory import ResearchMemory
from .algorithm_memory import AlgorithmMemory
from .project_memory import ProjectMemory
from .experiment_memory import ExperimentMemory
from .long_term_memory import LongTermMemory
from .knowledge_graph import KnowledgeGraph
from .vector_memory import VectorMemory
from .ontology import OntologyEngine
from .entity_linking import EntityLinker
from .citation_db import CitationDatabase
from .rag import RAGPipeline
from .cross_reference import CrossReferenceEngine
from .consolidation import KnowledgeConsolidation
from .memory_manager import KnowledgeMemoryManager

__all__ = [
    "KnowledgeEntry", "KnowledgeSource", "KnowledgeCategory", "ConfidenceLevel",
    "SemanticKnowledgeMemory", "EpisodicKnowledgeMemory", "WorkingKnowledgeMemory",
    "ProceduralMemory", "ResearchMemory", "AlgorithmMemory", "ProjectMemory",
    "ExperimentMemory", "LongTermMemory", "KnowledgeGraph", "VectorMemory",
    "OntologyEngine", "EntityLinker", "CitationDatabase", "RAGPipeline",
    "CrossReferenceEngine", "KnowledgeConsolidation", "KnowledgeMemoryManager",
]
