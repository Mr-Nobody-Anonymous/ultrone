# Copyright (c) Ultrone Contributors. All rights reserved.
"""Autonomous Research Division — specialized AI agents for continuous
research discovery, analysis, and experimentation.

Agents communicate via asynchronous events on the message bus and
collaborate through the knowledge engine and research database.
"""

from .base_agent import ResearchAgent, ResearchAgentRole
from .coordinator import ResearchDivisionCoordinator
from .research_scout import ResearchScout
from .paper_analyzer import PaperAnalyzer
from .algorithm_extractor import AlgorithmExtractor
from .implementation_planner import ImplementationPlanner
from .code_generator import CodeGeneratorAgent
from .benchmark_agent import BenchmarkAgent
from .experiment_manager import ExperimentManagerAgent
from .knowledge_graph_builder import KnowledgeGraphBuilder
from .citation_manager import CitationManager
from .memory_manager import ResearchMemoryManagerAgent
from .quality_reviewer import QualityReviewer
from .safety_validator import SafetyValidator
from .performance_optimizer import PerformanceOptimizer
from .documentation_writer import DocumentationWriter
from .release_manager import ReleaseManager

__all__ = [
    "ResearchAgent",
    "ResearchAgentRole",
    "ResearchDivisionCoordinator",
    "ResearchScout",
    "PaperAnalyzer",
    "AlgorithmExtractor",
    "ImplementationPlanner",
    "CodeGeneratorAgent",
    "BenchmarkAgent",
    "ExperimentManagerAgent",
    "KnowledgeGraphBuilder",
    "CitationManager",
    "ResearchMemoryManagerAgent",
    "QualityReviewer",
    "SafetyValidator",
    "PerformanceOptimizer",
    "DocumentationWriter",
    "ReleaseManager",
]