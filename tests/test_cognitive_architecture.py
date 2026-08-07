# Copyright (c) Ultrone Contributors. All rights reserved.
"""Comprehensive tests for the ULTRONE cognitive architecture.

Tests the full cognitive loop with all layers:
- Perception → Situational Awareness → World Model → Active Inference →
- Memory → Knowledge → Reasoning → Prediction → Planning →
- Self-Reflection → Meta-Learning → Agentic → Learning →
- Explainability → Safety
"""

from __future__ import annotations

import asyncio
import logging
import unittest
from typing import Any, Dict, List

from cognitive import (
    # Core
    CognitiveAgent,
    CognitiveAgentConfig,
    CognitiveIntegration,
    CognitiveIntegrationConfig,
    CognitiveLoop,
    CognitiveLoopConfig,
    CycleContext,
    CyclePhase,
    EventBus,
    # Types
    Action,
    CognitiveContext,
    Modality,
    Observation,
    SceneGraph,
    SceneGraphNode,
    SceneGraphEdge,
    UncertaintyEstimate,
    # Layers
    PerceptionLayer,
    PerceptionLayerConfig,
    SituationalAwarenessLayer,
    SituationalAwarenessConfig,
    WorldModelLayer,
    WorldModelLayerConfig,
    ActiveInferenceLayer,
    ActiveInferenceConfig,
    MemoryLayer,
    MemoryLayerConfig,
    KnowledgeLayer,
    KnowledgeLayerConfig,
    ReasoningLayer,
    ReasoningLayerConfig,
    PlanningLayer,
    PlanningLayerConfig,
    PredictionLayer,
    PredictionLayerConfig,
    SelfReflectionLayer,
    SelfReflectionConfig,
    MetaLearningLayer,
    MetaLearningConfig,
    AgenticLayer,
    AgenticLayerConfig,
    LearningLayer,
    LearningLayerConfig,
    ExplainabilityLayer,
    ExplainabilityLayerConfig,
    SafetyLayer,
    SafetyLayerConfig,
)

logger = logging.getLogger("Ultrone.CognitiveTests")


def make_observation(
    text: str = "test observation",
    confidence: float = 0.9,
    modality: Modality = Modality.TEXT,
) -> Observation:
    """Create a test observation."""
    return Observation(
        modalities={modality: text},
        confidence=confidence,
        source="test",
    )


class TestPerceptionLayer(unittest.TestCase):
    """Test the perception layer."""

    def setUp(self):
        self.layer = PerceptionLayer(PerceptionLayerConfig())

    def test_process_with_observation(self):
        """Test processing an observation."""
        obs = make_observation()
        ctx = CycleContext()
        ctx.observations.append(obs)

        result = self.layer.process(ctx)
        self.assertTrue(result.success)
        self.assertIsNotNone(ctx.scene_graph)
        self.assertGreater(len(ctx.scene_graph.nodes), 0)

    def test_process_without_observation(self):
        """Test processing without observations."""
        ctx = CycleContext()
        result = self.layer.process(ctx)
        self.assertTrue(result.success)
        self.assertIsNone(ctx.scene_graph)

    def test_anomaly_detection(self):
        """Test anomaly detection."""
        obs = make_observation(confidence=0.2)
        ctx = CycleContext()
        ctx.observations.append(obs)

        result = self.layer.process(ctx)
        self.assertTrue(result.success)
        self.assertGreater(len(self.layer.get_anomalies()), 0)

    def test_scene_graph_history(self):
        """Test scene graph history."""
        obs = make_observation()
        ctx = CycleContext()
        ctx.observations.append(obs)
        self.layer.process(ctx)

        self.assertEqual(len(self.layer.get_scene_graph_history()), 1)


