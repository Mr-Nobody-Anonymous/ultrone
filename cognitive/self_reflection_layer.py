# Copyright (c) Ultrone Contributors. All rights reserved.
"""Self-Reflection Layer — post-task evaluation and improvement.

After every completed task, evaluates prediction accuracy, reasoning
quality, memory usefulness, planning efficiency, resource efficiency,
and decision confidence. Generates lessons learned, failure explanations,
policy improvements, and knowledge updates.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .base_layer import CognitiveLayer, LayerConfig
from .cycle_context import CycleContext, CyclePhase, PhaseResult
from .event_types import CognitiveEventType

logger = logging.getLogger("Ultrone.Cognitive.SelfReflection")


@dataclass
class SelfReflectionConfig(LayerConfig):
    """Configuration for the self-reflection layer."""
    name: str = "self_reflection"
    enable_lessons_learning: bool = True
    enable_failure_analysis: bool = True
    enable_policy_improvement: bool = True
    enable_knowledge_updates: bool = True
    evaluation_threshold: float = 0.5


class SelfReflectionLayer(CognitiveLayer):
    """Self-reflection layer that evaluates and improves.

    The self-reflection layer:
    1. Evaluates prediction accuracy
    2. Assesses reasoning quality
    3. Evaluates memory usefulness
    4. Assesses planning efficiency
    5. Evaluates resource efficiency
    6. Assesses decision confidence
    7. Generates lessons learned
    8. Identifies failure explanations
    9. Proposes policy improvements
    10. Updates knowledge
    """

    def __init__(self, config: Optional[SelfReflectionConfig] = None):
        super().__init__(config or SelfReflectionConfig())
        self._reflection_history: List[Dict[str, Any]] = []
        self._lessons_learned: List[str] = []
        self._policy_improvements: List[Dict[str, Any]] = []

    def _layer_phase(self) -> CyclePhase:
        return CyclePhase.LEARN

    def process(self, ctx: CycleContext) -> PhaseResult:
        """Execute the self-reflection phase.

        Parameters
        ----------
        ctx : CycleContext
            The shared cycle context.

        Returns
        -------
        PhaseResult
            Result with self-reflection evaluation.
        """
        start = time.time()

        # 1. Evaluate prediction accuracy
        prediction_accuracy = self._evaluate_prediction_accuracy(ctx)

        # 2. Assess reasoning quality
        reasoning_quality = self._evaluate_reasoning_quality(ctx)

        # 3. Evaluate memory usefulness
        memory_usefulness = self._evaluate_memory_usefulness(ctx)

        # 4. Assess planning efficiency
        planning_efficiency = self._evaluate_planning_efficiency(ctx)

        # 5. Evaluate resource efficiency
        resource_efficiency = self._evaluate_resource_efficiency(ctx)

        # 6. Assess decision confidence
        decision_confidence = self._evaluate_decision_confidence(ctx)

        # 7. Generate lessons learned
        lessons = self._generate_lessons(ctx, {
            "prediction_accuracy": prediction_accuracy,
            "reasoning_quality": reasoning_quality,
            "memory_usefulness": memory_usefulness,
            "planning_efficiency": planning_efficiency,
            "resource_efficiency": resource_efficiency,
            "decision_confidence": decision_confidence,
        })

        # 8. Identify failure explanations
        failures = self._identify_failures(ctx)

        # 9. Propose policy improvements
        improvements = self._propose_improvements(ctx, {
            "prediction_accuracy": prediction_accuracy,
            "reasoning_quality": reasoning_quality,
            "planning_efficiency": planning_efficiency,
        })

        # 10. Update knowledge
        knowledge_updates = self._update_knowledge(ctx, lessons)

        # 11. Store in context
        reflection = {
            "evaluations": {
                "prediction_accuracy": prediction_accuracy,
                "reasoning_quality": reasoning_quality,
                "memory_usefulness": memory_usefulness,
                "planning_efficiency": planning_efficiency,
                "resource_efficiency": resource_efficiency,
                "decision_confidence": decision_confidence,
            },
            "lessons_learned": lessons,
            "failures": failures,
            "policy_improvements": improvements,
            "knowledge_updates": knowledge_updates,
        }
        ctx.self_reflection = reflection

        # 12. Publish event
        self._publish_event(
            CognitiveEventType.LEARNING,
            {
                "evaluations": reflection["evaluations"],
                "lessons": len(lessons),
                "improvements": len(improvements),
            },
        )

        # 13. Create decision trace
        trace = self._create_trace(
            decision="Self-reflection: evaluate and improve",
            confidence=decision_confidence,
            evidence=[
                {
                    "source": "self_reflection",
                    "description": f"Evaluated with prediction accuracy {prediction_accuracy:.2f}",
                    "confidence": decision_confidence,
                }
            ],
        )

        self._reflection_history.append(reflection)
        self._lessons_learned.extend(lessons)
        self._policy_improvements.extend(improvements)

        return PhaseResult(
            phase=self._phase,
            success=True,
            duration_seconds=time.time() - start,
            output=reflection,
            trace=trace,
        )

    def _evaluate_prediction_accuracy(self, ctx: CycleContext) -> float:
        """Evaluate prediction accuracy."""
        predictions = ctx.metadata.get("predictions", [])
        if not predictions:
            return 0.5
        accuracies = []
        for pred in predictions:
            if isinstance(pred, dict):
                confidence = pred.get("confidence", 0.5)
                uncertainty = pred.get("uncertainty", {})
                if isinstance(uncertainty, dict):
                    total_uncertainty = uncertainty.get("total", 0.0)
                else:
                    total_uncertainty = 0.0
                accuracies.append(max(0.0, confidence - total_uncertainty))
        return sum(accuracies) / len(accuracies) if accuracies else 0.5

    def _evaluate_reasoning_quality(self, ctx: CycleContext) -> float:
        """Evaluate reasoning quality."""
        if ctx.reasoning_trace:
            return ctx.reasoning_trace.confidence
        return 0.5

    def _evaluate_memory_usefulness(self, ctx: CycleContext) -> float:
        """Evaluate memory usefulness."""
        if ctx.memory_retrievals:
            return min(1.0, len(ctx.memory_retrievals) * 0.2)
        return 0.3

    def _evaluate_planning_efficiency(self, ctx: CycleContext) -> float:
        """Evaluate planning efficiency."""
        if ctx.plan:
            return ctx.plan.confidence
        return 0.5

    def _evaluate_resource_efficiency(self, ctx: CycleContext) -> float:
        """Evaluate resource efficiency."""
        resources = ctx.context.resources
        if not resources:
            return 0.7
        return sum(resources.values()) / len(resources)

    def _evaluate_decision_confidence(self, ctx: CycleContext) -> float:
        """Evaluate decision confidence."""
        return ctx.confidence if ctx.confidence > 0 else 0.5

    def _generate_lessons(self, ctx: CycleContext, evaluations: Dict[str, float]) -> List[str]:
        """Generate lessons learned from the cycle."""
        lessons = []

        if not self.config.enable_lessons_learning:
            return lessons

        if evaluations["prediction_accuracy"] < self.config.evaluation_threshold:
            lessons.append("Prediction accuracy is low; consider improving world model")

        if evaluations["reasoning_quality"] < self.config.evaluation_threshold:
            lessons.append("Reasoning quality is low; consider alternative reasoning strategies")

        if evaluations["planning_efficiency"] < self.config.evaluation_threshold:
            lessons.append("Planning efficiency is low; consider different planners")

        if evaluations["decision_confidence"] < self.config.evaluation_threshold:
            lessons.append("Decision confidence is low; gather more information")

        if not lessons:
            lessons.append("Cycle performed well; maintain current strategies")

        return lessons

    def _identify_failures(self, ctx: CycleContext) -> List[Dict[str, Any]]:
        """Identify failures in the cycle."""
        failures = []

        if not self.config.enable_failure_analysis:
            return failures

        for pr in ctx.phase_results:
            if not pr.success:
                failures.append({
                    "phase": pr.phase.value,
                    "error": pr.error,
                    "explanation": f"Phase {pr.phase.value} failed: {pr.error}",
                })

        return failures

    def _propose_improvements(self, ctx: CycleContext, evaluations: Dict[str, float]) -> List[Dict[str, Any]]:
        """Propose policy improvements."""
        improvements = []

        if not self.config.enable_policy_improvement:
            return improvements

        if evaluations["prediction_accuracy"] < self.config.evaluation_threshold:
            improvements.append({
                "policy": "prediction",
                "improvement": "Increase ensemble model diversity",
                "expected_effect": "Better prediction accuracy",
            })

        if evaluations["reasoning_quality"] < self.config.evaluation_threshold:
            improvements.append({
                "policy": "reasoning",
                "improvement": "Use probabilistic reasoning more often",
                "expected_effect": "Better reasoning under uncertainty",
            })

        if evaluations["planning_efficiency"] < self.config.evaluation_threshold:
            improvements.append({
                "policy": "planning",
                "improvement": "Use hierarchical planning for complex goals",
                "expected_effect": "More efficient planning",
            })

        return improvements

    def _update_knowledge(self, ctx: CycleContext, lessons: List[str]) -> List[Dict[str, Any]]:
        """Update knowledge based on lessons learned."""
        updates = []

        if not self.config.enable_knowledge_updates:
            return updates

        for lesson in lessons:
            updates.append({
                "type": "lesson",
                "content": lesson,
                "source": "self_reflection",
                "timestamp": time.time(),
            })

        return updates

    def get_reflection_history(self) -> List[Dict[str, Any]]:
        """Return the history of self-reflections."""
        return self._reflection_history

    def get_lessons_learned(self) -> List[str]:
        """Return all lessons learned."""
        return self._lessons_learned

    def get_policy_improvements(self) -> List[Dict[str, Any]]:
        """Return all policy improvements."""
        return self._policy_improvements