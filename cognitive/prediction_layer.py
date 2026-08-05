# Copyright (c) Ultrone Contributors. All rights reserved.
"""Prediction Layer — ensemble prediction subsystem.

Forecasts entity trajectories, system evolution, resource usage, failure
probability, risk, expected outcomes, and confidence intervals. Uses
ensemble prediction models.
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
    PredictionResult,
    UncertaintyEstimate,
    UncertaintyType,
)

logger = logging.getLogger("Ultrone.Cognitive.Prediction")


@dataclass
class PredictionLayerConfig(LayerConfig):
    """Configuration for the prediction layer."""
    name: str = "prediction"
    ensemble_models: List[str] = field(default_factory=lambda: ["linear", "exponential", "moving_average"])
    enable_ensemble: bool = True
    enable_confidence_intervals: bool = True
    enable_feature_importance: bool = True
    max_predictions: int = 20
    default_horizon: float = 300.0


class PredictionLayer(CognitiveLayer):
    """Ensemble prediction subsystem.

    The prediction layer:
    1. Forecasts entity trajectories
    2. Predicts system evolution
    3. Estimates resource usage
    4. Computes failure probability and risk
    5. Generates confidence intervals
    6. Uses ensemble prediction models
    """

    def __init__(self, config: Optional[PredictionLayerConfig] = None):
        super().__init__(config or PredictionLayerConfig())
        self._prediction_history: List[PredictionResult] = []
        self._model_performance: Dict[str, List[float]] = {}

    def _layer_phase(self) -> CyclePhase:
        return CyclePhase.PREDICT_FUTURES

    def process(self, ctx: CycleContext) -> PhaseResult:
        """Execute the prediction phase.

        Parameters
        ----------
        ctx : CycleContext
            The shared cycle context.

        Returns
        -------
        PhaseResult
            Result with predictions.
        """
        start = time.time()

        # 1. Build prediction input
        input_data = self._build_prediction_input(ctx)

        # 2. Generate predictions using ensemble
        predictions = self._generate_ensemble_predictions(input_data, ctx)

        # 3. Compute confidence intervals
        if self.config.enable_confidence_intervals:
            for pred in predictions:
                pred.confidence_intervals = self._compute_confidence_intervals(pred)

        # 4. Compute feature importance
        if self.config.enable_feature_importance:
            for pred in predictions:
                pred.feature_importance = self._compute_feature_importance(pred, input_data)

        # 5. Store in context
        ctx.metadata["predictions"] = [p.to_dict() for p in predictions]

        # 6. Publish event
        self._publish_event(
            CognitiveEventType.PREDICTION_GENERATED,
            {
                "predictions": len(predictions),
                "models": self.config.ensemble_models,
            },
        )

        # 7. Create decision trace
        trace = self._create_trace(
            decision="Generate ensemble predictions",
            confidence=0.7,
            evidence=[
                {
                    "source": "prediction",
                    "description": f"Generated {len(predictions)} predictions using {len(self.config.ensemble_models)} models",
                    "confidence": 0.7,
                }
            ],
        )

        self._prediction_history.extend(predictions)
        if len(self._prediction_history) > 100:
            self._prediction_history = self._prediction_history[-100:]

        return PhaseResult(
            phase=self._phase,
            success=True,
            duration_seconds=time.time() - start,
            output={
                "predictions": [p.to_dict() for p in predictions],
                "models_used": self.config.ensemble_models,
                "prediction_count": len(predictions),
            },
            trace=trace,
        )

    def _build_prediction_input(self, ctx: CycleContext) -> Dict[str, Any]:
        """Build the prediction input from the cycle context."""
        return {
            "world_state": ctx.world_state.to_dict() if ctx.world_state else {},
            "situational_context": ctx.situational_context.to_dict() if ctx.situational_context else {},
            "goals": ctx.context.goals,
            "constraints": ctx.context.constraints,
            "resources": ctx.context.resources,
        }

    def _generate_ensemble_predictions(self, input_data: Dict[str, Any], ctx: CycleContext) -> List[PredictionResult]:
        """Generate predictions using an ensemble of models."""
        predictions = []
        world_state = input_data.get("world_state", {})

        for model_name in self.config.ensemble_models:
            pred = self._predict_with_model(model_name, input_data, ctx)
            predictions.append(pred)

        # Generate combined ensemble prediction
        if self.config.enable_ensemble and len(predictions) > 1:
            ensemble = self._combine_ensemble(predictions, input_data, ctx)
            predictions.append(ensemble)

        return predictions[:self.config.max_predictions]

    def _predict_with_model(self, model_name: str, input_data: Dict[str, Any], ctx: CycleContext) -> PredictionResult:
        """Generate a prediction using a specific model."""
        world_state = input_data.get("world_state", {})
        entities = world_state.get("entities", {})

        predictions = {}
        for entity_id, entity in entities.items():
            entity_type = entity.get("type", "unknown")
            confidence = entity.get("confidence", 0.5)

            if model_name == "linear":
                value = confidence * 0.8
            elif model_name == "exponential":
                value = confidence * 0.9
            elif model_name == "moving_average":
                value = confidence * 0.7
            else:
                value = confidence * 0.75

            predictions[entity_id] = value

        # Add system-level predictions
        predictions["system_health"] = self._predict_system_health(input_data)
        predictions["resource_usage"] = self._predict_resource_usage(input_data)
        predictions["failure_probability"] = self._predict_failure_probability(input_data)
        predictions["risk"] = self._predict_risk(input_data)

        uncertainty = UncertaintyEstimate(
            epistemic=0.2,
            aleatoric=0.1,
            total=0.3,
            type=UncertaintyType.EPISTEMIC,
            contributing_factors=[f"model:{model_name}"],
        )

        return PredictionResult(
            model_name=model_name,
            predictions=predictions,
            uncertainty=uncertainty,
            model_version="1.0",
        )

    def _combine_ensemble(self, predictions: List[PredictionResult], input_data: Dict[str, Any], ctx: CycleContext) -> PredictionResult:
        """Combine individual model predictions into an ensemble prediction."""
        combined = {}
        weights = {}

        # Simple average ensemble
        for pred in predictions:
            for key, value in pred.predictions.items():
                if key not in combined:
                    combined[key] = []
                combined[key].append(value)

        final_predictions = {}
        for key, values in combined.items():
            final_predictions[key] = sum(values) / len(values)

        # Compute ensemble weights
        for pred in predictions:
            weights[pred.model_name] = 1.0 / len(predictions)

        return PredictionResult(
            model_name="ensemble",
            predictions=final_predictions,
            ensemble_weights=weights,
            uncertainty=UncertaintyEstimate(
                epistemic=0.15,
                aleatoric=0.1,
                total=0.25,
                type=UncertaintyType.EPISTEMIC,
                contributing_factors=["ensemble"],
            ),
            model_version="ensemble-1.0",
        )

    def _predict_system_health(self, input_data: Dict[str, Any]) -> float:
        """Predict system health."""
        world_state = input_data.get("world_state", {})
        entities = world_state.get("entities", {})
        if not entities:
            return 0.8
        avg_confidence = sum(e.get("confidence", 0.5) for e in entities.values()) / len(entities)
        return min(1.0, avg_confidence + 0.1)

    def _predict_resource_usage(self, input_data: Dict[str, Any]) -> float:
        """Predict resource usage."""
        resources = input_data.get("resources", {})
        if not resources:
            return 0.5
        return sum(resources.values()) / len(resources)

    def _predict_failure_probability(self, input_data: Dict[str, Any]) -> float:
        """Predict failure probability."""
        world_state = input_data.get("world_state", {})
        uncertainty = world_state.get("uncertainty", {})
        total_uncertainty = uncertainty.get("total", 0.0) if isinstance(uncertainty, dict) else 0.0
        return min(1.0, total_uncertainty * 0.8)

    def _predict_risk(self, input_data: Dict[str, Any]) -> float:
        """Predict risk level."""
        failure_prob = self._predict_failure_probability(input_data)
        return min(1.0, failure_prob * 1.2)

    def _compute_confidence_intervals(self, pred: PredictionResult) -> Dict[str, tuple]:
        """Compute confidence intervals for predictions."""
        intervals = {}
        for key, value in pred.predictions.items():
            margin = 0.1 * (1.0 - pred.uncertainty.total)
            intervals[key] = (max(0.0, value - margin), min(1.0, value + margin))
        return intervals

    def _compute_feature_importance(self, pred: PredictionResult, input_data: Dict[str, Any]) -> Dict[str, float]:
        """Compute feature importance for predictions."""
        importance = {}
        for key in pred.predictions:
            importance[key] = 1.0 / max(1, len(pred.predictions))
        return importance

    def get_prediction_history(self) -> List[PredictionResult]:
        """Return the history of predictions."""
        return self._prediction_history

    def get_model_performance(self) -> Dict[str, float]:
        """Return the average performance of each model."""
        return {
            model: (
                sum(confidences) / len(confidences)
                if confidences else 0.0
            )
            for model, confidences in self._model_performance.items()
        }