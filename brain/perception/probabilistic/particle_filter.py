# Copyright (c) Ultrone Contributors. All rights reserved.
"""Particle Filter (Sequential Monte Carlo) for non-linear state estimation."""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Union

logger = logging.getLogger("Ultrone.Brain.Perception.Probabilistic.PF")


@dataclass
class ParticleFilterConfig:
    """Configuration for Particle Filter."""
    num_particles: int = 1000
    resample_threshold: float = 0.5
    dim_state: int = 4


class ParticleFilter:
    """Particle Filter for non-linear, non-Gaussian state estimation."""

    def __init__(self, config: Optional[ParticleFilterConfig] = None):
        self.config = config or ParticleFilterConfig()
        self._particles = np.random.randn(self.config.num_particles, self.config.dim_state)
        self._weights = np.ones(self.config.num_particles) / self.config.num_particles

    def predict(self, transition_fn: Optional[Callable] = None, step: int = 1) -> np.ndarray:
        """Apply transition function to all particles.
        
        If no transition_fn is provided, returns the mean state.
        """
        if transition_fn is not None:
            self._particles = transition_fn(self._particles)
        return self.mean_state

    def update(self, likelihood_fn: Callable[[np.ndarray], np.ndarray]) -> None:
        """Update weights based on observation likelihood."""
        self._weights *= likelihood_fn(self._particles)
        self._weights /= self._weights.sum() + 1e-10
        if 1.0 / (self._weights ** 2).sum() < self.config.resample_threshold * self.config.num_particles:
            self._resample()

    def _resample(self) -> None:
        """Systematic resampling."""
        n = self.config.num_particles
        indices = np.random.choice(n, n, p=self._weights)
        self._particles = self._particles[indices]
        self._weights = np.ones(n) / n

    @property
    def mean_state(self) -> np.ndarray:
        return (self._particles * self._weights[:, np.newaxis]).sum(axis=0)

    def get_stats(self) -> Dict[str, Any]:
        return {"type": "ParticleFilter", "particles": self.config.num_particles}
