# Copyright (c) Ultrone Contributors. All rights reserved.
"""World Model Layer — internal predictive simulation.

Builds an internal predictive simulation representing entities, dynamics,
resources, time, space, and causality. Predicts short-term futures,
long-term futures, alternative futures, and counterfactual futures.
Continuously updates from new observations.
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
    FuturePrediction,
    SituationalContext,
    UncertaintyEstimate,
    UncertaintyType,
    WorldState,
)

logger = logging.getLogger("Ultrone.Cognitive.WorldModel")


@dataclass
class WorldModelLayerConfig(LayerConfig):
    """Configuration for the world model layer."""
    name: str = "world_model"
    prediction_horizons: List[float] = field(default_factory=lambda: [5.0, 30.0, 300.0, 3600.0])
    enable_counterfactuals: bool = True
    enable_alternative_futures: bool = True
    max_predictions: int = 10
    dynamics_model: str = "linear"  # linear, learned, hybrid
    update_confidence: float = 0.8


class WorldModelLayer(CognitiveLayer):
    """Maintains an internal predictive world model.

    The world model layer:
    1. Updates the world state from the situational context
    2. Maintains entity dynamics and causal structure
    3. Predicts short-term and long-term futures
    4. Generates alternative and counterfactual futures
    5. Continuously updates from new observations
    """

    def __init__(self, config: Optional[WorldModelLayerConfig] = None):
        super().__init__(config or WorldModelLayerConfig())
        self._world_state_history: List[WorldState] = []
        self._prediction_history: List[FuturePrediction] = []
        self._dynamics_models: Dict[str, Any] = {}

    def _layer_phase(self) -> CyclePhase:
        return CyclePhase.UPDATE_WORLD_MODEL

    def process(self, ctx: CycleContext) -> PhaseResult:
        """Execute the world model update phase.

        Parameters
        ----------
        ctx : CycleContext
            The shared cycle context containing the situational context.

        Returns
        -------
        PhaseResult
            Result with the updated world state and predictions.
        """
        start = time.time()
        situational = ctx.situational_context

        if situational is None:
            return PhaseResult(
                phase=self._phase,
                success=True,
                duration_seconds=time.time() - start,
                output={"world_state": None, "message": "no situational context"},
            )

        # 1. Update world state
        world_state = self._update_world_state(situational, ctx)
        ctx.world_state = world_state

        # 2. Generate predictions
        predictions = self._generate_predictions(world_state, ctx)
        ctx.predicted_futures = predictions

        # 3. Publish event
        self._publish_event(
            CognitiveEventType.WORLD_MODEL_UPDATED,
            {
                "state_id": world_state.state_id,
                "entities": len(world_state.entities),
                "predictions": len(predictions),
                "confidence": world_state.uncertainty.total,
            },
        )

        # 4. Create decision trace
        trace = self._create_trace(
            decision="Update world model and generate predictions",
            confidence=1.0 - world_state.uncertainty.total,
            evidence=[
                {
                    "source": "situational_context",
                    "description": f"Updated world state with {len(world_state.entities)} entities",
                    "confidence": situational.confidence,
                }
            ],
        )
        trace.uncertainty = world_state.uncertainty

        self._world_state_history.append(world_state)
        if len(self._world_state_history) > 100:
            self._world_state_history = self._world_state_history[-100:]

        return PhaseResult(
            phase=self._phase,
            success=True,
            duration_seconds=time.time() - start,
            output={
                "world_state": world_state.to_dict(),
                "predictions": [p.to_dict() for p in predictions],
                "entities": len(world_state.entities),
                "prediction_count": len(predictions),
            },
            trace=trace,
        )

    def _update_world_state(self, situational: SituationalContext, ctx: CycleContext) -> WorldState:
        """Update the world state from the situational context."""
        world_state = WorldState(
            entities=situational.entities,
            time_info={
                "timestamp": time.time(),
                "horizon": situational.prediction_horizon,
            },
            uncertainty=situational.scene_graph.uncertainty_estimate if situational.scene_graph else UncertaintyEstimate(),
        )

        # Update dynamics from entity tracks
        world_state.dynamics = self._update_dynamics(situational)

        # Update causal structure
        world_state.causal_structure = self._update_causal_structure(situational)

        # Update resources
        world_state.resources = self._extract_resources(situational)

        return world_state

    def _update_dynamics(self, situational: SituationalContext) -> Dict[str, Any]:
        """Update entity dynamics models."""
        dynamics = {}
        for entity_id, entity in situational.entities.items():
            entity_type = entity.get("type", "unknown")
            if entity_type not in self._dynamics_models:
                self._dynamics_models[entity_type] = {
                    "velocity": 0.0,
                    "acceleration": 0.0,
                    "last_position": entity.get("properties", {}).get("position"),
                    "last_time": time.time(),
                }
            dynamics[entity_id] = {
                "type": entity_type,
                "model": self._dynamics_models[entity_type],
            }
        return dynamics

    def _update_causal_structure(self, situational: SituationalContext) -> Dict[str, Any]:
        """Update the causal structure from relationships."""
        causal = {}
        for rel in situational.relationships:
            source = rel.get("source", "")
            target = rel.get("target", "")
            rel_type = rel.get("type", "related_to")
            if source not in causal:
                causal[source] = []
            causal[source].append({
                "target": target,
                "type": rel_type,
                "confidence": rel.get("confidence", 0.5),
            })
        return causal

    def _extract_resources(self, situational: SituationalContext) -> Dict[str, Any]:
        """Extract resource information from the situational context."""
        resources = {}
        for entity_id, entity in situational.entities.items():
            props = entity.get("properties", {})
            if "resources" in props:
                resources[entity_id] = props["resources"]
            elif "resource" in props:
                resources[entity_id] = props["resource"]
        return resources

    def _generate_predictions(self, world_state: WorldState, ctx: CycleContext) -> List[FuturePrediction]:
        """Generate predictions for multiple time horizons."""
        predictions = []

        for horizon in self.config.prediction_horizons:
            # Baseline prediction
            prediction = self._predict_future(world_state, horizon, scenario="baseline")
            predictions.append(prediction)

            # Alternative futures
            if self.config.enable_alternative_futures and len(predictions) < self.config.max_predictions:
                alt = self._predict_future(world_state, horizon, scenario="optimistic")
                predictions.append(alt)
                alt = self._predict_future(world_state, horizon, scenario="pessimistic")
                predictions.append(alt)

            # Counterfactual futures
            if self.config.enable_counterfactuals and len(predictions) < self.config.max_predictions:
                cf = self._predict_counterfactual(world_state, horizon)
                predictions.append(cf)

        return predictions[:self.config.max_predictions]

    def _predict_future(self, world_state: WorldState, horizon: float, scenario: str = "baseline") -> FuturePrediction:
        """Predict a future world state at a given horizon."""
        future_state = WorldState(
            entities={},
            dynamics=world_state.dynamics,
            resources=world_state.resources,
            time_info={
                "timestamp": time.time() + horizon,
                "horizon": horizon,
                "scenario": scenario,
            },
            space_info=world_state.space_info,
            causal_structure=world_state.causal_structure,
        )

        # Predict entity states
        for entity_id, entity in world_state.entities.items():
            predicted = dict(entity)
            props = dict(entity.get("properties", {}))

            # Simple linear prediction for position
            if "position" in props and isinstance(props["position"], (list, tuple)) and len(props["position"]) >= 2:
                dynamics = world_state.dynamics.get(entity_id, {}).get("model", {})
                velocity = dynamics.get("velocity", 0.0)
                if velocity:
                    props["position"] = [
                        props["position"][0] + velocity * horizon,
                        props["position"][1] + velocity * horizon,
                    ]

            predicted["properties"] = props
            predicted["prediction_horizon"] = horizon
            predicted["scenario"] = scenario
            future_state.entities[entity_id] = predicted

        # Estimate confidence (decays with horizon)
        confidence = max(0.1, 1.0 - (horizon / 3600.0) * 0.5)
        uncertainty = UncertaintyEstimate(
            epistemic=1.0 - confidence,
            aleatoric=0.1,
            total=1.0 - confidence + 0.1,
            type=UncertaintyType.EPISTEMIC,
            contributing_factors=[f"horizon:{horizon}", f"scenario:{scenario}"],
        )

        return FuturePrediction(
            horizon=horizon,
            scenario=scenario,
            world_state=future_state,
            confidence=confidence,
            uncertainty=uncertainty,
            probability=confidence,
        )

    def _predict_counterfactual(self, world_state: WorldState, horizon: float) -> FuturePrediction:
        """Generate a counterfactual prediction."""
        cf_state = WorldState(
            entities={},
            dynamics=world_state.dynamics,
            resources=world_state.resources,
            time_info={
                "timestamp": time.time() + horizon,
                "horizon": horizon,
                "scenario": "counterfactual",
            },
            causal_structure=world_state.causal_structure,
        )

        # Counterfactual: remove the most influential entity
        if world_state.entities:
            # Find entity with most causal connections
            most_influential = None
            max_connections = -1
            for entity_id, connections in world_state.causal_structure.items():
                if len(connections) > max_connections:
                    max_connections = len(connections)
                    most_influential = entity_id

            if most_influential:
                for entity_id, entity in world_state.entities.items():
                    if entity_id != most_influential:
                        cf_state.entities[entity_id] = dict(entity)
                cf_state.metadata = {
                    "counterfactual": f"Removed entity {most_influential}",
                    "intervention": {"remove": most_influential},
                }

        return FuturePrediction(
            horizon=horizon,
            scenario="counterfactual",
            world_state=cf_state,
            confidence=0.3,
            uncertainty=UncertaintyEstimate(
                epistemic=0.5,
                aleatoric=0.2,
                total=0.7,
                type=UncertaintyType.EPISTEMIC,
                contributing_factors=["counterfactual"],
            ),
            is_counterfactual=True,
            intervention={"remove": most_influential} if 'most_influential' in locals() else None,
            probability=0.3,
        )

    def get_world_state_history(self) -> List[WorldState]:
        """Return the history of world states."""
        return self._world_state_history

    def get_prediction_history(self) -> List[FuturePrediction]:
        """Return the history of predictions."""
        return self._prediction_history