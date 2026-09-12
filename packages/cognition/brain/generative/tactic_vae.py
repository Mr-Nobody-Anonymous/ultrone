"""Variational Autoencoder for Tactics - learns latent tactical space for novel COA generation."""

from __future__ import annotations

import math
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any


@dataclass
class VAEConfig:
    """Configuration for the Tactical VAE."""
    input_dim: int = 64
    latent_dim: int = 16
    hidden_dim: int = 128
    beta: float = 1.0  # Beta-VAE weighting for disentanglement
    learning_rate: float = 1e-3


class TacticVAE:
    """Variational Autoencoder for tactical plan generation.

    Encodes tactical plans into a latent space, then decodes
    to generate novel plans with controlled variations.
    """

    def __init__(self, config: Optional[VAEConfig] = None):
        self.config = config or VAEConfig()
        # Simulated encoder/decoder weights
        self._encoder_weights = np.random.randn(self.config.input_dim, self.config.hidden_dim) * 0.01
        self._encoder_bias = np.zeros(self.config.hidden_dim)
        self._mean_weights = np.random.randn(self.config.hidden_dim, self.config.latent_dim) * 0.01
        self._logvar_weights = np.random.randn(self.config.hidden_dim, self.config.latent_dim) * 0.01
        self._decoder_weights = np.random.randn(self.config.latent_dim, self.config.input_dim) * 0.01
        self._decoder_bias = np.zeros(self.config.input_dim)
        self.training_count = 0

    def encode(self, x: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Encode input to latent distribution parameters (mu, logvar)."""
        h = np.tanh(x @ self._encoder_weights + self._encoder_bias)
        mu = h @ self._mean_weights
        logvar = h @ self._logvar_weights
        return mu, logvar

    def reparameterize(self, mu: np.ndarray, logvar: np.ndarray) -> np.ndarray:
        """Reparameterization trick: z = mu + sigma * epsilon."""
        std = np.exp(0.5 * logvar)
        eps = np.random.randn(*mu.shape)
        return mu + eps * std

    def decode(self, z: np.ndarray) -> np.ndarray:
        """Decode latent vector back to plan space."""
        return np.tanh(z @ self._decoder_weights + self._decoder_bias)

    def forward(self, x: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Full forward pass: encode, reparameterize, decode."""
        mu, logvar = self.encode(x)
        z = self.reparameterize(mu, logvar)
        x_recon = self.decode(z)
        return x_recon, mu, logvar, z

    def compute_loss(self, x: np.ndarray, x_recon: np.ndarray, mu: np.ndarray, logvar: np.ndarray) -> float:
        """Compute VAE loss: reconstruction + KL divergence."""
        recon_loss = np.mean((x - x_recon) ** 2)
        kl_loss = -0.5 * np.mean(1 + logvar - mu ** 2 - np.exp(logvar))
        return recon_loss + self.config.beta * kl_loss

    def train_step(self, x: np.ndarray) -> float:
        """Single training step (simulated gradient update)."""
        x_recon, mu, logvar, _ = self.forward(x)
        loss = self.compute_loss(x, x_recon, mu, logvar)

        # Simulated gradient update (simplified)
        grad_scale = self.config.learning_rate * (1.0 - math.exp(-loss))
        noise = np.random.randn(*self._decoder_weights.shape) * grad_scale * 0.001
        self._decoder_weights += noise
        self._decoder_bias += np.random.randn(*self._decoder_bias.shape) * grad_scale * 0.001

        self.training_count += 1
        return float(loss)

    def generate(self, z: Optional[np.ndarray] = None) -> np.ndarray:
        """Generate a tactical plan from latent vector.

        Args:
            z: Latent vector (latent_dim,). If None, samples from prior.

        Returns:
            Generated plan vector (input_dim,)
        """
        if z is None:
            z = np.random.randn(self.config.latent_dim)
        return self.decode(z)

    def interpolate(self, z1: np.ndarray, z2: np.ndarray, steps: int = 10) -> List[np.ndarray]:
        """Interpolate between two latent vectors."""
        alphas = np.linspace(0, 1, steps)
        plans = []
        for alpha in alphas:
            z = (1 - alpha) * z1 + alpha * z2
            plans.append(self.decode(z))
        return plans

    def encode_plan(self, plan: np.ndarray) -> np.ndarray:
        """Encode a tactical plan to latent vector."""
        mu, logvar = self.encode(plan.reshape(1, -1))
        return self.reparameterize(mu, logvar).flatten()

    def get_stats(self) -> Dict[str, Any]:
        return {
            "type": "TacticVAE",
            "input_dim": self.config.input_dim,
            "latent_dim": self.config.latent_dim,
            "beta": self.config.beta,
            "training_count": self.training_count,
        }
