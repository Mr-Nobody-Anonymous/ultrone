# Copyright (c) Ultrone Contributors. All rights reserved.
"""Uncertainty propagation through the awareness pipeline.

Propagates uncertainty from raw observations through fusion, tracking, and
prediction stages. Provides:

* observation-to-entity uncertainty propagation
* fusion uncertainty combination
* prediction uncertainty growth
* end-to-end uncertainty tracking
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

from .types import (
    Observation,
    TrackedEntity,
    utc_now,
)

__all__ = [
    "UncertaintyTrace",
    "UncertaintyPropagator",
    "UncertaintyPropagatorConfig",
]


@dataclass
class UncertaintyTrace:
    """A trace of uncertainty through the pipeline."""

    entity_id: str
    observation_uncertainty: float = 0.0
    fusion_uncertainty: float = 0.0
    tracking_uncertainty: float = 0.0
    prediction_uncertainty: float = 0.0
    total_uncertainty: float = 0.0
    timestamp: datetime = field(default_factory=utc_now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class UncertaintyPropagatorConfig:
    """Configuration for the uncertainty propagator."""

    def __init__(
        self,
        *,
        observation_weight: float = 0.3,
        fusion_weight: float = 0.3,
        tracking_weight: float = 0.2,
        prediction_weight: float = 0.2,
        prediction_growth_rate: float = 0.1,
    ) -> None:
        self.observation_weight = observation_weight
        self.fusion_weight = fusion_weight
        self.tracking_weight = tracking_weight
        self.prediction_weight = prediction_weight
        self.prediction_growth_rate = prediction_growth_rate


class UncertaintyPropagator:
    """Propagates uncertainty through the awareness pipeline."""

    def __init__(self, *, config: Optional[UncertaintyPropagatorConfig] = None) -> None:
        self._config = config or UncertaintyPropagatorConfig()
        self._traces: List[UncertaintyTrace] = []

    def observation_uncertainty(self, observation: Observation) -> float:
        """Compute uncertainty from a single observation."""
        uncertainty = 1.0 - observation.confidence
        if observation.measurement.covariance is not None:
            cov = observation.measurement.covariance.to_array()
            uncertainty += float(np.trace(cov))
        if observation.is_noisy:
            uncertainty += 0.1
        if observation.is_missing:
            uncertainty += 0.5
        return uncertainty

    def fusion_uncertainty(
        self, observations: Sequence[Observation]
    ) -> float:
        """Compute combined uncertainty from multiple observations."""
        if not observations:
            return 1.0
        uncertainties = [self.observation_uncertainty(o) for o in observations]
        # More observations reduce uncertainty (inverse of count weighting).
        combined = np.mean(uncertainties) / np.sqrt(len(observations))
        return float(combined)

    def tracking_uncertainty(self, entity: TrackedEntity) -> float:
        """Compute tracking uncertainty from entity state."""
        uncertainty = entity.uncertainty
        if not np.isfinite(uncertainty):
            uncertainty = 1.0
        # More observations reduce tracking uncertainty.
        if entity.observation_count > 0:
            uncertainty /= np.sqrt(entity.observation_count)
        return float(uncertainty)

    def prediction_uncertainty(
        self, base_uncertainty: float, horizon_seconds: float
    ) -> float:
        """Compute prediction uncertainty that grows with horizon."""
        return base_uncertainty + self._config.prediction_growth_rate * horizon_seconds

    def propagate(
        self,
        entity: TrackedEntity,
        *,
        observations: Optional[Sequence[Observation]] = None,
        horizon_seconds: float = 0.0,
    ) -> UncertaintyTrace:
        """Propagate uncertainty through the full pipeline for an entity."""
        obs_uncertainty = (
            self.fusion_uncertainty(observations)
            if observations
            else 1.0 - entity.confidence
        )
        fusion_unc = obs_uncertainty
        tracking_unc = self.tracking_uncertainty(entity)
        prediction_unc = self.prediction_uncertainty(tracking_unc, horizon_seconds)

        total = (
            self._config.observation_weight * obs_uncertainty
            + self._config.fusion_weight * fusion_unc
            + self._config.tracking_weight * tracking_unc
            + self._config.prediction_weight * prediction_unc
        )

        trace = UncertaintyTrace(
            entity_id=str(entity.entity_id),
            observation_uncertainty=float(obs_uncertainty),
            fusion_uncertainty=float(fusion_unc),
            tracking_uncertainty=float(tracking_unc),
            prediction_uncertainty=float(prediction_unc),
            total_uncertainty=float(total),
        )
        self._traces.append(trace)
        return trace

    def traces(self, limit: Optional[int] = None) -> List[UncertaintyTrace]:
        traces = self._traces
        if limit is not None:
            traces = traces[-limit:]
        return list(traces)

    def clear(self) -> None:
        self._traces.clear()