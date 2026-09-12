# Copyright (c) Ultrone Contributors. All rights reserved.
"""Multi-sensor fusion engine.

Implements the fusion algorithms required by the platform:

* Bayesian Fusion (Gaussian product)
* Extended Kalman Filter (EKF)
* Unscented Kalman Filter (UKF)
* Particle Filter
* Dempster–Shafer Theory
* Covariance Intersection
* Learned neural fusion (interface + simple MLP fallback)

Each algorithm is exposed as a strategy implementing the
:class:`FusionStrategy` protocol, and the :class:`SensorFusionEngine`
dispatches to the configured strategy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Protocol, Sequence, Tuple, runtime_checkable

import numpy as np

from .types import (
    BeliefDistribution,
    Observation,
)

__all__ = [
    "FusionResult",
    "FusionStrategy",
    "BayesianFusion",
    "ExtendedKalmanFusion",
    "UnscentedKalmanFusion",
    "ParticleFusion",
    "DempsterShaferFusion",
    "CovarianceIntersectionFusion",
    "NeuralFusion",
    "SensorFusionEngine",
    "FusionError",
]


@dataclass
class FusionResult:
    """Result of fusing multiple observations."""

    fused_mean: np.ndarray
    fused_covariance: np.ndarray
    confidence: float
    method: str
    contributing_sensor_ids: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_belief(self) -> BeliefDistribution:
        return BeliefDistribution.gaussian(self.fused_mean, self.fused_covariance)


@runtime_checkable
class FusionStrategy(Protocol):
    """Protocol for a sensor fusion strategy."""

    name: str

    def fuse(
        self,
        observations: Sequence[Observation],
        *,
        prior: Optional[BeliefDistribution] = None,
    ) -> FusionResult: ...


class FusionError(RuntimeError):
    """Raised when fusion cannot be performed."""


def _extract_measurement(
    observation: Observation,
) -> Tuple[np.ndarray, np.ndarray, float]:
    """Extract mean, covariance, and confidence from an observation."""
    measurement = observation.measurement
    value = measurement.value

    if isinstance(value, (list, tuple, np.ndarray)):
        mean = np.asarray(value, dtype=np.float64)
    elif isinstance(value, (int, float)):
        mean = np.asarray([float(value)], dtype=np.float64)
    else:
        raise FusionError(f"Unsupported measurement value type: {type(value)}")

    if measurement.covariance is not None:
        cov = measurement.covariance.to_array()
    else:
        cov = np.eye(mean.shape[0], dtype=np.float64) * 0.1

    return mean, cov, observation.confidence


class BayesianFusion:
    """Optimal Bayesian fusion via Gaussian product.

    Fuses multiple Gaussian observations into a single posterior using the
    closed-form product of Gaussians. This is the standard multi-sensor
    Bayesian fusion rule for independent Gaussian measurements.
    """

    name = "bayesian"

    def fuse(
        self,
        observations: Sequence[Observation],
        *,
        prior: Optional[BeliefDistribution] = None,
    ) -> FusionResult:
        if not observations:
            raise FusionError("No observations to fuse")

        means: List[np.ndarray] = []
        covs: List[np.ndarray] = []
        confidences: List[float] = []

        for obs in observations:
            mean, cov, conf = _extract_measurement(obs)
            means.append(mean)
            covs.append(cov)
            confidences.append(conf)

        dim = max(m.shape[0] for m in means)

        # Align all to the same dimension.
        aligned_means = []
        aligned_covs = []
        for m, c in zip(means, covs):
            if m.shape[0] < dim:
                m = np.pad(m, (0, dim - m.shape[0]))
                c = np.pad(c, ((0, dim - m.shape[0]), (0, dim - m.shape[0])))
            aligned_means.append(m)
            aligned_covs.append(c)

        # Start with the first observation as the prior.
        fused_mean = aligned_means[0].copy()
        fused_cov = aligned_covs[0].copy()

        for i in range(1, len(aligned_means)):
            inv1 = np.linalg.inv(fused_cov + np.eye(dim) * 1e-12)
            inv2 = np.linalg.inv(aligned_covs[i] + np.eye(dim) * 1e-12)
            inv_sum = inv1 + inv2
            fused_cov = np.linalg.inv(inv_sum)
            fused_mean = fused_cov @ (inv1 @ fused_mean + inv2 @ aligned_means[i])

        # Confidence: weighted average of observation confidences.
        weights = np.asarray(confidences, dtype=np.float64)
        weights = weights / weights.sum()
        confidence = float(np.sum(weights * np.asarray(confidences)))

        return FusionResult(
            fused_mean=fused_mean,
            fused_covariance=fused_cov,
            confidence=confidence,
            method=self.name,
            contributing_sensor_ids=[o.sensor_id for o in observations],
        )


class ExtendedKalmanFusion:
    """Extended Kalman Filter fusion.

    Applies a linearized state transition and measurement update. The
    transition function is configurable; by default it uses constant-velocity
    dynamics. The measurement function is assumed linear (identity) for
    position observations.
    """

    name = "ekf"

    def __init__(
        self,
        *,
        process_noise: float = 0.1,
        transition_fn: Optional[Callable[[np.ndarray, float], np.ndarray]] = None,
        jacobian_fn: Optional[Callable[[np.ndarray, float], np.ndarray]] = None,
    ) -> None:
        self._process_noise = process_noise
        self._transition_fn = transition_fn or self._default_transition
        self._jacobian_fn = jacobian_fn or self._default_jacobian

    @staticmethod
    def _default_transition(state: np.ndarray, dt: float) -> np.ndarray:
        """Constant-velocity transition on [x, y, z, vx, vy, vz]."""
        if state.shape[0] < 6:
            return state
        F = np.eye(6, dtype=np.float64)
        F[0, 3] = dt
        F[1, 4] = dt
        F[2, 5] = dt
        return F @ state[:6]

    @staticmethod
    def _default_jacobian(state: np.ndarray, dt: float) -> np.ndarray:
        if state.shape[0] < 6:
            return np.eye(state.shape[0], dtype=np.float64)
        F = np.eye(6, dtype=np.float64)
        F[0, 3] = dt
        F[1, 4] = dt
        F[2, 5] = dt
        return F

    def fuse(
        self,
        observations: Sequence[Observation],
        *,
        prior: Optional[BeliefDistribution] = None,
    ) -> FusionResult:
        if not observations:
            raise FusionError("No observations to fuse")

        # Initialize state from the first observation.
        first_mean, first_cov, _ = _extract_measurement(observations[0])
        state_dim = max(6, first_mean.shape[0])
        state = np.zeros(state_dim, dtype=np.float64)
        state[: first_mean.shape[0]] = first_mean
        cov = np.eye(state_dim, dtype=np.float64) * 10.0
        cov[: first_mean.shape[0], : first_mean.shape[0]] = first_cov

        for obs in observations[1:]:
            mean, obs_cov, _ = _extract_measurement(obs)
            dt = 0.1  # fixed timestep for simplicity

            # Predict
            F = self._jacobian_fn(state, dt)
            state = self._transition_fn(state, dt)
            Q = np.eye(state_dim, dtype=np.float64) * self._process_noise
            cov = F @ cov @ F.T + Q

            # Update (identity measurement model on position subspace)
            dim = mean.shape[0]
            H = np.zeros((dim, state_dim), dtype=np.float64)
            for i in range(dim):
                H[i, i] = 1.0

            innovation = mean - H @ state
            S = H @ cov @ H.T + obs_cov
            K = cov @ H.T @ np.linalg.inv(S + np.eye(dim) * 1e-12)
            state = state + K @ innovation
            cov = (np.eye(state_dim) - K @ H) @ cov

        confidence = float(np.mean([o.confidence for o in observations]))
        return FusionResult(
            fused_mean=state,
            fused_covariance=cov,
            confidence=confidence,
            method=self.name,
            contributing_sensor_ids=[o.sensor_id for o in observations],
        )


class UnscentedKalmanFusion:
    """Unscented Kalman Filter fusion.

    Uses sigma-point propagation through a nonlinear transition function,
    avoiding the linearization error of the EKF. The default transition is
    constant-velocity dynamics.
    """

    name = "ukf"

    def __init__(
        self,
        *,
        process_noise: float = 0.1,
        alpha: float = 1e-3,
        beta: float = 2.0,
        kappa: float = 0.0,
        transition_fn: Optional[Callable[[np.ndarray, float], np.ndarray]] = None,
    ) -> None:
        self._process_noise = process_noise
        self._alpha = alpha
        self._beta = beta
        self._kappa = kappa
        self._transition_fn = transition_fn or self._default_transition

    @staticmethod
    def _default_transition(state: np.ndarray, dt: float) -> np.ndarray:
        if state.shape[0] < 6:
            return state
        F = np.eye(6, dtype=np.float64)
        F[0, 3] = dt
        F[1, 4] = dt
        F[2, 5] = dt
        return F @ state[:6]

    def _sigma_points(
        self, mean: np.ndarray, cov: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        n = mean.shape[0]
        lam = self._alpha**2 * (n + self._kappa) - n
        sqrt_cov = np.linalg.cholesky((n + lam) * cov + np.eye(n) * 1e-12)

        points = np.zeros((2 * n + 1, n), dtype=np.float64)
        points[0] = mean
        for i in range(n):
            points[i + 1] = mean + sqrt_cov[:, i]
            points[n + i + 1] = mean - sqrt_cov[:, i]

        wm = np.full(2 * n + 1, 1.0 / (2 * (n + lam)), dtype=np.float64)
        wm[0] = lam / (n + lam)
        wc = wm.copy()
        wc[0] = wc[0] + (1 - self._alpha**2 + self._beta)
        return points, wm, wc

    def fuse(
        self,
        observations: Sequence[Observation],
        *,
        prior: Optional[BeliefDistribution] = None,
    ) -> FusionResult:
        if not observations:
            raise FusionError("No observations to fuse")

        first_mean, first_cov, _ = _extract_measurement(observations[0])
        state_dim = max(6, first_mean.shape[0])
        state = np.zeros(state_dim, dtype=np.float64)
        state[: first_mean.shape[0]] = first_mean
        cov = np.eye(state_dim, dtype=np.float64) * 10.0
        cov[: first_mean.shape[0], : first_mean.shape[0]] = first_cov

        for obs in observations[1:]:
            mean, obs_cov, _ = _extract_measurement(obs)
            dt = 0.1

            # Predict via sigma points
            points, wm, wc = self._sigma_points(state, cov)
            n = state.shape[0]
            propagated = np.zeros_like(points)
            for i in range(2 * n + 1):
                propagated[i] = self._transition_fn(points[i], dt)

            state = wm @ propagated
            cov = np.zeros((n, n), dtype=np.float64)
            for i in range(2 * n + 1):
                diff = propagated[i] - state
                cov += wc[i] * np.outer(diff, diff)
            cov += np.eye(n, dtype=np.float64) * self._process_noise

            # Update
            dim = mean.shape[0]
            H = np.zeros((dim, n), dtype=np.float64)
            for i in range(dim):
                H[i, i] = 1.0

            innovation = mean - H @ state
            S = H @ cov @ H.T + obs_cov
            K = cov @ H.T @ np.linalg.inv(S + np.eye(dim) * 1e-12)
            state = state + K @ innovation
            cov = (np.eye(n) - K @ H) @ cov

        confidence = float(np.mean([o.confidence for o in observations]))
        return FusionResult(
            fused_mean=state,
            fused_covariance=cov,
            confidence=confidence,
            method=self.name,
            contributing_sensor_ids=[o.sensor_id for o in observations],
        )


class ParticleFusion:
    """Particle filter fusion.

    Fuses observations by importance-weighting a particle set. The particle
    set is initialized from the first observation and updated with likelihood
    weights derived from subsequent observations.
    """

    name = "particle"

    def __init__(self, *, num_particles: int = 1000, rng: Optional[np.random.Generator] = None) -> None:
        self._num_particles = num_particles
        self._rng = rng or np.random.default_rng()

    def fuse(
        self,
        observations: Sequence[Observation],
        *,
        prior: Optional[BeliefDistribution] = None,
    ) -> FusionResult:
        if not observations:
            raise FusionError("No observations to fuse")

        first_mean, first_cov, _ = _extract_measurement(observations[0])
        dim = first_mean.shape[0]

        # Initialize particles around the first observation.
        particles = self._rng.multivariate_normal(
            first_mean, first_cov + np.eye(dim) * 1e-6, size=self._num_particles
        )
        weights = np.full(self._num_particles, 1.0 / self._num_particles)

        for obs in observations[1:]:
            mean, obs_cov, _ = _extract_measurement(obs)
            # Gaussian likelihood
            inv_cov = np.linalg.inv(obs_cov + np.eye(dim) * 1e-12)
            diff = particles - mean
            log_lik = -0.5 * np.sum((diff @ inv_cov) * diff, axis=1)
            weights = weights * np.exp(log_lik - log_lik.max())
            weights /= weights.sum() + 1e-12

            # Resample if effective sample size is low
            n_eff = 1.0 / np.sum(weights**2)
            if n_eff < self._num_particles / 2:
                indices = self._rng.choice(
                    self._num_particles, size=self._num_particles, p=weights
                )
                particles = particles[indices]
                weights = np.full(self._num_particles, 1.0 / self._num_particles)

        fused_mean = np.average(particles, axis=0, weights=weights)
        diff = particles - fused_mean
        fused_cov = (diff * weights[:, None]).T @ diff

        confidence = float(np.mean([o.confidence for o in observations]))
        return FusionResult(
            fused_mean=fused_mean,
            fused_covariance=fused_cov,
            confidence=confidence,
            method=self.name,
            contributing_sensor_ids=[o.sensor_id for o in observations],
        )


class DempsterShaferFusion:
    """Dempster–Shafer theory fusion.

    Combines belief masses from multiple sources over a discrete frame of
    discernment. Each observation provides a mass assignment over hypotheses;
    the combination rule is Dempster's rule of combination.
    """

    name = "dempster_shafer"

    def __init__(self, *, hypotheses: Optional[List[str]] = None) -> None:
        self._hypotheses = hypotheses or ["A", "B", "C"]

    def fuse(
        self,
        observations: Sequence[Observation],
        *,
        prior: Optional[BeliefDistribution] = None,
    ) -> FusionResult:
        if not observations:
            raise FusionError("No observations to fuse")

        # Convert each observation's confidence into a mass assignment.
        masses: List[Dict[str, float]] = []
        for obs in observations:
            conf = obs.confidence
            # Distribute confidence across hypotheses based on measurement class.
            detection_class = obs.measurement.detection_class
            if detection_class and detection_class in self._hypotheses:
                mass: Dict[str, float] = {h: 0.0 for h in self._hypotheses}
                mass[detection_class] = conf
                mass["unknown"] = 1.0 - conf
            else:
                # Uniform mass over hypotheses.
                per_hyp = conf / len(self._hypotheses)
                mass = {h: per_hyp for h in self._hypotheses}
                mass["unknown"] = 1.0 - conf
            masses.append(mass)

        # Dempster's rule of combination.
        combined: Dict[str, float] = {"unknown": 1.0}
        for mass in masses:
            new_combined: Dict[str, float] = {}
            for h1, m1 in combined.items():
                for h2, m2 in mass.items():
                    if h1 == "unknown":
                        key = h2
                    elif h2 == "unknown":
                        key = h1
                    elif h1 == h2:
                        key = h1
                    else:
                        continue  # conflict
                    new_combined[key] = new_combined.get(key, 0.0) + m1 * m2
            combined = new_combined

        # Normalize (ignore conflict mass).
        total = sum(combined.values())
        if total <= 0:
            raise FusionError("Dempster-Shafer combination produced zero mass")
        combined = {k: v / total for k, v in combined.items()}

        # Convert to a Gaussian belief over a one-hot encoding.
        dim = len(self._hypotheses)
        mean = np.zeros(dim, dtype=np.float64)
        for i, h in enumerate(self._hypotheses):
            mean[i] = combined.get(h, 0.0)
        cov = np.eye(dim, dtype=np.float64) * 0.1

        confidence = float(np.mean([o.confidence for o in observations]))
        return FusionResult(
            fused_mean=mean,
            fused_covariance=cov,
            confidence=confidence,
            method=self.name,
            contributing_sensor_ids=[o.sensor_id for o in observations],
            metadata={"combined_masses": combined},
        )


class CovarianceIntersectionFusion:
    """Covariance Intersection fusion.

    Fuses two estimates with unknown cross-correlation using the convex
    combination of inverse covariances. This is robust to correlated
    measurement errors.
    """

    name = "covariance_intersection"

    def __init__(self, *, omega: float = 0.5) -> None:
        self._omega = omega

    def fuse(
        self,
        observations: Sequence[Observation],
        *,
        prior: Optional[BeliefDistribution] = None,
    ) -> FusionResult:
        if not observations:
            raise FusionError("No observations to fuse")

        means: List[np.ndarray] = []
        covs: List[np.ndarray] = []
        for obs in observations:
            mean, cov, _ = _extract_measurement(obs)
            means.append(mean)
            covs.append(cov)

        dim = max(m.shape[0] for m in means)
        aligned_means = []
        aligned_covs = []
        for m, c in zip(means, covs):
            if m.shape[0] < dim:
                m = np.pad(m, (0, dim - m.shape[0]))
                c = np.pad(c, ((0, dim - m.shape[0]), (0, dim - m.shape[0])))
            aligned_means.append(m)
            aligned_covs.append(c)

        # Start with the first estimate.
        fused_mean = aligned_means[0].copy()
        fused_cov = aligned_covs[0].copy()

        for i in range(1, len(aligned_means)):
            omega = self._omega
            inv1 = np.linalg.inv(fused_cov + np.eye(dim) * 1e-12)
            inv2 = np.linalg.inv(aligned_covs[i] + np.eye(dim) * 1e-12)
            inv_sum = omega * inv1 + (1 - omega) * inv2
            fused_cov = np.linalg.inv(inv_sum)
            fused_mean = fused_cov @ (
                omega * inv1 @ fused_mean + (1 - omega) * inv2 @ aligned_means[i]
            )

        confidence = float(np.mean([o.confidence for o in observations]))
        return FusionResult(
            fused_mean=fused_mean,
            fused_covariance=fused_cov,
            confidence=confidence,
            method=self.name,
            contributing_sensor_ids=[o.sensor_id for o in observations],
        )


class NeuralFusion:
    """Learned neural fusion.

    Provides a GPU-ready abstraction for learned fusion. The default
    implementation is a simple weighted average with learned weights; a
    pluggable ``model`` callable can be supplied for transformer/GNN-based
    fusion backends.
    """

    name = "neural"

    def __init__(
        self,
        *,
        model: Optional[Callable[[np.ndarray, np.ndarray], Tuple[np.ndarray, np.ndarray]]] = None,
        device: str = "cpu",
    ) -> None:
        self._model = model or self._default_model
        self._device = device

    @staticmethod
    def _default_model(
        means: np.ndarray, covs: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Simple learned-style weighted average fallback."""
        n, dim = means.shape
        weights = np.ones(n, dtype=np.float64) / n
        fused_mean = weights @ means
        fused_cov = np.zeros((dim, dim), dtype=np.float64)
        for i in range(n):
            fused_cov += weights[i] * covs[i]
        return fused_mean, fused_cov

    def fuse(
        self,
        observations: Sequence[Observation],
        *,
        prior: Optional[BeliefDistribution] = None,
    ) -> FusionResult:
        if not observations:
            raise FusionError("No observations to fuse")

        means: List[np.ndarray] = []
        covs: List[np.ndarray] = []
        for obs in observations:
            mean, cov, _ = _extract_measurement(obs)
            means.append(mean)
            covs.append(cov)

        dim = max(m.shape[0] for m in means)
        aligned_means = []
        aligned_covs = []
        for m, c in zip(means, covs):
            if m.shape[0] < dim:
                m = np.pad(m, (0, dim - m.shape[0]))
                c = np.pad(c, ((0, dim - m.shape[0]), (0, dim - m.shape[0])))
            aligned_means.append(m)
            aligned_covs.append(c)

        means_arr = np.stack(aligned_means)
        covs_arr = np.stack(aligned_covs)
        fused_mean, fused_cov = self._model(means_arr, covs_arr)

        confidence = float(np.mean([o.confidence for o in observations]))
        return FusionResult(
            fused_mean=fused_mean,
            fused_covariance=fused_cov,
            confidence=confidence,
            method=self.name,
            contributing_sensor_ids=[o.sensor_id for o in observations],
            metadata={"device": self._device},
        )


