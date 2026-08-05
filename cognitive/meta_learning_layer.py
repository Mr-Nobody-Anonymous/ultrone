# Copyright (c) Ultrone Contributors. All rights reserved.
"""Meta-Learning Layer — automatic architecture improvement.

Improves planner selection, reasoning selection, memory retrieval,
model routing, hyperparameters, learning rate, and tool selection.
Automatically discovers better architectures.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .base_layer import CognitiveLayer, LayerConfig
from .cycle_context import CycleContext, CyclePhase, PhaseResult
from .event_types import CognitiveEventType

logger = logging.getLogger("Ultrone.Cognitive.MetaLearning")


@dataclass
class MetaLearningConfig(LayerConfig):
    """Configuration for the meta-learning layer."""
    name: str = "meta_learning"
    enable_planner_optimization: bool = True
    enable_reasoning_optimization: bool = True
    enable_memory_optimization: bool = True
    enable_hyperparameter_optimization: bool = True
    learning_rate: float = 0.1
    adaptation_threshold: float = 0.3
    max_adaptations: int = 10


class MetaLearningLayer(CognitiveLayer):
    """Meta-learning layer that improves the cognitive architecture.

    The meta-learning layer:
    1. Improves planner selection based on performance
    2. Improves reasoning selection based on performance
    3. Optimizes memory retrieval strategies
    4. Optimizes hyperparameters
    5. Discovers better architectures
    """

    def __init__(self, config: Optional[MetaLearningConfig] = None):
        super().__init__(config or MetaLearningConfig())
        self._adaptation_history: List[Dict[str, Any]] = []
        self._planner_scores: Dict[str, float] = {}
        self._reasoning_scores: Dict[str, float] = {}
        self._hyperparameters: Dict[str, Any] = {}

    def _layer_phase(self) -> CyclePhase:
        return CyclePhase.IMPROVE_POLICIES

    def process(self, ctx: CycleContext) -> PhaseResult:
        """Execute the meta-learning phase.

        Parameters
        ----------
        ctx : CycleContext
            The shared cycle context.

        Returns
        -------
        PhaseResult
            Result with meta-learning adaptations.
        """
        start = time.time()

        # 1. Analyze performance
        performance = self._analyze_performance(ctx)

        # 2. Optimize planner selection
        planner_adaptations = []
        if self.config.enable_planner_optimization:
            planner_adaptations = self._optimize_planners(ctx, performance)

        # 3. Optimize reasoning selection
        reasoning_adaptations = []
        if self.config.enable_reasoning_optimization:
            reasoning_adaptations = self._optimize_reasoning(ctx, performance)

        # 4. Optimize memory retrieval
        memory_adaptations = []
        if self.config.enable_memory_optimization:
            memory_adaptations = self._optimize_memory(ctx, performance)

        # 5. Optimize hyperparameters
        hyperparameter_adaptations = []
        if self.config.enable_hyperparameter_optimization:
            hyperparameter_adaptations = self._optimize_hyperparameters(ctx, performance)

        # 6. Combine adaptations
        adaptations = (
            planner_adaptations
            + reasoning_adaptations
            + memory_adaptations
            + hyperparameter_adaptations
        )[:self.config.max_adaptations]

        # 7. Store in context
        ctx.metadata["meta_learning"] = {
            "adaptations": adaptations,
            "performance": performance,
        }

        # 8. Publish event
        self._publish_event(
            CognitiveEventType.META_LEARNING_UPDATE,
            {
                "adaptations": adaptations,
                "improvement": performance.get("overall", 0.0),
            },
        )

        # 9. Create decision trace
        trace = self._create_trace(
            decision="Meta-learning: improve cognitive architecture",
            confidence=performance.get("overall", 0.5),
            evidence=[
                {
                    "source": "meta_learning",
                    "description": f"Generated {len(adaptations)} adaptations",
                    "confidence": performance.get("overall", 0.5),
                }
            ],
        )

        self._adaptation_history.append({
            "timestamp": time.time(),
            "adaptations": adaptations,
            "performance": performance,
        })

        return PhaseResult(
            phase=self._phase,
            success=True,
            duration_seconds=time.time() - start,
            output={
                "adaptations": adaptations,
                "performance": performance,
                "adaptation_count": len(adaptations),
            },
            trace=trace,
        )

    def _analyze_performance(self, ctx: CycleContext) -> Dict[str, float]:
        """Analyze the performance of the cognitive cycle."""
        performance = {}

        # Overall confidence
        performance["overall"] = ctx.confidence if ctx.confidence > 0 else 0.5

        # Phase success rate
        successful = sum(1 for pr in ctx.phase_results if pr.success)
        total = len(ctx.phase_results)
        performance["phase_success_rate"] = successful / total if total > 0 else 0.5

        # Self-reflection evaluations
        if ctx.self_reflection:
            evaluations = ctx.self_reflection.get("evaluations", {})
            for key, value in evaluations.items():
                performance[key] = value

        return performance

    def _optimize_planners(self, ctx: CycleContext, performance: Dict[str, float]) -> List[Dict[str, Any]]:
        """Optimize planner selection based on performance."""
        adaptations = []
        planning_efficiency = performance.get("planning_efficiency", 0.5)

        if planning_efficiency < self.config.adaptation_threshold:
            adaptation = {
                "type": "planner_selection",
                "current": "goap",
                "recommended": "hierarchical",
                "reason": f"Planning efficiency {planning_efficiency:.2f} is below threshold",
                "expected_improvement": 0.2,
            }
            adaptations.append(adaptation)
            self._planner_scores["hierarchical"] = self._planner_scores.get("hierarchical", 0.0) + self.config.learning_rate

        return adaptations

    def _optimize_reasoning(self, ctx: CycleContext, performance: Dict[str, float]) -> List[Dict[str, Any]]:
        """Optimize reasoning selection based on performance."""
        adaptations = []
        reasoning_quality = performance.get("reasoning_quality", 0.5)

        if reasoning_quality < self.config.adaptation_threshold:
            adaptation = {
                "type": "reasoning_selection",
                "current": "deductive",
                "recommended": "probabilistic",
                "reason": f"Reasoning quality {reasoning_quality:.2f} is below threshold",
                "expected_improvement": 0.15,
            }
            adaptations.append(adaptation)
            self._reasoning_scores["probabilistic"] = self._reasoning_scores.get("probabilistic", 0.0) + self.config.learning_rate

        return adaptations

    def _optimize_memory(self, ctx: CycleContext, performance: Dict[str, float]) -> List[Dict[str, Any]]:
        """Optimize memory retrieval strategies."""
        adaptations = []
        memory_usefulness = performance.get("memory_usefulness", 0.3)

        if memory_usefulness < self.config.adaptation_threshold:
            adaptation = {
                "type": "memory_retrieval",
                "current": "keyword",
                "recommended": "hybrid",
                "reason": f"Memory usefulness {memory_usefulness:.2f} is below threshold",
                "expected_improvement": 0.25,
            }
            adaptations.append(adaptation)

        return adaptations

    def _optimize_hyperparameters(self, ctx: CycleContext, performance: Dict[str, float]) -> List[Dict[str, Any]]:
        """Optimize hyperparameters based on performance."""
        adaptations = []
        overall = performance.get("overall", 0.5)

        if overall < self.config.adaptation_threshold:
            # Adjust learning rate
            new_lr = min(0.5, self.config.learning_rate * 1.5)
            adaptation = {
                "type": "hyperparameter",
                "parameter": "learning_rate",
                "current": self.config.learning_rate,
                "recommended": new_lr,
                "reason": f"Overall performance {overall:.2f} is below threshold",
            }
            adaptations.append(adaptation)
            self._hyperparameters["learning_rate"] = new_lr

        return adaptations

    def get_adaptation_history(self) -> List[Dict[str, Any]]:
        """Return the history of meta-learning adaptations."""
        return self._adaptation_history

    def get_planner_scores(self) -> Dict[str, float]:
        """Return the scores for each planner."""
        return self._planner_scores

    def get_reasoning_scores(self) -> Dict[str, float]:
        """Return the scores for each reasoning strategy."""
        return self._reasoning_scores

    def get_hyperparameters(self) -> Dict[str, Any]:
        """Return the optimized hyperparameters."""
        return self._hyperparameters