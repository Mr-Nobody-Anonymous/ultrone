"""Normalizing Flows for Tactical Planning - flexible density estimation for complex tactical distributions."""

from __future__ import annotations

import math
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Callable, Any


@dataclass
class FlowConfig:
    """Configuration for the Normalizing Flow planner."""
    input_dim: int = 64
    n_flows: int = 4
    hidden_dim: int = 64
    flow_type: str = "real_nvp"  # "real_nvp", "maf", "glow"
    learning_rate: float = 1e-3


class RealNVPBlock:
    """Real-valued Non-Volume Preserving (RealNVP) transformation block.

    Implements an affine coupling layer for normalizing flows.
    """

    def __init__(self, input_dim: int, hidden_dim: int):
        self.input_dim = input_dim
        # Split dimension
        self.d = input_dim // 2

        # Scale and translation networks (simplified as random projections)
        self.scale_net = np.random.randn(self.d, hidden_dim) * 0.01
        self.scale_out = np.random.randn(hidden_dim, self.d) * 0.01
        self.trans_net = np.random.randn(self.d, hidden_dim) * 0.01
        self.trans_out = np.random.randn(hidden_dim, self.d) * 0.01

    def forward(self, x: np.ndarray) -> Tuple[np.ndarray, float]:
        """Forward transformation: y = f(x)."""
        x1, x2 = x[..., :self.d], x[..., self.d:]

        # Compute scale and translation from x1
        h = np.tanh(x1 @ self.scale_net)
        log_s = h @ self.scale_out
        t = np.tanh(x1 @ self.trans_net) @ self.trans_out

        # Affine transformation
        y1 = x1
        y2 = x2 * np.exp(log_s) + t

        # Log determinant
        log_det = np.sum(log_s, axis=-1)

        y = np.concatenate([y1, y2], axis=-1)
        return y, float(log_det.mean())

    def inverse(self, y: np.ndarray) -> np.ndarray:
        """Inverse transformation: x = f^{-1}(y)."""
        y1, y2 = y[..., :self.d], y[..., self.d:]

        # Compute scale and translation from y1
        h = np.tanh(y1 @ self.scale_net)
        log_s = h @ self.scale_out
        t = np.tanh(y1 @ self.trans_net) @ self.trans_out

        # Inverse affine transformation
        x1 = y1
        x2 = (y2 - t) * np.exp(-log_s)

        return np.concatenate([x1, x2], axis=-1)


class NormalizingFlowPlanner:
    """Normalizing Flow planner for tactical plan generation.

    Uses a sequence of invertible transformations to map a simple
    base distribution (Gaussian) to complex tactical plan distributions.
    """

    def __init__(self, config: Optional[FlowConfig] = None):
        self.config = config or FlowConfig()
        self.flow_blocks: List[RealNVPBlock] = []
        self._init_flows()
        self.training_count = 0

    def _init_flows(self) -> None:
        """Initialize the flow blocks."""
        for _ in range(self.config.n_flows):
            block = RealNVPBlock(self.config.input_dim, self.config.hidden_dim)
            self.flow_blocks.append(block)

    def sample_base(self, n: int = 1) -> np.ndarray:
        """Sample from the base distribution (standard Gaussian)."""
        return np.random.randn(n, self.config.input_dim)

    def forward(self, z: np.ndarray) -> Tuple[np.ndarray, float]:
        """Transform samples from base distribution through flows.

        Args:
            z: Samples from base distribution (batch_size, input_dim)

        Returns:
            Tuple of (transformed samples, log probability)
        """
        x = z.copy()
        log_prob = 0.0

        for block in self.flow_blocks:
            x, ldj = block.forward(x)
            log_prob += ldj

        # Base log probability
        base_log_prob = -0.5 * np.sum(z ** 2, axis=-1) - 0.5 * self.config.input_dim * math.log(2 * math.pi)
        log_prob += float(base_log_prob.mean())

        return x, log_prob

    def inverse(self, x: np.ndarray) -> np.ndarray:
        """Transform data back to base distribution (inverse flow)."""
        z = x.copy()
        for block in reversed(self.flow_blocks):
            z = block.inverse(z)
        return z

    def generate(self, n_samples: int = 1) -> np.ndarray:
        """Generate tactical plans by sampling from the flow.

        Args:
            n_samples: Number of plans to generate

        Returns:
            Generated plans (n_samples, input_dim)
        """
        z = self.sample_base(n_samples)
        plans, _ = self.forward(z)
        self.training_count += 1
        return plans

    def log_probability(self, x: np.ndarray) -> float:
        """Compute log probability of a plan under the flow model."""
        z = self.inverse(x)
        _, log_prob = self.forward(z.reshape(1, -1))
        return log_prob

    def train_step(self, x: np.ndarray) -> float:
        """Single training step (simulated)."""
        z = self.inverse(x)
        _, log_prob = self.forward(z.reshape(1, -1))

        # Simulated gradient update
        noise = np.random.randn() * 0.001
        for block in self.flow_blocks:
            block.scale_net += np.random.randn(*block.scale_net.shape) * noise
            block.trans_net += np.random.randn(*block.trans_net.shape) * noise

        self.training_count += 1
        return float(-log_prob)  # Return negative log-likelihood

    def interpolate(self, x1: np.ndarray, x2: np.ndarray, steps: int = 10) -> List[np.ndarray]:
        """Interpolate between two plans in the latent space."""
        z1 = self.inverse(x1.reshape(1, -1))
        z2 = self.inverse(x2.reshape(1, -1))
        alphas = np.linspace(0, 1, steps)
        plans = []
        for alpha in alphas:
            z = (1 - alpha) * z1 + alpha * z2
            plan, _ = self.forward(z)
            plans.append(plan.flatten())
        return plans

    def get_stats(self) -> Dict[str, Any]:
        return {
            "type": "NormalizingFlowPlanner",
            "input_dim": self.config.input_dim,
            "n_flows": self.config.n_flows,
            "flow_type": self.config.flow_type,
            "training_count": self.training_count,
        }
