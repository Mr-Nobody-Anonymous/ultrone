# Copyright (c) Ultrone Contributors. All rights reserved.
"""Belief state estimation using Bayesian inference.

Implements recursive Bayesian filtering for entity states supporting:

* Gaussian belief states (Extended / Unscented Kalman-style updates)
* Particle belief states with importance resampling
* Categorical beliefs over discrete hypotheses (e.g., entity type, intent)
* Information gain computation between belief distributions (KL divergence)
* Entropy-based uncertainty quantification
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from .types import (
    BeliefDistribution,
    BeliefDistributionType,
    BeliefUpdate,
    CovarianceMatrix,
    EntityID,
)

__all__ = [
    "BeliefStateEstimator",
    "BeliefUpdateError",
    "kl_divergence",
    "entropy",
    "gaussian_product",
]


def entropy(belief: BeliefDistribution) -> float:
    """Shannon entropy of a belief distribution (nats)."""
    return belief.entropy()


def kl_divergence(
    posterior: BeliefDistribution, prior: BeliefDistribution
) -> float:
    """KL divergence D_KL(posterior || prior) for Gaussian or categorical beliefs."""
    if (
        posterior.distribution_type
        in (BeliefDistributionType.GAUSSIAN, BeliefDistributionType.DETERMINISTIC)
        and prior.distribution_type
        in (BeliefDistributionType.GAUSSIAN, BeliefDistributionType.DETERMINISTIC)
    ):
        mu1 = posterior.mean_array()
        mu0 = prior.mean_array()
        sigma1 = posterior.covariance_array()
        sigma0 = prior.covariance_array()

        n = mu1.shape[0]
        if mu0.shape[0] != n:
            min_dim = min(n, mu0.shape[0])
            mu1 = mu1[:min_dim]
            mu0 = mu0[:min_dim]
            sigma1 = sigma1[:min_dim, :min_dim]
            sigma0 = sigma0[:min_dim, :min_dim]
            n = min_dim

        diff = mu1 - mu0
        try:
            inv_sigma0 = np.linalg.inv(sigma0 + np.eye(n) * 1e-12)
            sign, logdet_sigma0 = np.linalg.slogdet(sigma0 + np.eye(n) * 1e-12)
            sign1, logdet_sigma1 = np.linalg.slogdet(sigma1 + np.eye(n) * 1e-12)
            trace_term = float(np.trace(inv_sigma0 @ sigma1))
            quad_term = float(diff @ inv_sigma0 @ diff)
            return 0.5 * (trace_term + quad_term - n + logdet_sigma0 - logdet_sigma1)
        except np.linalg.LinAlgError:
            return float("inf")

    if (
        posterior.distribution_type == BeliefDistributionType.CATEGORICAL
        and posterior.categorical_probs is not None
        and prior.categorical_probs is not None
    ):
        keys = set(posterior.categorical_probs) | set(prior.categorical_probs)
        total = 0.0
        for key in keys:
            p = posterior.categorical_probs.get(key, 0.0)
            q = prior.categorical_probs.get(key, 0.0)
            if p > 0:
                total += p * math.log(p / max(q, 1e-12))
        return total

    raise ValueError(
        "KL divergence only supports Gaussian and categorical beliefs"
    )


def gaussian_product(
    mean1: np.ndarray, cov1: np.ndarray, mean2: np.ndarray, cov2: np.ndarray
) -> Tuple[np.ndarray, np.ndarray]:
    """Product of two multivariate Gaussians (unnormalized form).

    Returns the posterior ``(mean, covariance)`` of
    N(x; m1, S1) * N(x; m2, S2) ∝ N(x; m, S).
    """
    inv1 = np.linalg.inv(cov1 + np.eye(cov1.shape[0]) * 1e-12)
    inv2 = np.linalg.inv(cov2 + np.eye(cov2.shape[0]) * 1e-12)
    inv_sum = inv1 + inv2
    cov = np.linalg.inv(inv_sum)
    mean = cov @ (inv1 @ mean1 + inv2 @ mean2)
    return mean, cov


class BeliefUpdateError(RuntimeError):
    """Raised when a belief update cannot be performed."""


class BeliefStateEstimator:
    """Recursive Bayesian belief estimator.

    Maintains per-entity posterior beliefs and applies observation-driven
    updates using the appropriate fusion rule:

    * Gaussian observations -> optimal Bayesian product / Kalman-style update
    * Particle beliefs -> importance weighting + resampling
    * Categorical observations -> multiplicative categorical update
    """

    def __init__(
        self,
        *,
        schedule_resampling: bool = True,
        effective_sample_threshold: float = 0.5,
        epsilon: float = 1e-12,
    ) -> None:
        self._beliefs: Dict[str, BeliefDistribution] = {}
        self._schedule_resampling = schedule_resampling
        self._effective_sample_threshold = effective_sample_threshold
        self._epsilon = epsilon
        self._updates: List[BeliefUpdate] = []

    def initialize_gaussian(
        self, entity_id: EntityID, mean: Sequence[float], cov: np.ndarray
    ) -> BeliefDistribution:
        belief = BeliefDistribution.gaussian(mean, cov)
        self._beliefs[str(entity_id)] = belief
        return belief

    def initialize_particles(
        self, entity_id: EntityID, particles: Sequence[Sequence[float]]
    ) -> BeliefDistribution:
        pts = np.asarray(particles, dtype=np.float64)
        n = pts.shape[0]
        weights = np.full(n, 1.0 / n, dtype=np.float64)
        belief = BeliefDistribution(
            distribution_type=BeliefDistributionType.PARTICLE,
            particles=pts.tolist(),
            particle_weights=weights.tolist(),
            sample_count=n,
        )
        self._beliefs[str(entity_id)] = belief
        return belief

    def initialize_categorical(
        self, entity_id: EntityID, probs: Dict[str, float]
    ) -> BeliefDistribution:
        total = sum(probs.values())
        normalized = {k: v / total for k, v in probs.items()}
        belief = BeliefDistribution(
            distribution_type=BeliefDistributionType.CATEGORICAL,
            categorical_probs=normalized,
            sample_count=len(normalized),
        )
        self._beliefs[str(entity_id)] = belief
        return belief

    def get_belief(self, entity_id: EntityID) -> Optional[BeliefDistribution]:
        return self._beliefs.get(str(entity_id))

    def gaussian_update(
        self,
        entity_id: EntityID,
        observation_mean: Sequence[float],
        observation_covariance: np.ndarray,
        *,
        observation_id: Optional[str] = None,
        method: str = "bayesian_product",
    ) -> BeliefDistribution:
        """Bayesian update of a Gaussian belief with a Gaussian observation."""
        current = self._beliefs.get(str(entity_id))
        if current is None:
            raise BeliefUpdateError(
                f"No belief exists for entity {entity_id}; initialize first"
            )

        if current.distribution_type not in (
            BeliefDistributionType.GAUSSIAN,
            BeliefDistributionType.DETERMINISTIC,
        ):
            raise BeliefUpdateError(
                "Gaussian update requires a Gaussian or deterministic belief"
            )

        prior_mean = current.mean_array()
        prior_cov = current.covariance_array()
        obs_mean = np.asarray(observation_mean, dtype=np.float64)
        obs_cov = np.asarray(observation_covariance, dtype=np.float64)

        # Align dimensions for partial observations.
        dim = obs_mean.shape[0]
        if prior_mean.shape[0] < dim:
            raise BeliefUpdateError(
                f"Observation dim {dim} exceeds belief dim {prior_mean.shape[0]}"
            )

        # The update acts on the subspace covered by the observation. For
        # simplicity and correctness with shared dimensions, we use the full
        # Gaussian product on aligned subspaces.
        posterior_mean, posterior_cov = gaussian_product(
            prior_mean[:dim], prior_cov[:dim, :dim], obs_mean, obs_cov
        )

        full_mean = prior_mean.copy()
        full_mean[:dim] = posterior_mean
        full_cov = prior_cov.copy()
        full_cov[:dim, :dim] = posterior_cov

        new_belief = BeliefDistribution.gaussian(full_mean, full_cov)
        self._beliefs[str(entity_id)] = new_belief

        gain = kl_divergence(new_belief, current)
        self._updates.append(
            BeliefUpdate(
                entity_id=entity_id,
                previous_belief=current,
                updated_belief=new_belief,
                information_gain=gain,
                contributing_observation_ids=[observation_id] if observation_id else [],
                method=method,
            )
        )
        return new_belief

    def particle_update(
        self,
        entity_id: EntityID,
        likelihood_weights: Sequence[float],
        *,
        observation_id: Optional[str] = None,
        method: str = "importance_weighting",
    ) -> BeliefDistribution:
        """Update a particle belief with likelihood weights and resample."""
        current = self._beliefs.get(str(entity_id))
        if current is None or current.particles is None:
            raise BeliefUpdateError(
                f"Particle update requires an initialized particle belief for {entity_id}"
            )

        pts = np.asarray(current.particles, dtype=np.float64)
        w = np.asarray(current.particle_weights or np.full(pts.shape[0], 1.0 / pts.shape[0]))
        lik = np.asarray(likelihood_weights, dtype=np.float64)

        if lik.shape[0] != pts.shape[0]:
            raise BeliefUpdateError(
                f"Likelihood weights ({lik.shape[0]}) must match particle count ({pts.shape[0]})"
            )

        new_w = w * lik + self._epsilon
        new_w /= new_w.sum()

        if self._schedule_resampling:
            n_eff = 1.0 / float(np.sum(new_w**2))
            if n_eff < self._effective_sample_threshold * pts.shape[0]:
                resampled = self._resample(pts, new_w)
                pts = resampled
                new_w = np.full(pts.shape[0], 1.0 / pts.shape[0])

        new_belief = BeliefDistribution(
            distribution_type=BeliefDistributionType.PARTICLE,
            particles=pts.tolist(),
            particle_weights=new_w.tolist(),
            sample_count=pts.shape[0],
        )
        self._beliefs[str(entity_id)] = new_belief

        self._updates.append(
            BeliefUpdate(
                entity_id=entity_id,
                previous_belief=current,
                updated_belief=new_belief,
                information_gain=entropy(current) - entropy(new_belief),
                contributing_observation_ids=[observation_id] if observation_id else [],
                method=method,
            )
        )
        return new_belief

    def categorical_update(
        self,
        entity_id: EntityID,
        observation_probs: Dict[str, float],
        *,
        observation_id: Optional[str] = None,
        method: str = "categorical_bayes",
    ) -> BeliefDistribution:
        """Multiplicative categorical Bayesian update."""
        current = self._beliefs.get(str(entity_id))
        if current is None or current.categorical_probs is None:
            raise BeliefUpdateError(
                f"Categorical update requires an initialized categorical belief for {entity_id}"
            )

        prior = current.categorical_probs
        keys = set(prior) | set(observation_probs)
        posterior: Dict[str, float] = {}
        for key in keys:
            posterior[key] = prior.get(key, 0.0) * observation_probs.get(
                key, self._epsilon
            )

        total = sum(posterior.values())
        if total <= 0:
            raise BeliefUpdateError("Categorical posterior has zero mass")
        posterior = {k: v / total for k, v in posterior.items()}

        new_belief = BeliefDistribution(
            distribution_type=BeliefDistributionType.CATEGORICAL,
            categorical_probs=posterior,
            sample_count=len(posterior),
        )
        self._beliefs[str(entity_id)] = new_belief

        self._updates.append(
            BeliefUpdate(
                entity_id=entity_id,
                previous_belief=current,
                updated_belief=new_belief,
                information_gain=kl_divergence(new_belief, current),
                contributing_observation_ids=[observation_id] if observation_id else [],
                method=method,
            )
        )
        return new_belief

    @staticmethod
    def _resample(
        particles: np.ndarray, weights: np.ndarray, rng: Optional[np.random.Generator] = None
    ) -> np.ndarray:
        """Systematic resampling."""
        rng = rng or np.random.default_rng()
        n = particles.shape[0]
        u = (np.arange(n) + rng.random()) / n
        cumsum = np.cumsum(weights)
        cumsum[-1] = 1.0
        indices = np.searchsorted(cumsum, u, side="right")
        indices = np.clip(indices, 0, n - 1)
        return particles[indices]

    def predict(self, entity_id: EntityID, dt: float) -> BeliefDistribution:
        """Time-evolve a Gaussian belief with constant-velocity dynamics.

        Applies the standard linear prediction step:
        ``P' = F P F^T + Q`` with a zero-mean position-space process noise.
        """
        current = self._beliefs.get(str(entity_id))
        if current is None:
            raise BeliefUpdateError(f"No belief exists for entity {entity_id}")

        if current.distribution_type not in (
            BeliefDistributionType.GAUSSIAN,
            BeliefDistributionType.DETERMINISTIC,
        ):
            return current

        mean = current.mean_array()
        cov = current.covariance_array()
        dim = mean.shape[0]

        # 3D constant velocity transition on position+velocity.
        if dim >= 6:
            F = np.eye(6, dtype=np.float64)
            F[0, 3] = dt
            F[1, 4] = dt
            F[2, 5] = dt
            m = mean[:6]
            c = cov[:6, :6]
            predicted_mean = F @ m
            process_noise = np.eye(6, dtype=np.float64) * (dt**2) * 0.1
            process_noise[3:, 3:] *= 0.01
            predicted_cov = F @ c @ F.T + process_noise

            full_mean = mean.copy()
            full_mean[:6] = predicted_mean
            full_cov = cov.copy()
            full_cov[:6, :6] = predicted_cov

            new_belief = BeliefDistribution.gaussian(full_mean, full_cov)
            self._beliefs[str(entity_id)] = new_belief
            return new_belief

        # Fallback: inflate uncertainty.
        predicted_cov = cov + np.eye(dim, dtype=np.float64) * (dt**2) * 0.1
        new_belief = BeliefDistribution.gaussian(mean, predicted_cov)
        self._beliefs[str(entity_id)] = new_belief
        return new_belief

    def history(self, limit: Optional[int] = None) -> List[BeliefUpdate]:
        updates = self._updates
        if limit is not None:
            updates = updates[-limit:]
        return list(updates)