class TestSituationalAwarenessLayer(unittest.TestCase):
    """Test the situational awareness layer."""

    def setUp(self):
        self.perception = PerceptionLayer(PerceptionLayerConfig())
        self.layer = SituationalAwarenessLayer(SituationalAwarenessConfig())

    def test_process_with_scene_graph(self):
        """Test processing with a scene graph."""
        obs = make_observation()
        ctx = CycleContext()
        ctx.observations.append(obs)
        self.perception.process(ctx)

        result = self.layer.process(ctx)
        self.assertTrue(result.success)
        self.assertIsNotNone(ctx.situational_context)
        self.assertGreater(len(ctx.situational_context.entities), 0)

    def test_entity_tracking(self):
        """Test entity tracking."""
        obs = make_observation()
        ctx = CycleContext()
        ctx.observations.append(obs)
        self.perception.process(ctx)
        self.layer.process(ctx)

        self.assertGreater(len(self.layer.get_entity_tracks()), 0)

    def test_context_recognition(self):
        """Test context recognition."""
        obs = make_observation()
        ctx = CycleContext()
        ctx.observations.append(obs)
        self.perception.process(ctx)
        self.layer.process(ctx)

        self.assertIn("context_type", ctx.situational_context.metadata)


class TestWorldModelLayer(unittest.TestCase):
    """Test the world model layer."""

    def setUp(self):
        self.perception = PerceptionLayer(PerceptionLayerConfig())
        self.situational = SituationalAwarenessLayer(SituationalAwarenessConfig())
        self.layer = WorldModelLayer(WorldModelLayerConfig())

    def test_process_with_situational_context(self):
        """Test processing with situational context."""
        obs = make_observation()
        ctx = CycleContext()
        ctx.observations.append(obs)
        self.perception.process(ctx)
        self.situational.process(ctx)

        result = self.layer.process(ctx)
        self.assertTrue(result.success)
        self.assertIsNotNone(ctx.world_state)
        self.assertGreater(len(ctx.predicted_futures), 0)

    def test_predictions_generated(self):
        """Test that predictions are generated."""
        obs = make_observation()
        ctx = CycleContext()
        ctx.observations.append(obs)
        self.perception.process(ctx)
        self.situational.process(ctx)
        self.layer.process(ctx)

        self.assertGreater(len(ctx.predicted_futures), 0)
        scenarios = {p.scenario for p in ctx.predicted_futures}
        self.assertIn("baseline", scenarios)


class TestActiveInferenceLayer(unittest.TestCase):
    """Test the active inference layer."""

    def setUp(self):
        self.perception = PerceptionLayer(PerceptionLayerConfig())
        self.situational = SituationalAwarenessLayer(SituationalAwarenessConfig())
        self.world_model = WorldModelLayer(WorldModelLayerConfig())
        self.layer = ActiveInferenceLayer(ActiveInferenceConfig())

    def test_process_with_world_state(self):
        """Test processing with world state."""
        obs = make_observation()
        ctx = CycleContext()
        ctx.observations.append(obs)
        self.perception.process(ctx)
        self.situational.process(ctx)
        self.world_model.process(ctx)

        result = self.layer.process(ctx)
        self.assertTrue(result.success)
        self.assertIn("active_inference", ctx.metadata)


class TestMemoryLayer(unittest.TestCase):
    """Test the memory layer."""

    def setUp(self):
        self.layer = MemoryLayer(MemoryLayerConfig())

    def test_store_and_recall(self):
        """Test storing and recalling memories."""
        from cognitive.types import MemoryLayer as MemoryLayerType
        item = self.layer.store(
            layer=MemoryLayerType.SEMANTIC,
            key="test_key",
            content="test content",
            importance=0.8,
        )
        self.assertIsNotNone(item)

        recalled = self.layer.recall(MemoryLayerType.SEMANTIC, "test_key")
        self.assertIsNotNone(recalled)
        self.assertEqual(recalled.content, "test content")

    def test_retrieve(self):
        """Test memory retrieval."""
        from cognitive.types import MemoryLayer as MemoryLayerType
        self.layer.store(
            layer=MemoryLayerType.SEMANTIC,
            key="concept_rl",
            content="Reinforcement learning concept",
            importance=0.9,
        )

        retrieval = self.layer.retrieve("reinforcement learning")
        self.assertGreater(retrieval.total_found, 0)

    def test_consolidation(self):
        """Test memory consolidation."""
        from cognitive.types import MemoryLayer as MemoryLayerType
        self.layer.store(
            layer=MemoryLayerType.WORKING,
            key="important_memory",
            content="Important concept to consolidate",
            importance=0.9,
        )

        result = self.layer.consolidate()
        self.assertGreaterEqual(result["consolidated"], 1)


