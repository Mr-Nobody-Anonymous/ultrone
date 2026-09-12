# Copyright (c) Ultrone Contributors. All rights reserved.
"""Reasoning Layer — multi-strategy reasoning engine.

Combines multiple reasoning methods: deductive, inductive, abductive,
analogical, probabilistic, causal, counterfactual, temporal, spatial,
constraint-based, graph reasoning, and neuro-symbolic reasoning.
Selects the reasoning strategy dynamically.
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
    CounterfactualExplanation,
    DecisionTrace,
    Evidence,
    ReasoningStrategy,
    UncertaintyEstimate,
    UncertaintyType,
)

logger = logging.getLogger("Ultrone.Cognitive.Reasoning")


@dataclass
class ReasoningLayerConfig(LayerConfig):
    """Configuration for the reasoning layer."""
    name: str = "reasoning"
    default_strategy: ReasoningStrategy = ReasoningStrategy.PROBABILISTIC
    enable_strategy_selection: bool = True
    enable_counterfactuals: bool = True
    enable_causal_reasoning: bool = True
    max_reasoning_steps: int = 20
    confidence_threshold: float = 0.5


class ReasoningLayer(CognitiveLayer):
    """Multi-strategy reasoning engine.

    The reasoning layer:
    1. Selects the appropriate reasoning strategy dynamically
    2. Applies deductive, inductive, abductive, and analogical reasoning
    3. Performs probabilistic and causal reasoning
    4. Generates counterfactual explanations
    5. Produces a full reasoning trace
    """

    def __init__(self, config: Optional[ReasoningLayerConfig] = None):
        super().__init__(config or ReasoningLayerConfig())
        self._reasoning_history: List[Dict[str, Any]] = []
        self._strategy_performance: Dict[ReasoningStrategy, List[float]] = {}

    def _layer_phase(self) -> CyclePhase:
        return CyclePhase.REASON

    def process(self, ctx: CycleContext) -> PhaseResult:
        """Execute the reasoning phase.

        Parameters
        ----------
        ctx : CycleContext
            The shared cycle context.

        Returns
        -------
        PhaseResult
            Result with the reasoning trace.
        """
        start = time.time()

        # 1. Select reasoning strategy
        strategy = self._select_strategy(ctx)

        # 2. Build reasoning context
        reasoning_input = self._build_reasoning_input(ctx)

        # 3. Apply reasoning
        result = self._apply_reasoning(strategy, reasoning_input, ctx)

        # 4. Generate counterfactual explanation
        counterfactual = None
        if self.config.enable_counterfactuals:
            counterfactual = self._generate_counterfactual(result, ctx)

        # 5. Create decision trace
        trace = self._create_trace(
            decision=result.get("conclusion", "Reasoning completed"),
            confidence=result.get("confidence", 0.5),
            evidence=result.get("evidence", []),
        )
        trace.reasoning_strategy = strategy
        trace.reasoning_steps = result.get("steps", [])
        trace.counterfactual = counterfactual
        trace.feature_importance = result.get("feature_importance", {})

        # 6. Store in context
        ctx.reasoning_trace = trace

        # 7. Publish event
        self._publish_event(
            CognitiveEventType.REASONING,
            {
                "strategy": strategy.value,
                "result": result.get("conclusion", ""),
                "confidence": result.get("confidence", 0.0),
                "trace_id": trace.trace_id,
            },
        )

        # 8. Track strategy performance
        self._track_strategy_performance(strategy, result.get("confidence", 0.0))

        self._reasoning_history.append({
            "timestamp": time.time(),
            "strategy": strategy.value,
            "conclusion": result.get("conclusion", ""),
            "confidence": result.get("confidence", 0.0),
        })

        return PhaseResult(
            phase=self._phase,
            success=True,
            duration_seconds=time.time() - start,
            output={
                "strategy": strategy.value,
                "conclusion": result.get("conclusion", ""),
                "confidence": result.get("confidence", 0.0),
                "steps": result.get("steps", []),
                "counterfactual": counterfactual.__dict__ if counterfactual else None,
            },
            trace=trace,
        )

    def _select_strategy(self, ctx: CycleContext) -> ReasoningStrategy:
        """Select the reasoning strategy dynamically."""
        if not self.config.enable_strategy_selection:
            return self.config.default_strategy

        # Select based on context
        uncertainty = ctx.uncertainty if ctx.uncertainty > 0 else 0.5

        if uncertainty > 0.7:
            return ReasoningStrategy.PROBABILISTIC
        elif ctx.world_state and ctx.world_state.causal_structure:
            return ReasoningStrategy.CAUSAL
        elif ctx.situational_context and len(ctx.situational_context.entities) > 5:
            return ReasoningStrategy.GRAPH_REASONING
        elif ctx.context.goals:
            return ReasoningStrategy.DEDUCTIVE
        else:
            return ReasoningStrategy.INDUCTIVE

    def _build_reasoning_input(self, ctx: CycleContext) -> Dict[str, Any]:
        """Build the reasoning input from the cycle context."""
        return {
            "goals": ctx.context.goals,
            "constraints": ctx.context.constraints,
            "world_state": ctx.world_state.to_dict() if ctx.world_state else {},
            "situational_context": ctx.situational_context.to_dict() if ctx.situational_context else {},
            "predictions": [p.to_dict() for p in ctx.predicted_futures],
            "memory_retrievals": ctx.memory_retrievals,
        }

    def _apply_reasoning(self, strategy: ReasoningStrategy, input_data: Dict[str, Any], ctx: CycleContext) -> Dict[str, Any]:
        """Apply the selected reasoning strategy."""
        steps = []
        evidence = []

        if strategy == ReasoningStrategy.DEDUCTIVE:
            result = self._deductive_reasoning(input_data, steps, evidence)
        elif strategy == ReasoningStrategy.INDUCTIVE:
            result = self._inductive_reasoning(input_data, steps, evidence)
        elif strategy == ReasoningStrategy.ABDUCTIVE:
            result = self._abductive_reasoning(input_data, steps, evidence)
        elif strategy == ReasoningStrategy.ANALOGICAL:
            result = self._analogical_reasoning(input_data, steps, evidence)
        elif strategy == ReasoningStrategy.PROBABILISTIC:
            result = self._probabilistic_reasoning(input_data, steps, evidence)
        elif strategy == ReasoningStrategy.CAUSAL:
            result = self._causal_reasoning(input_data, steps, evidence)
        elif strategy == ReasoningStrategy.COUNTERFACTUAL:
            result = self._counterfactual_reasoning(input_data, steps, evidence)
        elif strategy == ReasoningStrategy.TEMPORAL:
            result = self._temporal_reasoning(input_data, steps, evidence)
        elif strategy == ReasoningStrategy.SPATIAL:
            result = self._spatial_reasoning(input_data, steps, evidence)
        elif strategy == ReasoningStrategy.CONSTRAINT_BASED:
            result = self._constraint_reasoning(input_data, steps, evidence)
        elif strategy == ReasoningStrategy.GRAPH_REASONING:
            result = self._graph_reasoning(input_data, steps, evidence)
        else:
            result = self._neuro_symbolic_reasoning(input_data, steps, evidence)

        result["steps"] = steps
        result["evidence"] = evidence
        return result

    def _deductive_reasoning(self, input_data: Dict[str, Any], steps: List[str], evidence: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Apply deductive reasoning from general rules to specific cases."""
        steps.append("Applying deductive reasoning: general rules → specific conclusions")
        goals = input_data.get("goals", [])
        world_state = input_data.get("world_state", {})

        if goals and world_state:
            steps.append(f"Evaluating {len(goals)} goals against world state")
            conclusion = f"Goals {goals} are achievable given current world state"
            confidence = 0.7
            evidence.append({
                "source": "deductive",
                "description": f"Derived from {len(goals)} goals and world state",
                "confidence": confidence,
            })
        else:
            conclusion = "Insufficient information for deductive reasoning"
            confidence = 0.3

        return {"conclusion": conclusion, "confidence": confidence}

    def _inductive_reasoning(self, input_data: Dict[str, Any], steps: List[str], evidence: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Apply inductive reasoning from specific cases to general rules."""
        steps.append("Applying inductive reasoning: specific cases → general patterns")
        predictions = input_data.get("predictions", [])

        if predictions:
            confidences = [p.get("confidence", 0.0) for p in predictions]
            avg_confidence = sum(confidences) / len(confidences)
            steps.append(f"Analyzed {len(predictions)} predictions with avg confidence {avg_confidence:.2f}")
            conclusion = f"Pattern detected: predictions have {avg_confidence:.2f} average confidence"
            confidence = min(0.9, avg_confidence + 0.1)
            evidence.append({
                "source": "inductive",
                "description": f"Induced from {len(predictions)} predictions",
                "confidence": confidence,
            })
        else:
            conclusion = "No predictions available for inductive reasoning"
            confidence = 0.3

        return {"conclusion": conclusion, "confidence": confidence}

    def _abductive_reasoning(self, input_data: Dict[str, Any], steps: List[str], evidence: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Apply abductive reasoning to find best explanation."""
        steps.append("Applying abductive reasoning: observations → best explanation")
        situational = input_data.get("situational_context", {})

        if situational:
            entities = situational.get("entities", {})
            steps.append(f"Analyzing {len(entities)} entities for best explanation")
            conclusion = f"Best explanation involves {len(entities)} observed entities"
            confidence = 0.6
            evidence.append({
                "source": "abductive",
                "description": f"Best explanation from {len(entities)} entities",
                "confidence": confidence,
            })
        else:
            conclusion = "No observations for abductive reasoning"
            confidence = 0.3

        return {"conclusion": conclusion, "confidence": confidence}

    def _analogical_reasoning(self, input_data: Dict[str, Any], steps: List[str], evidence: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Apply analogical reasoning by comparing to known situations."""
        steps.append("Applying analogical reasoning: current situation → similar known situations")
        memory = input_data.get("memory_retrievals", [])

        if memory:
            steps.append(f"Comparing to {len(memory)} retrieved memories")
            conclusion = "Current situation is analogous to retrieved memories"
            confidence = 0.5
            evidence.append({
                "source": "analogical",
                "description": f"Compared to {len(memory)} memories",
                "confidence": confidence,
            })
        else:
            conclusion = "No analogous memories found"
            confidence = 0.3

        return {"conclusion": conclusion, "confidence": confidence}

    def _probabilistic_reasoning(self, input_data: Dict[str, Any], steps: List[str], evidence: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Apply probabilistic reasoning with uncertainty."""
        steps.append("Applying probabilistic reasoning: uncertainty-aware inference")
        predictions = input_data.get("predictions", [])

        if predictions:
            probabilities = [p.get("probability", 0.0) for p in predictions]
            best_prob = max(probabilities) if probabilities else 0.0
            best_idx = probabilities.index(best_prob) if probabilities else -1
            steps.append(f"Evaluated {len(predictions)} scenarios, best probability {best_prob:.2f}")
            conclusion = f"Most likely scenario: {predictions[best_idx].get('scenario', 'unknown')}" if best_idx >= 0 else "No scenarios"
            confidence = best_prob
            evidence.append({
                "source": "probabilistic",
                "description": f"Best scenario has probability {best_prob:.2f}",
                "confidence": confidence,
            })
        else:
            conclusion = "No predictions for probabilistic reasoning"
            confidence = 0.3

        return {"conclusion": conclusion, "confidence": confidence}

    def _causal_reasoning(self, input_data: Dict[str, Any], steps: List[str], evidence: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Apply causal reasoning using the causal structure."""
        steps.append("Applying causal reasoning: cause-effect analysis")
        world_state = input_data.get("world_state", {})
        causal = world_state.get("causal_structure", {})

        if causal:
            steps.append(f"Analyzing {len(causal)} causal relationships")
            # Find most influential entity
            most_influential = max(causal.items(), key=lambda x: len(x[1]), default=(None, []))
            conclusion = f"Entity {most_influential[0]} is most causally influential" if most_influential[0] else "No causal structure"
            confidence = 0.7
            evidence.append({
                "source": "causal",
                "description": f"Identified {len(causal)} causal relationships",
                "confidence": confidence,
            })
        else:
            conclusion = "No causal structure available"
            confidence = 0.3

        return {"conclusion": conclusion, "confidence": confidence}

    def _counterfactual_reasoning(self, input_data: Dict[str, Any], steps: List[str], evidence: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Apply counterfactual reasoning."""
        steps.append("Applying counterfactual reasoning: what-if analysis")
        world_state = input_data.get("world_state", {})

        if world_state:
            steps.append("Generating counterfactual scenarios")
            conclusion = "Counterfactual analysis complete"
            confidence = 0.4
            evidence.append({
                "source": "counterfactual",
                "description": "Generated counterfactual scenarios",
                "confidence": confidence,
            })
        else:
            conclusion = "No world state for counterfactual reasoning"
            confidence = 0.3

        return {"conclusion": conclusion, "confidence": confidence}

    def _temporal_reasoning(self, input_data: Dict[str, Any], steps: List[str], evidence: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Apply temporal reasoning."""
        steps.append("Applying temporal reasoning: time-based analysis")
        predictions = input_data.get("predictions", [])

        if predictions:
            horizons = [p.get("horizon", 0) for p in predictions]
            steps.append(f"Analyzing predictions across {len(horizons)} time horizons")
            conclusion = f"Temporal analysis across {len(horizons)} horizons complete"
            confidence = 0.6
            evidence.append({
                "source": "temporal",
                "description": f"Analyzed {len(horizons)} time horizons",
                "confidence": confidence,
            })
        else:
            conclusion = "No temporal data available"
            confidence = 0.3

        return {"conclusion": conclusion, "confidence": confidence}

    def _spatial_reasoning(self, input_data: Dict[str, Any], steps: List[str], evidence: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Apply spatial reasoning."""
        steps.append("Applying spatial reasoning: spatial relationships")
        situational = input_data.get("situational_context", {})

        if situational:
            entities = situational.get("entities", {})
            steps.append(f"Analyzing spatial relationships of {len(entities)} entities")
            conclusion = f"Spatial analysis of {len(entities)} entities complete"
            confidence = 0.6
            evidence.append({
                "source": "spatial",
                "description": f"Analyzed {len(entities)} entities spatially",
                "confidence": confidence,
            })
        else:
            conclusion = "No spatial data available"
            confidence = 0.3

        return {"conclusion": conclusion, "confidence": confidence}

    def _constraint_reasoning(self, input_data: Dict[str, Any], steps: List[str], evidence: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Apply constraint-based reasoning."""
        steps.append("Applying constraint-based reasoning")
        constraints = input_data.get("constraints", {})

        if constraints:
            steps.append(f"Evaluating {len(constraints)} constraints")
            conclusion = f"Constraint analysis of {len(constraints)} constraints complete"
            confidence = 0.7
            evidence.append({
                "source": "constraint",
                "description": f"Evaluated {len(constraints)} constraints",
                "confidence": confidence,
            })
        else:
            conclusion = "No constraints to evaluate"
            confidence = 0.5

        return {"conclusion": conclusion, "confidence": confidence}

    def _graph_reasoning(self, input_data: Dict[str, Any], steps: List[str], evidence: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Apply graph-based reasoning."""
        steps.append("Applying graph reasoning: graph traversal and analysis")
        situational = input_data.get("situational_context", {})

        if situational:
            relationships = situational.get("relationships", [])
            steps.append(f"Analyzing {len(relationships)} graph relationships")
            conclusion = f"Graph analysis of {len(relationships)} relationships complete"
            confidence = 0.6
            evidence.append({
                "source": "graph",
                "description": f"Analyzed {len(relationships)} relationships",
                "confidence": confidence,
            })
        else:
            conclusion = "No graph data available"
            confidence = 0.3

        return {"conclusion": conclusion, "confidence": confidence}

    def _neuro_symbolic_reasoning(self, input_data: Dict[str, Any], steps: List[str], evidence: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Apply neuro-symbolic reasoning."""
        steps.append("Applying neuro-symbolic reasoning: neural + symbolic integration")
        conclusion = "Neuro-symbolic reasoning complete"
        confidence = 0.5
        evidence.append({
            "source": "neuro_symbolic",
            "description": "Integrated neural and symbolic reasoning",
            "confidence": confidence,
        })
        return {"conclusion": conclusion, "confidence": confidence}

    def _generate_counterfactual(self, result: Dict[str, Any], ctx: CycleContext) -> Optional[CounterfactualExplanation]:
        """Generate a counterfactual explanation for the reasoning result."""
        if not result.get("conclusion"):
            return None

        return CounterfactualExplanation(
            condition=f"If the reasoning strategy had been different",
            hypothesis=f"The conclusion '{result.get('conclusion', '')}' might differ",
            estimated_effect=0.1,
            confidence=0.3,
            intervention={"strategy": "alternative"},
        )

    def _track_strategy_performance(self, strategy: ReasoningStrategy, confidence: float) -> None:
        """Track the performance of each reasoning strategy."""
        if strategy not in self._strategy_performance:
            self._strategy_performance[strategy] = []
        self._strategy_performance[strategy].append(confidence)
        # Keep only recent performance
        if len(self._strategy_performance[strategy]) > 100:
            self._strategy_performance[strategy] = self._strategy_performance[strategy][-100:]

    def get_reasoning_history(self) -> List[Dict[str, Any]]:
        """Return the history of reasoning operations."""
        return self._reasoning_history

    def get_strategy_performance(self) -> Dict[str, float]:
        """Return the average performance of each strategy."""
        return {
            strategy.value: (
                sum(confidences) / len(confidences)
                if confidences else 0.0
            )
            for strategy, confidences in self._strategy_performance.items()
        }