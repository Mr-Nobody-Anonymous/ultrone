# Copyright (c) Ultrone Contributors. All rights reserved.
"""Kalman Filter, Extended Kalman Filter, and Unscented Kalman Filter."""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("Ultrone.Brain.Perception.Probabilistic.KF")


@dataclass
class KFConfig:
    """Configuration for Kalman filters."""
    dim_state: int = 4
    dim_obs: int = 2
    process_noise: float = 0.1
    observation_noise: float = 0.1


class KalmanFilter:
    """Linear Kalman Filter for Gaussian state estimation."""

    def __init__(self, config: Optional[KFConfig] = None):
        self.config = config or KFConfig()
        dim = self.config.dim_state
        self._x = np.zeros(dim)  # state
        self._P = np.eye(dim) * 100.0  # covariance
        self._F = np.eye(dim)  # state transition
        self._H = np.zeros((self.config.dim_obs, dim))  # observation matrix
        self._H[:self.config.dim_obs, :self.config.dim_obs] = np.eye(self.config.dim_obs)
        self._Q = np.eye(dim) * self.config.process_noise
        self._R = np.eye(self.config.dim_obs) * self.config.observation_noise

    def predict(self, dt: float = 1.0, step: int = 1) -> np.ndarray:
        """Predict next state."""
        self._x = self._F @ self._x
        self._P = self._F @ self._P @ self._F.T + self._Q
        return self._x.copy()

    def update(self, z: np.ndarray) -> np.ndarray:
        """Update state estimate with observation."""
        y = z - self._H @ self._x  # innovation
        S = self._H @ self._P @ self._H.T + self._R
        K = self._P @ self._H.T @ np.linalg.inv(S)  # Kalman gain
        self._x = self._x + K @ y
        self._P = (np.eye(len(self._x)) - K @ self._H) @ self._P
        return self._x.copy()

    @property
    def state(self) -> np.ndarray:
        return self._x.copy()

    @property
    def covariance(self) -> np.ndarray:
        return self._P.copy()

    def get_stats(self) -> Dict[str, Any]:
        return {"type": "KalmanFilter", "dim_state": self.config.dim_state}


class ExtendedKalmanFilter(KalmanFilter):
    """Extended Kalman Filter for non-linear systems.

    Linearises the state transition and observation functions using
    Jacobian matrices, then applies the standard Kalman update.

    Subclass and override ``_state_transition(state)`` and
    ``_observation_model(state)`` for domain-specific non-linear dynamics.
    """

    def __init__(self, config: Optional[KFConfig] = None):
        super().__init__(config)

    def _state_transition(self, state: np.ndarray, dt: float = 1.0) -> np.ndarray:
        """Non-linear state transition function (identity by default)."""
        return self._F @ state

    def _observation_model(self, state: np.ndarray) -> np.ndarray:
        """Non-linear observation function (linear by default)."""
        return self._H @ state

    def _state_jacobian(self, state: np.ndarray, dt: float = 1.0) -> np.ndarray:
        """Jacobian of the state transition function (F by default)."""
        return self._F

    def _obs_jacobian(self, state: np.ndarray) -> np.ndarray:
        """Jacobian of the observation function (H by default)."""
        return self._H

    def predict(self, dt: float = 1.0, step: int = 1) -> np.ndarray:
        """EKF predict step: apply non-linear transition, then linearise."""
        F_jac = self._state_jacobian(self._x, dt)
        self._x = self._state_transition(self._x, dt)
        self._P = F_jac @ self._P @ F_jac.T + self._Q
        return self._x.copy()

    def update(self, z: np.ndarray) -> np.ndarray:
        """EKF update step: linearise observation, then standard KF update."""
        H_jac = self._obs_jacobian(self._x)
        y = z - self._observation_model(self._x)  # innovation
        S = H_jac @ self._P @ H_jac.T + self._R
        K = self._P @ H_jac.T @ np.linalg.inv(S)  # Kalman gain
        self._x = self._x + K @ y
        self._P = (np.eye(len(self._x)) - K @ H_jac) @ self._P
        return self._x.copy()

    def get_stats(self) -> Dict[str, Any]:
        return {"type": "ExtendedKalmanFilter", "dim_state": self.config.dim_state}