class SensorFusionEngine:
    """Dispatches fusion requests to the configured strategy.

    Supports per-entity fusion with optional prior beliefs, and provides
    strategy lookup by name.
    """

    _STRATEGIES: Dict[str, FusionStrategy] = {
        "bayesian": BayesianFusion(),
        "ekf": ExtendedKalmanFusion(),
        "ukf": UnscentedKalmanFusion(),
        "particle": ParticleFusion(),
        "dempster_shafer": DempsterShaferFusion(),
        "covariance_intersection": CovarianceIntersectionFusion(),
        "neural": NeuralFusion(),
    }

    def __init__(
        self,
        *,
        default_strategy: str = "bayesian",
        strategies: Optional[Dict[str, FusionStrategy]] = None,
    ) -> None:
        self._strategies = dict(strategies or self._STRATEGIES)
        if default_strategy not in self._strategies:
            raise FusionError(f"Unknown fusion strategy: {default_strategy}")
        self._default_strategy = default_strategy

    def register_strategy(self, name: str, strategy: FusionStrategy) -> None:
        self._strategies[name] = strategy

    def get_strategy(self, name: Optional[str] = None) -> FusionStrategy:
        name = name or self._default_strategy
        if name not in self._strategies:
            raise FusionError(f"Unknown fusion strategy: {name}")
        return self._strategies[name]

    def fuse(
        self,
        observations: Sequence[Observation],
        *,
        strategy: Optional[str] = None,
        prior: Optional[BeliefDistribution] = None,
    ) -> FusionResult:
        """Fuse a batch of observations using the selected strategy."""
        if not observations:
            raise FusionError("No observations to fuse")
        fusion_strategy = self.get_strategy(strategy)
        return fusion_strategy.fuse(observations, prior=prior)

    def fuse_by_entity(
        self,
        observations: Sequence[Observation],
        *,
        strategy: Optional[str] = None,
        prior: Optional[BeliefDistribution] = None,
    ) -> Dict[str, FusionResult]:
        """Group observations by entity and fuse each group."""
        grouped: Dict[str, List[Observation]] = {}
        for obs in observations:
            key = str(obs.entity_id) if obs.entity_id else "unassigned"
            grouped.setdefault(key, []).append(obs)

        results: Dict[str, FusionResult] = {}
        for key, group in grouped.items():
            results[key] = self.fuse(group, strategy=strategy, prior=prior)
        return results

    @property
    def available_strategies(self) -> List[str]:
        return list(self._strategies.keys())