class TestKnowledgeLayer(unittest.TestCase):
    """Test the knowledge layer."""

    def setUp(self):
        self.layer = KnowledgeLayer(KnowledgeLayerConfig())

    def test_store_fact(self):
        """Test storing a fact."""
        fact = self.layer.store_fact(
            content="Test knowledge fact",
            confidence=0.9,
            source="test",
            entities=["test_entity"],
        )
        self.assertIsNotNone(fact.fact_id)
        self.assertEqual(len(self.layer.get_facts()), 1)

    def test_retrieve(self):
        """Test knowledge retrieval."""
        self.layer.store_fact(
            content="Reinforcement learning is a machine learning paradigm",
            confidence=0.9,
            source="test",
            entities=["RL"],
        )

        results = self.layer.retrieve("reinforcement learning")
        self.assertGreater(len(results), 0)

    def test_hybrid_retrieve(self):
        """Test hybrid retrieval."""
        self.layer.store_fact(
            content="Neural networks are powerful models",
            confidence=0.9,
            source="test",
        )

        result = self.layer.hybrid_retrieve("neural networks")
        self.assertGreater(result["total_found"], 0)

    def test_rag_generate(self):
        """Test RAG generation."""
        self.layer.store_fact(
            content="Transformers use attention mechanisms",
            confidence=0.9,
            source="test",
        )

        result = self.layer.rag_generate("transformers")
        self.assertIn("response", result)
        self.assertGreater(result["facts_used"], 0)


class TestReasoningLayer(unittest.TestCase):
    """Test the reasoning layer."""

    def setUp(self):
        self.layer = ReasoningLayer(ReasoningLayerConfig())

    def test_process(self):
        """Test reasoning processing."""
        ctx = CycleContext()
        ctx.context.goals = ["achieve_objective"]
        ctx.confidence = 0.8

        result = self.layer.process(ctx)
        self.assertTrue(result.success)
        self.assertIsNotNone(ctx.reasoning_trace)

    def test_strategy_selection(self):
        """Test dynamic strategy selection."""
        ctx = CycleContext()
        ctx.context.goals = ["test_goal"]
        ctx.uncertainty = 0.8

        strategy = self.layer._select_strategy(ctx)
        self.assertEqual(strategy.value, "probabilistic")


class TestPlanningLayer(unittest.TestCase):
    """Test the planning layer."""

    def setUp(self):
        self.layer = PlanningLayer(PlanningLayerConfig())

    def test_process(self):
        """Test planning processing."""
        ctx = CycleContext()
        ctx.context.goals = ["achieve_objective"]
        ctx.context.time_horizon = 300.0

        result = self.layer.process(ctx)
        self.assertTrue(result.success)
        self.assertIsNotNone(ctx.plan)
        self.assertGreater(len(ctx.actions), 0)

    def test_planner_selection(self):
        """Test planner selection."""
        ctx = CycleContext()
        ctx.context.goals = ["goal1", "goal2"]
        ctx.context.time_horizon = 300.0

        planner = self.layer._select_planner(ctx)
        self.assertEqual(planner.value, "goap")


class TestPredictionLayer(unittest.TestCase):
    """Test the prediction layer."""

    def setUp(self):
        self.layer = PredictionLayer(PredictionLayerConfig())

    def test_process(self):
        """Test prediction processing."""
        ctx = CycleContext()
        ctx.world_state = None

        result = self.layer.process(ctx)
        self.assertTrue(result.success)
        self.assertIn("predictions", ctx.metadata)


class TestSelfReflectionLayer(unittest.TestCase):
    """Test the self-reflection layer."""

    def setUp(self):
        self.layer = SelfReflectionLayer(SelfReflectionConfig())

    def test_process(self):
        """Test self-reflection processing."""
        ctx = CycleContext()
        ctx.confidence = 0.8

        result = self.layer.process(ctx)
        self.assertTrue(result.success)
        self.assertTrue(ctx.self_reflection)
        self.assertIn("evaluations", ctx.self_reflection)


class TestMetaLearningLayer(unittest.TestCase):
    """Test the meta-learning layer."""

    def setUp(self):
        self.layer = MetaLearningLayer(MetaLearningConfig())

    def test_process(self):
        """Test meta-learning processing."""
        ctx = CycleContext()
        ctx.confidence = 0.8
        ctx.self_reflection = {
            "evaluations": {
                "planning_efficiency": 0.2,
                "reasoning_quality": 0.3,
            }
        }

        result = self.layer.process(ctx)
        self.assertTrue(result.success)
        self.assertIn("meta_learning", ctx.metadata)