class UnscentedKalmanFilter(KalmanFilter):
    """Unscented Kalman Filter using sigma points.

    Avoids linearisation by propagating a set of deterministically
    chosen sigma points through the non-linear functions, then
    reconstructing the Gaussian from the transformed points.
    """

    def __init__(self, config: Optional[KFConfig] = None):
        super().__init__(config)
        self._alpha: float = 1.0  # sigma point spread
        self._beta: float = 2.0   # prior knowledge (2 is optimal for Gaussian)
        self._kappa: float = 0.0  # secondary scaling parameter
        self._lambda_: float = 0.0  # computed from alpha, kappa, n

    def _compute_sigma_weights(self, n: int) -> Tuple[float, float, float, np.ndarray]:
        """Compute sigma point weights for the Unscented Transform.

        Returns
        -------
        Tuple of (lambda, mean_weight_0, cov_weight_0, weight_i)
        """
        lam = self._alpha ** 2 * (n + self._kappa) - n
        w_m0 = lam / (n + lam)
        w_c0 = w_m0 + (1 - self._alpha ** 2 + self._beta)
        w_i = 1.0 / (2.0 * (n + lam))
        return lam, w_m0, w_c0, w_i

    def _sigma_points(self, x: np.ndarray, P: np.ndarray, lam: float) -> np.ndarray:
        """Generate 2n+1 sigma points from state x and covariance P."""
        n = len(x)
        sigma_pts = np.zeros((2 * n + 1, n))
        sigma_pts[0] = x
        try:
            sqrt_P = np.linalg.cholesky((n + lam) * P)
        except np.linalg.LinAlgError:
            sqrt_P = np.linalg.cholesky((n + lam) * P + 1e-6 * np.eye(n))
        for i in range(n):
            sigma_pts[i + 1] = x + sqrt_P[:, i]
            sigma_pts[n + i + 1] = x - sqrt_P[:, i]
        return sigma_pts

    def _unscented_transform(
        self,
        sigma_pts: np.ndarray,
        w_m0: float,
        w_c0: float,
        w_i: float,
        nonlinear_fn,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Apply non-linear function to sigma points and reconstruct Gaussian."""
        n_pts = len(sigma_pts)
        transformed = np.array([nonlinear_fn(sp) for sp in sigma_pts])

        # Compute weighted mean
        mean = w_m0 * transformed[0]
        for i in range(1, n_pts):
            mean += w_i * transformed[i]

        # Compute weighted covariance
        cov = w_c0 * np.outer(transformed[0] - mean, transformed[0] - mean)
        for i in range(1, n_pts):
            diff = transformed[i] - mean
            cov += w_i * np.outer(diff, diff)

        # Cross-covariance for state-measurement
        cross = w_c0 * np.outer(sigma_pts[0] - self._x, transformed[0] - mean)
        for i in range(1, n_pts):
            diff_x = sigma_pts[i] - self._x
            diff_z = transformed[i] - mean
            cross += w_i * np.outer(diff_x, diff_z)

        return mean, cov, cross

    def predict(self, dt: float = 1.0, step: int = 1) -> np.ndarray:
        """UKF predict step using sigma points through state transition."""
        n = len(self._x)
        lam, w_m0, w_c0, w_i = self._compute_sigma_weights(n)

        # Generate sigma points
        sigma_pts = self._sigma_points(self._x, self._P, lam)

        # Propagate through state transition
        def f(sp: np.ndarray) -> np.ndarray:
            return self._F @ sp

        mean, cov, _ = self._unscented_transform(sigma_pts, w_m0, w_c0, w_i, f)
        self._x = mean
        self._P = cov + self._Q  # Add process noise
        return self._x.copy()

    def update(self, z: np.ndarray) -> np.ndarray:
        """UKF update step using sigma points through observation function."""
        n = len(self._x)
        lam, w_m0, w_c0, w_i = self._compute_sigma_weights(n)

        # Generate new sigma points from predicted state
        sigma_pts = self._sigma_points(self._x, self._P, lam)

        # Propagate through observation function
        def h(sp: np.ndarray) -> np.ndarray:
            return self._H @ sp

        z_pred, S, cross = self._unscented_transform(sigma_pts, w_m0, w_c0, w_i, h)
        S += self._R  # Add observation noise

        # Kalman gain
        K = cross @ np.linalg.inv(S)

        # Update state and covariance
        y = z - z_pred  # innovation
        self._x = self._x + K @ y
        self._P = self._P - K @ S @ K.T
        return self._x.copy()

    def get_stats(self) -> Dict[str, Any]:
        return {"type": "UnscentedKalmanFilter", "dim_state": self.config.dim_state}
