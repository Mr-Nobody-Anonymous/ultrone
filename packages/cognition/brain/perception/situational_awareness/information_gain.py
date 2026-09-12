# Copyright (c) Ultrone Contributors. All rights reserved.
"""Information gain estimation for active perception.

Computes expected information gain from potential observations:

* entropy reduction
* KL divergence between prior and posterior
* mutual information
* expected entropy reduction for sensor selection
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np

from .types import BeliefDistribution

__all__ = [
    "InformationGain",
    "InformationGainEstimator",
]


@dataclass
class InformationGain:
    """Information gain estimate for a potential observation."""

    sensor_id: str
    entity_id: str
    expected_gain: float
    current_entropy: float
    expected_entropy: float
    method: str = "entropy_reduction"
    metadata: Dict[str, object] = field(default_factory=dict)


class InformationGainEstimator:
    """Estimates expected information gain from potential observations."""

    def __init__(self, *, num_samples: int = 100) -> None:
        self._num_samples = num_samples

    def entropy_reduction(
        self,
        belief: BeliefDistribution,
        *,
        sensor_id: str,
        entity_id: str,
        measurement_noise: float = 0.1,
    ) -> InformationGain:
        """Estimate entropy reduction from a hypothetical measurement."""
        current_entropy = belief.entropy()

        # Simulate a measurement with the given noise and estimate posterior entropy.
        mean = belief.mean_array()
        cov = belief.covariance_array()
        n = mean.shape[0]

        # Expected posterior covariance after a measurement with noise R.
        R = np.eye(n, dtype=np.float64) * measurement_noise
        posterior_cov = np.linalg.inv(
            np.linalg.inv(cov + np.eye(n) * 1e-12) + np.linalg.inv(R)
        )

        sign, logdet = np.linalg.slogdet(posterior_cov + np.eye(n) * 1e-12)
        expected_entropy = 0.5 * (n * (1.0 + np.log(2.0 * np.pi)) + logdet)

        gain = max(0.0, current_entropy - expected_entropy)
        return InformationGain(
            sensor_id=sensor_id,
            entity_id=entity_id,
            expected_gain=float(gain),
            current_entropy=float(current_entropy),
            expected_entropy=float(expected_entropy),
            method="entropy_reduction",
        )

    def kl_divergence_gain(
        self,
        prior: BeliefDistribution,
        posterior: BeliefDistribution,
        *,
        sensor_id: str,
        entity_id: str,
    ) -> InformationGain:
        """Compute information gain as KL divergence between prior and posterior."""
        from .belief_state import kl_divergence

        gain = kl_divergence(posterior, prior)
        return InformationGain(
            sensor_id=sensor_id,
            entity_id=entity_id,
            expected_gain=float(gain),
            current_entropy=prior.entropy(),
            expected_entropy=posterior.entropy(),
            method="kl_divergence",
        )

    def rank_sensors(
        self,
        belief: BeliefDistribution,
        sensor_noises: Dict[str, float],
        *,
        entity_id: str,
    ) -> List[InformationGain]:
        """Rank sensors by expected information gain for a belief."""
        gains: List[InformationGain] = []
        for sensor_id, noise in sensor_noises.items():
            gain = self.entropy_reduction(
                belief,
                sensor_id=sensor_id,
                entity_id=entity_id,
                measurement_noise=noise,
            )
            gains.append(gain)
        gains.sort(key=lambda g: g.expected_gain, reverse=True)
        return gains

    def best_sensor(
        self,
        belief: BeliefDistribution,
        sensor_noises: Dict[str, float],
        *,
        entity_id: str,
    ) -> Optional[InformationGain]:
        """Return the sensor with the highest expected information gain."""
        gains = self.rank_sensors(belief, sensor_noises, entity_id=entity_id)
        return gains[0] if gains else None