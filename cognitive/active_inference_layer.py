# Copyright (c) Ultrone Contributors. All rights reserved.
"""Active Inference Layer — uncertainty minimization and information gain.

Minimizes uncertainty and maximizes useful information. Determines what
is unknown, what observation reduces uncertainty, what action improves
the model, and what hypothesis is most likely. Prefers information gain
when confidence is low.
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
    Action,
    FuturePrediction,
    PlanningHorizon,
    UncertaintyEstimate,
    UncertaintyType,
    WorldState,
)

logger = logging.getLogger("Ultrone.Cognitive.ActiveInference")


@dataclass
class ActiveInferenceConfig(LayerConfig):
    """Configuration for the active inference layer."""
    name: str = "active_inference"
    information_gain_threshold: float = 0.3
    uncertainty_threshold: float = 0.5
    max_queries: int = 5
    enable_information_gain: bool = True
    enable_hypothesis_testing: bool = True
    exploration_bonus: float = 0.1


class ActiveInferenceLayer(CognitiveLayer):
    """Active inference layer that minimizes uncertainty.

    The active inference layer:
    1. Identifies what is unknown
    2. Determines which observations reduce uncertainty most
    3. Identifies actions that improve the model
    4. Tests hypotheses
    5. Prefers information gain when confidence is low
    """

    def __init__(self, config: Optional[ActiveInferenceConfig] = None):
        super().__init__(config or ActiveInferenceConfig())
        self._information_gain_history: List[Dict[str, Any]] = []
        self._hypotheses: List[Dict[str, Any]] = []
        self._queries_made: List[Dict[str, Any]] = []

    def _layer_phase(self) -> CyclePhase:
        return CyclePhase.RETRIEVE_MEMORY

    def process(self, ctx: CycleContext) -> PhaseResult:
        """Execute the active inference phase.

        Parameters
        ----------
        ctx : CycleContext
            The shared cycle context.

        Returns
        -------
        PhaseResult
            Result with information gain analysis and queries.
        """
        start = time.time()
        world_state = ctx.world_state
        predictions = ctx.predicted_futures

        if world_state is None:
            return PhaseResult(
                phase=self._phase,
                success=True,
                duration_seconds=time.time() - start,
                output={"message": "no world state"},
            )

        # 1. Identify unknowns
        unknowns = self._identify_unknowns(world_state, predictions)

        # 2. Compute information gain for potential observations
        information_gain = self._compute_information_gain(unknowns, world_state)

        # 3. Generate queries
        queries = self._generate_queries(unknowns, information_gain)

        # 4. Test hypotheses
        if self.config.enable_hypothesis_testing:
            hypotheses = self._test_hypotheses(world_state, predictions)
            self._hypotheses.extend(hypotheses)

        # 5. Determine if exploration is needed
        uncertainty = world_state.uncertainty.total
        needs_exploration = uncertainty > self.config.uncertainty_threshold

        # 6. Store in context
        ctx.metadata["active_inference"] = {
            "unknowns": unknowns,
            "information_gain": information_gain,
            "queries": queries,
            "needs_exploration": needs_exploration,
        }

        # 7. Publish event
        self._publish_event(
            CognitiveEventType.UNCERTAINTY_HIGH if needs_exploration else CognitiveEventType.PERCEPTION,
            {
                "unknowns": len(unknowns),
                "information_gain": information_gain,
                "queries": len(queries),
                "needs_exploration": needs_exploration,
            },
        )

        # 8. Create decision trace
        trace = self._create_trace(
            decision="Active inference: minimize uncertainty and maximize information",
            confidence=1.0 - uncertainty,
            evidence=[
                {
                    "source": "world_model",
                    "description": f"Identified {len(unknowns)} unknowns with information gain {information_gain:.3f}",
                    "confidence": 1.0 - uncertainty,
                }
            ],
        )
        trace.uncertainty = world_state.uncertainty

        self._information_gain_history.append({
            "timestamp": time.time(),
            "unknowns": len(unknowns),
            "information_gain": information_gain,
            "needs_exploration": needs_exploration,
        })

        return PhaseResult(
            phase=self._phase,
            success=True,
            duration_seconds=time.time() - start,
            output={
                "unknowns": unknowns,
                "information_gain": information_gain,
                "queries": queries,
                "needs_exploration": needs_exploration,
                "hypotheses_tested": len(self._hypotheses),
            },
            trace=trace,
        )

    def _identify_unknowns(self, world_state: WorldState, predictions: List[FuturePrediction]) -> List[Dict[str, Any]]:
        """Identify what is unknown in the world state."""
        unknowns = []

        # Entities with low confidence
        for entity_id, entity in world_state.entities.items():
            confidence = entity.get("confidence", 1.0)
            if confidence < self.config.uncertainty_threshold:
                unknowns.append({
                    "type": "entity_uncertainty",
                    "entity_id": entity_id,
                    "confidence": confidence,
                    "reason": "low_confidence",
                })

        # Missing dynamics
        for entity_id, entity in world_state.entities.items():
            if entity_id not in world_state.dynamics:
                unknowns.append({
                    "type": "missing_dynamics",
                    "entity_id": entity_id,
                    "reason": "no_dynamics_model",
                })

        # Missing causal structure
        for entity_id in world_state.entities:
            if entity_id not in world_state.causal_structure:
                unknowns.append({
                    "type": "missing_causal",
                    "entity_id": entity_id,
                    "reason": "no_causal_connections",
                })

        # High uncertainty predictions
        for pred in predictions:
            if pred.uncertainty.total > self.config.uncertainty_threshold:
                unknowns.append({
                    "type": "prediction_uncertainty",
                    "horizon": pred.horizon,
                    "scenario": pred.scenario,
                    "uncertainty": pred.uncertainty.total,
                    "reason": "high_prediction_uncertainty",
                })

        return unknowns[:self.config.max_queries * 2]

    def _compute_information_gain(self, unknowns: List[Dict[str, Any]], world_state: WorldState) -> float:
        """Compute the expected information gain from resolving unknowns."""
        if not unknowns:
            return 0.0

        # Information gain is proportional to the number of unknowns
        # and inversely proportional to current confidence
        base_gain = len(unknowns) * 0.1
        uncertainty = world_state.uncertainty.total
        gain = base_gain * (1.0 + uncertainty)

        # Add exploration bonus
        if self.config.enable_information_gain:
            gain += self.config.exploration_bonus

        return min(1.0, gain)

    def _generate_queries(self, unknowns: List[Dict[str, Any]], information_gain: float) -> List[Dict[str, Any]]:
        """Generate queries to resolve unknowns."""
        queries = []

        if information_gain < self.config.information_gain_threshold:
            return queries

        for unknown in unknowns[:self.config.max_queries]:
            query = {
                "type": "observation_request",
                "target": unknown.get("entity_id", unknown.get("type", "unknown")),
                "reason": unknown.get("reason", "reduce_uncertainty"),
                "expected_gain": information_gain / max(1, len(unknowns)),
            }
            queries.append(query)
            self._queries_made.append(query)

        return queries

    def _test_hypotheses(self, world_state: WorldState, predictions: List[FuturePrediction]) -> List[Dict[str, Any]]:
        """Test hypotheses about the world state."""
        hypotheses = []

        # Hypothesis: entity with most connections is most influential
        if world_state.causal_structure:
            most_connected = max(
                world_state.causal_structure.items(),
                key=lambda x: len(x[1]),
                default=(None, []),
            )
            if most_connected[0]:
                hypotheses.append({
                    "hypothesis": f"Entity {most_connected[0]} is most influential",
                    "confidence": 0.6,
                    "evidence": f"Has {len(most_connected[1])} causal connections",
                })

        # Hypothesis: predictions with high confidence are reliable
        reliable_predictions = [p for p in predictions if p.confidence > 0.7]
        if reliable_predictions:
            hypotheses.append({
                "hypothesis": f"{len(reliable_predictions)} predictions are reliable",
                "confidence": 0.7,
                "evidence": "High confidence predictions",
            })

        return hypotheses

    def get_information_gain_history(self) -> List[Dict[str, Any]]:
        """Return the history of information gain computations."""
        return self._information_gain_history

    def get_hypotheses(self) -> List[Dict[str, Any]]:
        """Return all tested hypotheses."""
        return self._hypotheses

    def get_queries_made(self) -> List[Dict[str, Any]]:
        """Return all queries made."""
        return self._queries_made