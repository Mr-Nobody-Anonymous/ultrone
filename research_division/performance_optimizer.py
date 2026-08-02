# Copyright (c) Ultrone Contributors. All rights reserved.
"""Performance Optimizer — analyzes performance, suggests optimizations,
and tracks resource usage across the research platform.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from comms.protocol import MessageType, Priority
from knowledge_engine.base import KnowledgeSource, KnowledgeCategory, ConfidenceLevel
from .base_agent import ResearchAgent, ResearchAgentRole

logger = logging.getLogger("Ultrone.ResearchDivision.Optimizer")


class PerformanceOptimizer(ResearchAgent):
    """Analyzes and optimizes platform performance."""

    def __init__(self, **kwargs):
        super().__init__(
            agent_id=kwargs.pop("agent_id", "performance-optimizer-001"),
            role=ResearchAgentRole.OPTIMIZER,
            **kwargs,
        )
        self.message_handlers[MessageType.RESEARCH_PERFORMANCE_OPTIMIZATION] = self._on_optimization_request

    async def run(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Analyze performance of all experiments and suggest optimizations."""
        experiments = self.research_db.list_experiments()
        analyses = []
        for experiment in experiments:
            if experiment.resource_usage:
                analysis = self._analyze_experiment_performance(experiment)
                analyses.append(analysis)

        self._log_action("optimization_cycle", {"analyses": len(analyses)}, None)
        return {"analyses": len(analyses), "results": analyses}

    def _on_optimization_request(self, message: Any) -> Any:
        experiment_id = message.content.get("experiment_id")
        experiment = self.research_db.get_experiment(experiment_id) if experiment_id else None
        if experiment:
            return self._analyze_experiment_performance(experiment)
        return None

    def _analyze_experiment_performance(self, experiment: Any) -> Dict[str, Any]:
        """Analyze experiment performance and suggest optimizations."""
        usage = experiment.resource_usage
        suggestions = []

        gpu_util = usage.get("gpu_utilization", 0)
        if gpu_util < 0.5:
            suggestions.append("GPU underutilized - consider increasing batch size")
        elif gpu_util > 0.95:
            suggestions.append("GPU overutilized - consider reducing batch size or using gradient accumulation")

        memory_gb = usage.get("memory_gb", 0)
        if memory_gb > 20:
            suggestions.append("High memory usage - consider mixed precision training")

        cpu_util = usage.get("cpu_utilization", 0)
        if cpu_util > 0.8:
            suggestions.append("High CPU usage - consider using more workers for data loading")

        if not suggestions:
            suggestions.append("Performance is well-balanced")

        analysis = {
            "experiment_id": experiment.experiment_id,
            "resource_usage": usage,
            "suggestions": suggestions,
            "efficiency_score": min(1.0, gpu_util * 0.5 + (1.0 - min(1.0, memory_gb / 32)) * 0.3 + 0.2),
        }

        self.knowledge.store_auto_categorized(
            content=f"Performance analysis for experiment '{experiment.experiment_id}': "
                    f"suggestions={suggestions}",
            source=KnowledgeSource.ANALYSIS,
            tags=["performance", "optimization"],
            entities=[experiment.experiment_id],
            confidence_score=0.75,
            layer="experiment",
            metadata={"experiment_id": experiment.experiment_id, "analysis": analysis},
        )

        self._log_action("performance_analyzed", {"experiment_id": experiment.experiment_id}, analysis)
        return analysis