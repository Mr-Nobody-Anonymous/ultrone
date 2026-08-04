# Copyright (c) Ultrone Contributors. All rights reserved.
"""Uncertainty quantification and propagation.

Provides:

* scalar uncertainty metrics (trace, determinant, entropy)
* uncertainty propagation through linear and nonlinear transforms
* confidence decay over time
* uncertainty aggregation across sources
* aleatoric vs. epistemic uncertainty decomposition
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional, Sequence

import numpy as np

from .types import BeliefDistribution

__all__ = [
    "UncertaintyMetrics",
    "UncertaintyEngine",
    "UncertaintyConfig",
]


@dataclass
class UncertaintyMetrics:
    """Aggregated uncertainty metrics for a belief."""

    trace: float = 0.0
    determinant: float = 0.0
    entropy: float = 0.0
    max_eigenvalue: float = 0.0
    aleatoric: float = 0.0
    epistemic: float = 0.0
    total: float = 0.0


class UncertaintyConfig:
    """Configuration for the uncertainty engine."""

    def __init__(
        self,
        *,
        confidence_decay_rate: float = 0.01,
        uncertainty_growth_rate: float = 0.1,
        decay_enabled: bool = True,
    ) -> None:
        self.confidence_decay_rate = confidence_decay_rate
        self.uncertainty_growth_rate = uncertainty_growth_rate
        self.decay_enabled = decay_enabled


class UncertaintyEngine:
    """Computes and propagates uncertainty for beliefs."""

    def __init__(self, *, config: Optional[UncertaintyConfig] = None) -> None:
        self._config = config or UncertaintyConfig()

    def metrics(self, belief: BeliefDistribution) -> UncertaintyMetrics:
        """Compute comprehensive uncertainty metrics for a belief."""
        cov = belief.covariance_array()
        trace = float(np.trace(cov))
        entropy = belief.entropy()

        try:
            det = float(np.linalg.det(cov))
        except np.linalg.LinAlgError:
            det = float("inf")

        try:
            eigenvalues = np.linalg.eigvalsh(cov)
            max_eigen = float(eigenvalues[-1]) if eigenvalues.size > 0 else 0.0
        except np.linalg.LinAlgError:
            max_eigen = float("inf")

        # Aleatoric: irreducible noise (trace of covariance).
        aleatoric = trace
        # Epistemic: model uncertainty (entropy beyond Gaussian baseline).
        n = cov.shape[0]
        gaussian_entropy = 0.5 * (n * (1.0 + np.log(2.0 * np.pi)) + np.log(max(det, 1e-12)))
        epistemic = max(0.0, entropy - gaussian_entropy)

        return UncertaintyMetrics(
            trace=trace,
            determinant=det,
            entropy=entropy,
            max_eigenvalue=max_eigen,
            aleatoric=aleatoric,
            epistemic=epistemic,
            total=trace + epistemic,
        )

    def propagate_linear(
        self, belief: BeliefDistribution, jacobian: np.ndarray
    ) -> BeliefDistribution:
        """Propagate a Gaussian belief through a linear transform."""
        mean = belief.mean_array()
        cov = belief.covariance_array()
        new_mean = jacobian @ mean
        new_cov = jacobian @ cov @ jacobian.T
        return BeliefDistribution.gaussian(new_mean, new_cov)

    def propagate_nonlinear(
        self,
        belief: BeliefDistribution,
        transform: Callable[[np.ndarray], np.ndarray],
        *,
        num_samples: int = 1000,
        rng: Optional[np.random.Generator] = None,
    ) -> BeliefDistribution:
        """Propagate a Gaussian belief through a nonlinear transform via Monte Carlo."""
        rng = rng or np.random.default_rng()
        mean = belief.mean_array()
        cov = belief.covariance_array()
        n = mean.shape[0]

        samples = rng.multivariate_normal(mean, cov + np.eye(n) * 1e-12, size=num_samples)
        transformed = np.stack([transform(s) for s in samples])

        new_mean = np.mean(transformed, axis=0)
        new_cov = np.cov(transformed, rowvar=False, ddof=0)
        if new_cov.ndim == 0:
            new_cov = np.array([[float(new_cov)]])
        return BeliefDistribution.gaussian(new_mean, new_cov)

    def decay_confidence(
        self, confidence: float, elapsed_seconds: float
    ) -> float:
        """Exponentially decay confidence over time."""
        if not self._config.decay_enabled:
            return confidence
        return confidence * np.exp(
            -self._config.confidence_decay_rate * elapsed_seconds
        )

    def grow_uncertainty(
        self, uncertainty: float, elapsed_seconds: float
    ) -> float:
        """Linearly grow uncertainty over time."""
        if not self._config.decay_enabled:
            return uncertainty
        return uncertainty + self._config.uncertainty_growth_rate * elapsed_seconds

    def aggregate(
        self, uncertainties: Sequence[float], *, method: str = "max"
    ) -> float:
        """Aggregate multiple uncertainty values.

        Supported methods: ``max``, ``mean``, ``rms``, ``sum``.
        """
        if not uncertainties:
            return 0.0
        arr = np.asarray(uncertainties, dtype=np.float64)
        if method == "max":
            return float(np.max(arr))
        if method == "mean":
            return float(np.mean(arr))
        if method == "rms":
            return float(np.sqrt(np.mean(arr**2)))
        if method == "sum":
            return float(np.sum(arr))
        raise ValueError(f"Unknown aggregation method: {method}")

    def combine_covariances(
        self, covariances: Sequence[np.ndarray]
    ) -> np.ndarray:
        """Combine multiple covariances via covariance intersection."""
        if not covariances:
            raise ValueError("No covariances to combine")
        dim = covariances[0].shape[0]
        omega = 1.0 / len(covariances)
        inv_sum = np.zeros((dim, dim), dtype=np.float64)
        for cov in covariances:
            inv_sum += omega * np.linalg.inv(cov + np.eye(dim) * 1e-12)
        return np.linalg.inv(inv_sum)