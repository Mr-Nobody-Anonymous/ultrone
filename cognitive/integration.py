# Copyright (c) Ultrone Contributors. All rights reserved.
"""Cognitive Integration — unified cognitive architecture facade.

Provides a single entry point for the entire cognitive architecture,
integrating all cognitive layers with the brain, knowledge engine, and
research platform. Exposes a unified API for perception, reasoning,
planning, prediction, learning, and self-reflection.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .active_inference_layer import ActiveInferenceLayer, ActiveInferenceConfig
from .agentic_layer import AgenticLayer, AgenticLayerConfig
from .base_layer import CognitiveLayer, LayerConfig
from .cognitive_agent import CognitiveAgent, CognitiveAgentConfig
from .cognitive_loop import CognitiveLoop, CognitiveLoopConfig
from .cycle_context import CycleContext, CyclePhase, PhaseResult
from .event_types import CognitiveEvent, CognitiveEventType, EventBus
from .explainability_layer import ExplainabilityLayer, ExplainabilityLayerConfig
from .knowledge_layer import KnowledgeLayer, KnowledgeLayerConfig
from .learning_layer import LearningLayer, LearningLayerConfig
from .memory_layer import MemoryLayer, MemoryLayerConfig
from .meta_learning_layer import MetaLearningLayer, MetaLearningConfig
from .perception_layer import PerceptionLayer, PerceptionLayerConfig
from .planning_layer import PlanningLayer, PlanningLayerConfig
from .prediction_layer import PredictionLayer, PredictionLayerConfig
from .reasoning_layer import ReasoningLayer, ReasoningLayerConfig
from .safety_layer import SafetyLayer, SafetyLayerConfig
from .self_reflection_layer import SelfReflectionLayer, SelfReflectionConfig
from .situational_awareness_layer import SituationalAwarenessLayer, SituationalAwarenessConfig
from .types import (
    Action,
    CognitiveContext,
    DecisionTrace,
    Observation,
)
from .world_model_layer import WorldModelLayer, WorldModelLayerConfig

logger = logging.getLogger("Ultrone.Cognitive.Integration")


@dataclass
class CognitiveIntegrationConfig:
    """Configuration for the cognitive integration."""
    agent_id: str = "ultrone-cognitive"
    enable_perception: bool = True
    enable_situational_awareness: bool = True
    enable_world_model: bool = True
    enable_memory: bool = True
    enable_knowledge: bool = True
    enable_reasoning: bool = True
    enable_prediction: bool = True
    enable_planning: bool = True
    enable_self_reflection: bool = True
    enable_meta_learning: bool = True
    enable_agentic: bool = True
    enable_learning: bool = True
    enable_explainability: bool = True
    enable_safety: bool = True
    event_bus: Optional[EventBus] = None
    layer_overrides: Dict[str, CognitiveLayer] = field(default_factory=dict)


class CognitiveIntegration:
    """Unified facade for the ULTRONE cognitive architecture.

    The cognitive integration:
    1. Composes all cognitive layers into a unified system
    2. Provides a single API for all cognitive operations
    3. Integrates with the broader ULTRONE ecosystem
    4. Exposes explainability and safety monitoring
    5. Enables benchmarking and evaluation
    """

    def __init__(self, config: Optional[CognitiveIntegrationConfig] = None):
        self.config = config or CognitiveIntegrationConfig()
        self.event_bus = self.config.event_bus or EventBus()

        # Build the cognitive agent
        self.agent = CognitiveAgent(CognitiveAgentConfig(
            agent_id=self.config.agent_id,
            event_bus=self.event_bus,
            layer_overrides=self.config.layer_overrides,
        ))

        # Expose layers for direct access
        self.layers = self.agent.loop._layers_by_phase

        # Set up event subscriptions
        self._event_handlers: Dict[CognitiveEventType, List[Callable]] = {}
        self._subscribe_default_handlers()

        # Integration state
        self._integrated_components: Dict[str, Any] = {}
        self._benchmark_results: List[Dict[str, Any]] = []

    def _subscribe_default_handlers(self) -> None:
        """Subscribe to default event handlers."""
        self.event_bus.subscribe_any(self._on_any_event)

    def _on_any_event(self, event: CognitiveEvent) -> None:
        """Handle any cognitive event."""
        handlers = self._event_handlers.get(event.event_type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.warning("Event handler failed for %s: %s", event.event_type.value, e)

    def subscribe(self, event_type: CognitiveEventType, handler: Callable) -> None:
        """Subscribe to a specific cognitive event type."""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)

    def register_component(self, name: str, component: Any) -> None:
        """Register an external component for integration."""
        self._integrated_components[name] = component

    def get_component(self, name: str) -> Optional[Any]:
        """Get a registered component."""
        return self._integrated_components.get(name)

    async def perceive_and_decide(
        self,
        observation: Observation,
        goals: Optional[List[str]] = None,
        context: Optional[CognitiveContext] = None,
    ) -> CycleContext:
        """Full cognitive cycle: perceive, reason, plan, and act.

        Parameters
        ----------
        observation : Observation
            The observation to process.
        goals : list of str, optional
            Goals for this cycle.
        context : CognitiveContext, optional
            Additional cognitive context.

        Returns
        -------
        CycleContext
            The completed cognitive cycle.
        """
        return await self.agent.decide(observation, goals, context)

    async def run_cycle(
        self,
        observation: Observation,
        context: Optional[CognitiveContext] = None,
    ) -> CycleContext:
        """Run a single cognitive cycle.

        Parameters
        ----------
        observation : Observation
            The observation to process.
        context : CognitiveContext, optional
            The cognitive context.

        Returns
        -------
        CycleContext
            The completed cognitive cycle.
        """
        return await self.agent.perceive(observation)

    async def run_benchmark(
        self,
        benchmark_name: str,
        observations: List[Observation],
        goals: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Run a benchmark against the cognitive architecture.

        Parameters
        ----------
        benchmark_name : str
            Name of the benchmark.
        observations : list of Observation
            Observations to process.
        goals : list of str, optional
            Goals for the benchmark.

        Returns
        -------
        dict
            Benchmark results.
        """
        start = time.time()
        results = []
        total_confidence = 0.0
        total_uncertainty = 0.0

        for obs in observations:
            ctx = await self.agent.perceive(obs)
            results.append(ctx)
            total_confidence += ctx.confidence
            total_uncertainty += ctx.uncertainty

        duration = time.time() - start
        benchmark_result = {
            "name": benchmark_name,
            "cycles": len(observations),
            "total_duration": duration,
            "avg_cycle_time": duration / max(1, len(observations)),
            "avg_confidence": total_confidence / max(1, len(observations)),
            "avg_uncertainty": total_uncertainty / max(1, len(observations)),
            "success_rate": (
                sum(1 for ctx in results if all(pr.success for pr in ctx.phase_results))
                / max(1, len(results))
            ),
            "layers": self.agent.loop.get_stats()["layers"],
        }

        self._benchmark_results.append(benchmark_result)
        return benchmark_result

    def get_stats(self) -> Dict[str, Any]:
        """Return integration statistics."""
        stats = {
            "agent": self.agent.get_stats(),
            "components": list(self._integrated_components.keys()),
            "benchmarks": len(self._benchmark_results),
            "event_handlers": {
                et.value: len(handlers)
                for et, handlers in self._event_handlers.items()
            },
        }
        return stats

    def get_benchmark_results(self) -> List[Dict[str, Any]]:
        """Return all benchmark results."""
        return self._benchmark_results

    def get_layers(self, phase: CyclePhase) -> List[CognitiveLayer]:
        """Get all layers for a phase."""
        return self.layers.get(phase, [])