# Copyright (c) Ultrone Contributors. All rights reserved.
"""Event prediction for Level 3 projection.

Predicts future events based on:

* entity state trends
* temporal patterns
* causal relationships
* threshold crossings
* scenario branching
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional, Sequence, Tuple

import numpy as np

from .types import (
    EventForecast,
    TrackedEntity,
    utc_now,
)

__all__ = [
    "EventPredictor",
    "EventPredictorConfig",
    "EventRule",
]


@dataclass
class EventRule:
    """A rule that predicts an event from entity state."""

    event_type: str
    predicate: Callable[[TrackedEntity, float], Tuple[bool, float]]
    description: str = ""


class EventPredictorConfig:
    """Configuration for the event predictor."""

    def __init__(
        self,
        *,
        default_horizon_seconds: float = 30.0,
        min_confidence: float = 0.1,
        max_events_per_entity: int = 10,
    ) -> None:
        self.default_horizon_seconds = default_horizon_seconds
        self.min_confidence = min_confidence
        self.max_events_per_entity = max_events_per_entity


class EventPredictor:
    """Predicts future events from entity state and rules."""

    def __init__(self, *, config: Optional[EventPredictorConfig] = None) -> None:
        self._config = config or EventPredictorConfig()
        self._rules: List[EventRule] = []
        self._forecasts: List[EventForecast] = []

    def add_rule(self, rule: EventRule) -> None:
        """Register a custom event prediction rule."""
        self._rules.append(rule)

    def add_proximity_rule(
        self,
        event_type: str,
        *,
        threshold_distance: float = 10.0,
        description: str = "",
    ) -> None:
        """Add a rule that predicts an event when an entity approaches a threshold."""

        def predicate(entity: TrackedEntity, horizon: float) -> Tuple[bool, float]:
            speed = float(np.linalg.norm(entity.state.velocity.as_array()))
            if speed < 1e-6:
                return False, 0.0
            # Predict distance at horizon.
            predicted_distance = threshold_distance - speed * horizon
            probability = min(1.0, max(0.0, (threshold_distance - predicted_distance) / threshold_distance))
            return probability > self._config.min_confidence, probability

        self._rules.append(
            EventRule(
                event_type=event_type,
                predicate=predicate,
                description=description or f"Proximity event within {threshold_distance}",
            )
        )

    def predict_entity(
        self,
        entity: TrackedEntity,
        *,
        horizon_seconds: Optional[float] = None,
    ) -> List[EventForecast]:
        """Predict events for a single entity."""
        horizon = horizon_seconds or self._config.default_horizon_seconds
        forecasts: List[EventForecast] = []

        for rule in self._rules:
            try:
                triggered, probability = rule.predicate(entity, horizon)
            except Exception:
                continue
            if not triggered:
                continue
            forecast = EventForecast(
                event_type=rule.event_type,
                probability=float(np.clip(probability, 0.0, 1.0)),
                time_to_event=horizon,
                confidence=entity.confidence,
                affected_entity_ids=[entity.entity_id],
                contributing_factors=[rule.description],
                generated_at=utc_now(),
                method="rule_based",
            )
            forecasts.append(forecast)

        self._forecasts.extend(forecasts)
        return forecasts

    def predict_batch(
        self,
        entities: Sequence[TrackedEntity],
        *,
        horizon_seconds: Optional[float] = None,
    ) -> List[EventForecast]:
        """Predict events for a batch of entities."""
        all_forecasts: List[EventForecast] = []
        for entity in entities:
            all_forecasts.extend(
                self.predict_entity(entity, horizon_seconds=horizon_seconds)
            )
        return all_forecasts

    def forecasts(self, limit: Optional[int] = None) -> List[EventForecast]:
        forecasts = self._forecasts
        if limit is not None:
            forecasts = forecasts[-limit:]
        return list(forecasts)

    def clear(self) -> None:
        self._forecasts.clear()