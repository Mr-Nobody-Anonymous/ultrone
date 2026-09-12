# Copyright (c) Ultrone Contributors. All rights reserved.
"""Research Division Coordinator — orchestrates all research agents.

Coordinates the full research pipeline: discovery → analysis → extraction →
planning → code generation → benchmarking → experimentation → review →
release. Manages agent lifecycle and event routing.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from knowledge_engine.memory_manager import KnowledgeMemoryManager
from research_db.store import ResearchDatabase
from .base_agent import ResearchAgent, ResearchAgentRole
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

logger = logging.getLogger("Ultrone.ResearchDivision.Coordinator")


class ResearchDivisionCoordinator(ResearchAgent):
    """Orchestrates the full autonomous research pipeline."""

    def __init__(
        self,
        message_bus: Optional[Any] = None,
        knowledge: Optional[KnowledgeMemoryManager] = None,
        research_db: Optional[ResearchDatabase] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            agent_id="research-coordinator-001",
            role=ResearchAgentRole.COORDINATOR,
            message_bus=message_bus,
            knowledge=knowledge,
            research_db=research_db,
            config=config,
        )

        # Create all specialized agents
        self.agents: Dict[str, ResearchAgent] = {
            "scout": ResearchScout(
                message_bus=message_bus, knowledge=knowledge, research_db=research_db, config=config
            ),
            "analyzer": PaperAnalyzer(
                message_bus=message_bus, knowledge=knowledge, research_db=research_db, config=config
            ),
            "extractor": AlgorithmExtractor(
                message_bus=message_bus, knowledge=knowledge, research_db=research_db, config=config
            ),
            "planner": ImplementationPlanner(
                message_bus=message_bus, knowledge=knowledge, research_db=research_db, config=config
            ),
            "codegen": CodeGeneratorAgent(
                message_bus=message_bus, knowledge=knowledge, research_db=research_db, config=config
            ),
            "benchmark": BenchmarkAgent(
                message_bus=message_bus, knowledge=knowledge, research_db=research_db, config=config
            ),
            "experiment": ExperimentManagerAgent(
                message_bus=message_bus, knowledge=knowledge, research_db=research_db, config=config
            ),
            "graph": KnowledgeGraphBuilder(
                message_bus=message_bus, knowledge=knowledge, research_db=research_db, config=config
            ),
            "citation": CitationManager(
                message_bus=message_bus, knowledge=knowledge, research_db=research_db, config=config
            ),
            "memory": ResearchMemoryManagerAgent(
                message_bus=message_bus, knowledge=knowledge, research_db=research_db, config=config
            ),
            "reviewer": QualityReviewer(
                message_bus=message_bus, knowledge=knowledge, research_db=research_db, config=config
            ),
            "safety": SafetyValidator(
                message_bus=message_bus, knowledge=knowledge, research_db=research_db, config=config
            ),
            "optimizer": PerformanceOptimizer(
                message_bus=message_bus, knowledge=knowledge, research_db=research_db, config=config
            ),
            "writer": DocumentationWriter(
                message_bus=message_bus, knowledge=knowledge, research_db=research_db, config=config
            ),
            "release": ReleaseManager(
                message_bus=message_bus, knowledge=knowledge, research_db=research_db, config=config
            ),
        }

    async def run(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Execute the full research pipeline.

        Pipeline: scout → analyze → extract → plan → codegen → benchmark →
        experiment → review → safety → optimize → document → release.
        """
        results: Dict[str, Any] = {}

        # Phase 1: Discovery
        results["scout"] = await self.agents["scout"].run(**kwargs)

        # Phase 2: Analysis
        results["analyzer"] = await self.agents["analyzer"].run(**kwargs)

        # Phase 3: Extraction
        results["extractor"] = await self.agents["extractor"].run(**kwargs)

        # Phase 4: Planning
        results["planner"] = await self.agents["planner"].run(**kwargs)

        # Phase 5: Code generation
        results["codegen"] = await self.agents["codegen"].run(**kwargs)

        # Phase 6: Benchmarking
        results["benchmark"] = await self.agents["benchmark"].run(**kwargs)

        # Phase 7: Experimentation
        results["experiment"] = await self.agents["experiment"].run(**kwargs)

        # Phase 8: Knowledge graph & citations
        results["graph"] = await self.agents["graph"].run(**kwargs)
        results["citation"] = await self.agents["citation"].run(**kwargs)

        # Phase 9: Memory consolidation
        results["memory"] = await self.agents["memory"].run(**kwargs)

        # Phase 10: Review & safety
        results["reviewer"] = await self.agents["reviewer"].run(**kwargs)
        results["safety"] = await self.agents["safety"].run(**kwargs)

        # Phase 11: Optimization
        results["optimizer"] = await self.agents["optimizer"].run(**kwargs)

        # Phase 12: Documentation
        results["writer"] = await self.agents["writer"].run(**kwargs)

        # Phase 13: Release proposals
        results["release"] = await self.agents["release"].run(**kwargs)

        self._log_action("pipeline_complete", {"phases": list(results.keys())}, results)
        return results

    async def run_phase(self, phase: str, **kwargs: Any) -> Dict[str, Any]:
        """Run a single phase of the research pipeline."""
        agent = self.agents.get(phase)
        if agent is None:
            raise ValueError(f"Unknown research phase: {phase}")
        result = await agent.run(**kwargs)
        self._log_action("phase_complete", {"phase": phase}, result)
        return result

    def get_agent(self, name: str) -> Optional[ResearchAgent]:
        """Get a specific agent by name."""
        return self.agents.get(name)

    def get_all_agents(self) -> Dict[str, ResearchAgent]:
        """Get all agents."""
        return self.agents

    def get_stats(self) -> Dict[str, Any]:
        """Get coordinator and agent statistics."""
        return {
            "coordinator": super().get_stats(),
            "agents": {name: agent.get_stats() for name, agent in self.agents.items()},
        }