class TestAgenticLayer(unittest.TestCase):
    """Test the agentic layer."""

    def setUp(self):
        self.layer = AgenticLayer(AgenticLayerConfig())

    def test_register_agent(self):
        """Test registering an agent."""
        from cognitive.agentic_layer import AgentSpec
        agent = AgentSpec(
            agent_id="agent1",
            role="researcher",
            capabilities=["research", "analysis"],
        )
        self.layer.register_agent(agent)
        self.assertEqual(len(self.layer.get_agents()), 1)

    def test_process(self):
        """Test agentic processing."""
        from cognitive.agentic_layer import AgentSpec
        agent = AgentSpec(
            agent_id="agent1",
            role="researcher",
            capabilities=["research"],
        )
        self.layer.register_agent(agent)

        ctx = CycleContext()
        ctx.context.goals = ["research topic"]
        ctx.confidence = 0.8

        result = self.layer.process(ctx)
        self.assertTrue(result.success)
        self.assertIn("agentic", ctx.metadata)


class TestLearningLayer(unittest.TestCase):
    """Test the learning layer."""

    def setUp(self):
        self.layer = LearningLayer(LearningLayerConfig())

    def test_process(self):
        """Test learning processing."""
        ctx = CycleContext()
        ctx.confidence = 0.8
        ctx.self_reflection = {
            "lessons_learned": ["Test lesson"]
        }

        result = self.layer.process(ctx)
        self.assertTrue(result.success)
        self.assertGreater(len(ctx.learnings), 0)


class TestExplainabilityLayer(unittest.TestCase):
    """Test the explainability layer."""

    def setUp(self):
        self.layer = ExplainabilityLayer(ExplainabilityLayerConfig())

    def test_process(self):
        """Test explainability processing."""
        ctx = CycleContext()
        ctx.confidence = 0.8
        ctx.context.goals = ["test_goal"]

        result = self.layer.process(ctx)
        self.assertTrue(result.success)
        self.assertIsNotNone(ctx.reasoning_trace)
        self.assertGreaterEqual(len(ctx.reasoning_trace.evidence), 0)


class TestSafetyLayer(unittest.TestCase):
    """Test the safety layer."""

    def setUp(self):
        self.layer = SafetyLayer(SafetyLayerConfig())

    def test_check_phase(self):
        """Test phase safety check."""
        ctx = CycleContext()
        ctx.confidence = 0.9
        ctx.uncertainty = 0.1

        result = self.layer.check_phase(ctx, CyclePhase.PERCEIVE)
        self.assertTrue(result["safe"])

    def test_check_phase_violation(self):
        """Test phase safety check with violation."""
        ctx = CycleContext()
        ctx.confidence = 0.1
        ctx.uncertainty = 0.9

        result = self.layer.check_phase(ctx, CyclePhase.PERCEIVE)
        self.assertFalse(result["safe"])

    def test_process(self):
        """Test safety monitoring."""
        ctx = CycleContext()
        ctx.confidence = 0.9
        ctx.uncertainty = 0.1

        result = self.layer.process(ctx)
        self.assertTrue(result.success)


class TestCognitiveAgent(unittest.TestCase):
    """Test the complete cognitive agent."""

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    def test_agent_creation(self):
        """Test agent creation."""
        agent = CognitiveAgent(CognitiveAgentConfig())
        self.assertIsNotNone(agent.loop)
        stats = agent.get_stats()
        self.assertEqual(stats["agent_id"], "cognitive-agent")

    def test_agent_perceive(self):
        """Test agent perception."""
        agent = CognitiveAgent(CognitiveAgentConfig())
        obs = make_observation()

        ctx = self.loop.run_until_complete(agent.perceive(obs))
        self.assertIsNotNone(ctx)
        self.assertGreater(len(ctx.phase_results), 0)

    def test_agent_decide(self):
        """Test agent decision making."""
        agent = CognitiveAgent(CognitiveAgentConfig())
        obs = make_observation()

        actions = self.loop.run_until_complete(
            agent.decide(obs, goals=["achieve_objective"])
        )
        self.assertIsInstance(actions, list)

    def test_agent_decision_traces(self):
        """Test agent decision traces."""
        agent = CognitiveAgent(CognitiveAgentConfig())
        obs = make_observation()

        self.loop.run_until_complete(agent.perceive(obs))
        traces = agent.get_decision_traces()
        self.assertGreater(len(traces), 0)


