# Copyright (c) Ultrone Contributors. All rights reserved.
"""Cognitive Agent — unified cognitive agent with full loop integration.

A complete cognitive agent that integrates perception, memory, world
modeling, reasoning, planning, prediction, learning, and self-reflection
into a single autonomous system. Exposes the full cognitive loop with
explainability and safety monitoring.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .base_layer import CognitiveLayer, LayerConfig
from .cognitive_loop import CognitiveLoop, CognitiveLoopConfig
from .cycle_context import CycleContext, CyclePhase
from .event_types import EventBus
from .types import Action, CognitiveContext, Observation

logger = logging.getLogger("Ultrone.Cognitive.Agent")


@dataclass
class CognitiveAgentConfig:
    """Configuration for the cognitive agent."""
    agent_id: str = "cognitive-agent"
    name: str = "Cognitive Agent"
    enable_autonomous_loop: bool = True
    max_cycles: int = 100
    cycle_interval_seconds: float = 1.0
    event_bus: Optional[EventBus] = None
    layer_overrides: Dict[str, CognitiveLayer] = field(default_factory=dict)
    loop_config: Optional[CognitiveLoopConfig] = None


class CognitiveAgent:
    """A complete autonomous cognitive agent.

    The cognitive agent:
    1. Composes all cognitive layers into a unified loop
    2. Runs the cognitive loop autonomously
    3. Processes observations and generates actions
    4. Provides full explainability traces
    5. Monitors safety and robustness
    """

    def __init__(self, config: Optional[CognitiveAgentConfig] = None):
        self.config = config or CognitiveAgentConfig()
        self.event_bus = self.config.event_bus or EventBus()

        # Build the cognitive loop with all layers
        self.loop = self._build_loop()

        # Agent state
        self._observations: List[Observation] = []
        self._actions: List[Action] = []
        self._cycle_contexts: List[CycleContext] = []
        self._is_running: bool = False
        self._cycle_count: int = 0

    def _build_loop(self) -> CognitiveLoop:
        """Build the cognitive loop with all standard layers."""
        from .active_inference_layer import ActiveInferenceLayer, ActiveInferenceConfig
        from .agentic_layer import AgenticLayer, AgenticLayerConfig
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
        from .world_model_layer import WorldModelLayer, WorldModelLayerConfig

        layers = {
            "perception": PerceptionLayer(PerceptionLayerConfig(event_bus=self.event_bus)),
            "situational_awareness": SituationalAwarenessLayer(SituationalAwarenessConfig(event_bus=self.event_bus)),
            "world_model": WorldModelLayer(WorldModelLayerConfig(event_bus=self.event_bus)),
            "memory": MemoryLayer(MemoryLayerConfig(event_bus=self.event_bus)),
            "knowledge": KnowledgeLayer(KnowledgeLayerConfig(event_bus=self.event_bus)),
            "active_inference": ActiveInferenceLayer(ActiveInferenceConfig(event_bus=self.event_bus)),
            "reasoning": ReasoningLayer(ReasoningLayerConfig(event_bus=self.event_bus)),
            "prediction": PredictionLayer(PredictionLayerConfig(event_bus=self.event_bus)),
            "planning": PlanningLayer(PlanningLayerConfig(event_bus=self.event_bus)),
            "self_reflection": SelfReflectionLayer(SelfReflectionConfig(event_bus=self.event_bus)),
            "meta_learning": MetaLearningLayer(MetaLearningConfig(event_bus=self.event_bus)),
            "agentic": AgenticLayer(AgenticLayerConfig(event_bus=self.event_bus)),
            "learning": LearningLayer(LearningLayerConfig(event_bus=self.event_bus)),
            "explainability": ExplainabilityLayer(ExplainabilityLayerConfig(event_bus=self.event_bus)),
        }

        # Apply overrides
        for name, layer in self.config.layer_overrides.items():
            if name in layers:
                layers[name] = layer
            else:
                layers[name] = layer

        # Safety layer
        safety_layer = SafetyLayer(SafetyLayerConfig(event_bus=self.event_bus))

        loop_config = self.config.loop_config or CognitiveLoopConfig(
            layers=layers,
            safety_layer=safety_layer,
            event_bus=self.event_bus,
        )
        loop_config.layers = layers
        loop_config.safety_layer = safety_layer
        loop_config.event_bus = self.event_bus

        return CognitiveLoop(loop_config)

    async def perceive(self, observation: Observation) -> CycleContext:
        """Process a single observation through the cognitive loop.

        Parameters
        ----------
        observation : Observation
            The observation to process.

        Returns
        -------
        CycleContext
            The completed cognitive cycle context.
        """
        context = CognitiveContext(
            session_id=self.config.agent_id,
        )

        ctx = await self.loop.run_cycle(observation=observation, context=context)

        self._observations.append(observation)
        self._cycle_contexts.append(ctx)
        self._cycle_count += 1

        return ctx

    async def decide(
        self,
        observation: Observation,
        goals: Optional[List[str]] = None,
        context: Optional[CognitiveContext] = None,
    ) -> List[Action]:
        """Process an observation and produce actions.

        Parameters
        ----------
        observation : Observation
            The observation to process.
        goals : list of str, optional
            Goals for this decision cycle.
        context : CognitiveContext, optional
            Additional cognitive context.

        Returns
        -------
        list of Action
            The actions to execute.
        """
        if context is None:
            context = CognitiveContext(
                goals=goals or [],
                session_id=self.config.agent_id,
            )
        elif goals:
            context.goals = goals

        ctx = await self.loop.run_cycle(observation=observation, context=context)

        self._observations.append(observation)
        self._cycle_contexts.append(ctx)
        self._cycle_count += 1

        return ctx.actions

    async def run_autonomous(
        self,
        observation_provider: Any,
        max_cycles: Optional[int] = None,
    ) -> List[CycleContext]:
        """Run the cognitive agent autonomously.

        Parameters
        ----------
        observation_provider : callable
            A callable that returns observations (can be async).
        max_cycles : int, optional
            Maximum number of cycles to run.

        Returns
        -------
        list of CycleContext
            All completed cycle contexts.
        """
        if not self.config.enable_autonomous_loop:
            return []

        max_cycles = max_cycles or self.config.max_cycles
        contexts = []

        for _ in range(max_cycles):
            observation = observation_provider()
            if observation is None:
                break

            context = CognitiveContext(session_id=self.config.agent_id)
            ctx = await self.loop.run_cycle(observation=observation, context=context)
            contexts.append(ctx)

            import asyncio
            await asyncio.sleep(self.config.cycle_interval_seconds)

        return contexts

    def get_stats(self) -> Dict[str, Any]:
        """Return agent statistics."""
        return {
            "agent_id": self.config.agent_id,
            "name": self.config.name,
            "cycles_run": self._cycle_count,
            "observations": len(self._observations),
            "actions": self._actions,
            "cognitive_loop": self.loop.get_stats(),
        }

    def get_cycle_contexts(self) -> List[CycleContext]:
        """Return all cycle contexts."""
        return self._cycle_contexts

    def get_decision_traces(self) -> List[Any]:
        """Return all decision traces."""
        return self.loop.get_decision_traces()

    def get_actions(self) -> List[Action]:
        """Return all actions."""
        return self._actions