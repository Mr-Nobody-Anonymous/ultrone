# Copyright (c) Ultrone Contributors. All rights reserved.
"""Explainability Layer — transparent decision generation.

Every decision must produce: decision trace, evidence, confidence,
alternative options, counterfactual explanation, reasoning graph,
feature importance, and supporting memory references.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .base_layer import CognitiveLayer, LayerConfig
from .cycle_context import CycleContext, CyclePhase, PhaseResult
from .event_types import CognitiveEventType
from .types import (
    AlternativeOption,
    CounterfactualExplanation,
    DecisionTrace,
    Evidence,
    MemoryReference,
    UncertaintyEstimate,
    UncertaintyType,
)

logger = logging.getLogger("Ultrone.Cognitive.Explainability")


@dataclass
class ExplainabilityLayerConfig(LayerConfig):
    """Configuration for the explainability layer."""
    name: str = "explainability"
    enable_decision_trace: bool = True
    enable_counterfactuals: bool = True
    enable_reasoning_graph: bool = True
    enable_feature_importance: bool = True
    enable_alternatives: bool = True
    max_alternatives: int = 3


class ExplainabilityLayer(CognitiveLayer):
    """Explainability layer for transparent decisions.

    The explainability layer:
    1. Produces complete decision traces for every decision
    2. Aggregates evidence from all phases
    3. Generates alternative options
    4. Creates counterfactual explanations
    5. Builds reasoning graphs
    6. Computes feature importance
    7. References supporting memories
    """

    def __init__(self, config: Optional[ExplainabilityLayerConfig] = None):
        super().__init__(config or ExplainabilityLayerConfig())
        self._explanation_history: List[Dict[str, Any]] = []

    def _layer_phase(self) -> CyclePhase:
        return CyclePhase.EVALUATE

    def process(self, ctx: CycleContext) -> PhaseResult:
        """Execute the explainability phase.

        Parameters
        ----------
        ctx : CycleContext
            The shared cycle context.

        Returns
        -------
        PhaseResult
            Result with the complete explanation.
        """
        start = time.time()

        # 1. Build decision trace
        trace = self._build_decision_trace(ctx)

        # 2. Generate alternatives
        alternatives = []
        if self.config.enable_alternatives:
            alternatives = self._generate_alternatives(ctx)

        # 3. Generate counterfactual explanation
        counterfactual = None
        if self.config.enable_counterfactuals:
            counterfactual = self._generate_counterfactual(ctx)

        # 4. Build reasoning graph
        reasoning_graph = None
        if self.config.enable_reasoning_graph:
            reasoning_graph = self._build_reasoning_graph(ctx)

        # 5. Compute feature importance
        feature_importance = {}
        if self.config.enable_feature_importance:
            feature_importance = self._compute_feature_importance(ctx)

        # 6. Collect memory references
        memory_refs = self._collect_memory_references(ctx)

        # 7. Populate trace with all explanation components
        trace.evidence = self._collect_evidence(ctx)
        trace.alternative_options = alternatives
        trace.counterfactual = counterfactual
        trace.feature_importance = feature_importance
        trace.supporting_memory = memory_refs
        trace.confidence = ctx.confidence
        trace.uncertainty = UncertaintyEstimate(
            epistemic=1.0 - ctx.confidence,
            aleatoric=0.0,
            total=1.0 - ctx.confidence,
            type=UncertaintyType.EPISTEMIC,
            contributing_factors=["overall_uncertainty"],
        )

        # 8. Store in context
        ctx.reasoning_trace = trace

        # 9. Publish event
        self._publish_event(
            CognitiveEventType.EVALUATION,
            {
                "trace_id": trace.trace_id,
                "decision": trace.decision,
                "confidence": trace.confidence,
                "alternatives": len(alternatives),
                "has_counterfactual": counterfactual is not None,
                "features": len(feature_importance),
            },
        )

        self._explanation_history.append(trace.to_dict())
        if len(self._explanation_history) > 100:
            self._explanation_history = self._explanation_history[-100:]

        return PhaseResult(
            phase=self._phase,
            success=True,
            duration_seconds=time.time() - start,
            output={
                "trace": trace.to_dict(),
                "alternatives": [a.__dict__ for a in alternatives],
                "has_counterfactual": counterfactual is not None,
                "reasoning_graph": reasoning_graph,
            },
            trace=trace,
        )

    def _build_decision_trace(self, ctx: CycleContext) -> DecisionTrace:
        """Build the decision trace for the cycle."""
        decision = ""
        if ctx.plan:
            decision = f"Execute plan for goal: {ctx.plan.goal}"
        elif ctx.context.goals:
            decision = f"Achieve goal: {ctx.context.goals[0]}"
        else:
            decision = "Cognitive decision"

        return DecisionTrace(
            decision=decision,
            confidence=ctx.confidence,
            context={
                "cycle_id": ctx.cycle_id,
                "goals": ctx.context.goals,
                "constraints": ctx.context.constraints,
                "timestamp": time.time(),
            },
        )

    def _collect_evidence(self, ctx: CycleContext) -> List[Evidence]:
        """Collect evidence from all phases."""
        evidence = []

        # Evidence from scene graph
        if ctx.scene_graph:
            evidence.append(Evidence(
                source="perception",
                description=f"Scene graph with {len(ctx.scene_graph.nodes)} entities",
                confidence=ctx.scene_graph.overall_confidence,
                weight=0.3,
            ))

        # Evidence from reasoning
        if ctx.reasoning_trace:
            evidence.append(Evidence(
                source="reasoning",
                description=ctx.reasoning_trace.decision,
                confidence=ctx.reasoning_trace.confidence,
                weight=0.3,
            ))

        # Evidence from predictions
        for pred in ctx.predicted_futures[:3]:
            evidence.append(Evidence(
                source="world_model",
                description=f"Prediction at horizon {pred.horizon:.0f}s ({pred.scenario})",
                confidence=pred.confidence,
                weight=0.2,
            ))

        return evidence

    def _generate_alternatives(self, ctx: CycleContext) -> List[AlternativeOption]:
        """Generate alternative options that were considered."""
        alternatives = []

        if ctx.plan and ctx.plan.alternatives:
            for alt_plan in ctx.plan.alternatives[:self.config.max_alternatives]:
                alternatives.append(AlternativeOption(
                    description=f"Alternative plan using {alt_plan.planner_type.value}",
                    value=alt_plan.expected_utility,
                    confidence=alt_plan.confidence,
                    reason_rejected="Lower expected utility than selected plan",
                ))

        # Add generic alternatives
        if len(alternatives) < 2:
            alternatives.append(AlternativeOption(
                description="Delay action and gather more information",
                value=0.4,
                confidence=0.3,
                reason_rejected="Lower expected utility",
            ))

        return alternatives

    def _generate_counterfactual(self, ctx: CycleContext) -> Optional[CounterfactualExplanation]:
        """Generate a counterfactual explanation."""
        if not ctx.plan and not ctx.context.goals:
            return None

        decision = ctx.plan.goal if ctx.plan else ctx.context.goals[0]
        return CounterfactualExplanation(
            condition=f"If the system had chosen a different plan for '{decision}'",
            hypothesis="The outcome would likely differ",
            estimated_effect=0.15,
            confidence=0.3,
            intervention={"plan": "alternative"},
        )

    def _build_reasoning_graph(self, ctx: CycleContext) -> Dict[str, Any]:
        """Build a reasoning graph showing the decision process."""
        nodes = [
            {"id": "perception", "label": "Perception", "confidence": ctx.scene_graph.overall_confidence if ctx.scene_graph else 0.0},
            {"id": "understanding", "label": "Understanding", "confidence": ctx.situational_context.confidence if ctx.situational_context else 0.0},
            {"id": "reasoning", "label": "Reasoning", "confidence": ctx.reasoning_trace.confidence if ctx.reasoning_trace else 0.0},
            {"id": "planning", "label": "Planning", "confidence": ctx.plan.confidence if ctx.plan else 0.0},
        ]

        edges = [
            {"source": "perception", "target": "understanding", "type": "feeds_into"},
            {"source": "understanding", "target": "reasoning", "type": "informs"},
            {"source": "reasoning", "target": "planning", "type": "guides"},
        ]

        return {
            "nodes": nodes,
            "edges": edges,
        }

    def _compute_feature_importance(self, ctx: CycleContext) -> Dict[str, float]:
        """Compute feature importance for the decision."""
        importance = {}

        if ctx.scene_graph:
            importance["scene_entities"] = len(ctx.scene_graph.nodes) * 0.2

        if ctx.situational_context:
            importance["situational_entities"] = len(ctx.situational_context.entities) * 0.2

        if ctx.predicted_futures:
            importance["predictions"] = len(ctx.predicted_futures) * 0.1

        if ctx.memory_retrievals:
            importance["memory"] = len(ctx.memory_retrievals) * 0.1

        if ctx.plan:
            importance["plan_steps"] = len(ctx.plan.steps) * 0.2

        return importance

    def _collect_memory_references(self, ctx: CycleContext) -> List[MemoryReference]:
        """Collect memory references that supported the decision."""
        references = []

        for retrieval in ctx.memory_retrievals:
            if isinstance(retrieval, dict):
                for result in retrieval.get("results", [])[:3]:
                    if isinstance(result, dict):
                        references.append(MemoryReference(
                            memory_id=result.get("item_id", result.get("fact_id", "unknown")),
                            layer=result.get("layer", "unknown"),
                            relevance_score=result.get("importance", result.get("score", 0.5)),
                            content_snippet=str(result.get("content", ""))[:100] if result.get("content") else "",
                        ))
                    elif isinstance(result, str):
                        references.append(MemoryReference(
                            memory_id="unknown",
                            layer="unknown",
                            relevance_score=0.5,
                            content_snippet=result[:100],
                        ))

        return references[:5]

    def get_explanation_history(self) -> List[Dict[str, Any]]:
        """Return the history of explanations."""
        return self._explanation_history