class TestCognitiveIntegration(unittest.TestCase):
    """Test the cognitive integration facade."""

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    def test_integration_creation(self):
        """Test integration creation."""
        integration = CognitiveIntegration(CognitiveIntegrationConfig())
        self.assertIsNotNone(integration.agent)
        self.assertIsNotNone(integration.layers)

    def test_integration_cycle(self):
        """Test integration cycle."""
        integration = CognitiveIntegration(CognitiveIntegrationConfig())
        obs = make_observation()

        ctx = self.loop.run_until_complete(integration.run_cycle(obs))
        self.assertIsNotNone(ctx)

    def test_integration_benchmark(self):
        """Test integration benchmark."""
        integration = CognitiveIntegration(CognitiveIntegrationConfig())
        observations = [make_observation(f"obs {i}") for i in range(3)]

        result = self.loop.run_until_complete(
            integration.run_benchmark("test_benchmark", observations)
        )
        self.assertEqual(result["cycles"], 3)
        self.assertIn("avg_confidence", result)

    def test_integration_components(self):
        """Test component registration."""
        integration = CognitiveIntegration(CognitiveIntegrationConfig())
        integration.register_component("test_component", {"key": "value"})
        self.assertIsNotNone(integration.get_component("test_component"))


class TestCognitiveLoop(unittest.TestCase):
    """Test the cognitive loop directly."""

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    def test_loop_with_all_layers(self):
        """Test the loop with all layers."""
        event_bus = EventBus()
        layers = {
            "perception": PerceptionLayer(PerceptionLayerConfig(event_bus=event_bus)),
            "situational": SituationalAwarenessLayer(SituationalAwarenessConfig(event_bus=event_bus)),
            "world_model": WorldModelLayer(WorldModelLayerConfig(event_bus=event_bus)),
            "memory": MemoryLayer(MemoryLayerConfig(event_bus=event_bus)),
            "knowledge": KnowledgeLayer(KnowledgeLayerConfig(event_bus=event_bus)),
            "reasoning": ReasoningLayer(ReasoningLayerConfig(event_bus=event_bus)),
            "prediction": PredictionLayer(PredictionLayerConfig(event_bus=event_bus)),
            "planning": PlanningLayer(PlanningLayerConfig(event_bus=event_bus)),
            "self_reflection": SelfReflectionLayer(SelfReflectionConfig(event_bus=event_bus)),
            "meta_learning": MetaLearningLayer(MetaLearningConfig(event_bus=event_bus)),
            "agentic": AgenticLayer(AgenticLayerConfig(event_bus=event_bus)),
            "learning": LearningLayer(LearningLayerConfig(event_bus=event_bus)),
            "explainability": ExplainabilityLayer(ExplainabilityLayerConfig(event_bus=event_bus)),
        }
        safety = SafetyLayer(SafetyLayerConfig(event_bus=event_bus))

        config = CognitiveLoopConfig(
            layers=layers,
            safety_layer=safety,
            event_bus=event_bus,
        )
        loop = CognitiveLoop(config)

        obs = make_observation()
        ctx = self.loop.run_until_complete(loop.run_cycle(observation=obs))

        self.assertIsNotNone(ctx)
        self.assertGreater(len(ctx.phase_results), 0)
        self.assertGreater(len(loop.get_decision_traces()), 0)

    def test_loop_stats(self):
        """Test loop statistics."""
        event_bus = EventBus()
        layers = {
            "perception": PerceptionLayer(PerceptionLayerConfig(event_bus=event_bus)),
        }
        config = CognitiveLoopConfig(layers=layers, event_bus=event_bus)
        loop = CognitiveLoop(config)

        obs = make_observation()
        self.loop.run_until_complete(loop.run_cycle(observation=obs))

        stats = loop.get_stats()
        self.assertEqual(stats["cycles_run"], 1)
        self.assertIn("layers", stats)


if __name__ == "__main__":
    unittest.main()
