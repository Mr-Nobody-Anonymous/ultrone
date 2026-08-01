"""Diffusion-based Plan Generation - generates tactical COAs via denoising diffusion."""

from __future__ import annotations

import math
import random
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Callable, Any


@dataclass
class DiffusionConfig:
    """Configuration for the diffusion planner."""
    num_timesteps: int = 100
    beta_start: float = 1e-4
    beta_end: float = 0.02
    plan_dim: int = 64
    schedule: str = "cosine"  # "linear" or "cosine"


class DiffusionPlanner:
    """Generates tactical plans using denoising diffusion probabilistic models.

    The diffusion process gradually adds noise to a tactical plan,
    then learns to reverse this process to generate novel plans.
    """

    def __init__(self, config: Optional[DiffusionConfig] = None):
        self.config = config or DiffusionConfig()
        self._setup_noise_schedule()
        self.generation_count = 0

    def _setup_noise_schedule(self) -> None:
        """Setup beta and alpha schedules for diffusion."""
        T = self.config.num_timesteps

        if self.config.schedule == "cosine":
            steps = np.arange(T + 1, dtype=np.float64)
            f_t = np.cos((steps / T + 0.008) / 1.008 * np.pi / 2) ** 2
            alphas = np.clip(f_t[1:] / f_t[:-1], 0.0, 1.0)
            self.betas = np.clip(1.0 - alphas, self.config.beta_start, self.config.beta_end)
        else:
            self.betas = np.linspace(self.config.beta_start, self.config.beta_end, T)

        self.alphas = 1.0 - self.betas
        self.alphas_cumprod = np.cumprod(self.alphas)
        self.sqrt_alphas_cumprod = np.sqrt(self.alphas_cumprod)
        self.sqrt_one_minus_alphas_cumprod = np.sqrt(1.0 - self.alphas_cumprod)

    def q_sample(self, plan: np.ndarray, t: int, noise: Optional[np.ndarray] = None) -> np.ndarray:
        """Forward diffusion: add noise to a plan at timestep t."""
        if noise is None:
            noise = np.random.randn(*plan.shape)

        sqrt_alpha = self.sqrt_alphas_cumprod[t]
        sqrt_one_minus = self.sqrt_one_minus_alphas_cumprod[t]

        return sqrt_alpha * plan + sqrt_one_minus * noise

    def generate_plan(
        self,
        noise: Optional[np.ndarray] = None,
        guidance_fn: Optional[Callable[[np.ndarray, int], np.ndarray]] = None,
        num_steps: Optional[int] = None,
    ) -> np.ndarray:
        """Generate a tactical plan by denoising from random noise.

        Args:
            noise: Initial noise vector (plan_dim,)
            guidance_fn: Optional function that modifies the denoising direction
            num_steps: Number of denoising steps (default: config.num_timesteps)

        Returns:
            Generated plan vector of shape (plan_dim,)
        """
        T = num_steps or self.config.num_timesteps
        dim = self.config.plan_dim

        if noise is not None:
            x = noise.copy()
        else:
            x = np.random.randn(dim)

        # Denoising loop
        for t in reversed(range(T)):
            t_batch = np.full(1, t, dtype=int)
            beta = self.betas[t]
            alpha = self.alphas[t]
            alpha_cumprod = self.alphas_cumprod[t]

            # Predict noise (simulated - in production this would be a neural network)
            if guidance_fn is not None:
                noise_pred = guidance_fn(x, t)
            else:
                # Simple simulated denoising
                noise_pred = self._simulate_noise_prediction(x, t, T)

            # Denoise step
            if t > 0:
                z = np.random.randn(dim)
                coeff = math.sqrt((1.0 - alpha_cumprod) / alpha)
                x = (1.0 / math.sqrt(alpha)) * (x - coeff * noise_pred) + math.sqrt(beta) * z
            else:
                x = (1.0 / math.sqrt(alpha)) * (x - math.sqrt(1.0 - alpha) * noise_pred)

        self.generation_count += 1
        return x

    def _simulate_noise_prediction(self, x: np.ndarray, t: int, T: int) -> np.ndarray:
        """Simulated noise prediction network.

        In production, this would be a U-Net or transformer trained
        to predict the noise added to the latent plan representation.
        """
        # Simple heuristic: noise decreases as we get closer to t=0
        noise_scale = 0.1 + 0.9 * (t / T)
        return np.random.randn(*x.shape) * noise_scale

    def encode_plan(self, plan: np.ndarray) -> np.ndarray:
        """Encode a tactical plan into the latent space."""
        if plan.ndim == 1:
            plan = plan.reshape(1, -1)
        # Simple encoding - in production would use a trained encoder
        target_dim = self.config.plan_dim
        if plan.shape[-1] != target_dim:
            if plan.shape[-1] > target_dim:
                plan = plan[:, :target_dim]
            else:
                plan = np.pad(plan, ((0, 0), (0, target_dim - plan.shape[-1])))
        return plan

    def decode_plan(self, latent: np.ndarray) -> np.ndarray:
        """Decode a latent vector back to a tactical plan."""
        return latent  # In production, would use a trained decoder

    def interpolate_plans(self, plan_a: np.ndarray, plan_b: np.ndarray, alpha: float = 0.5) -> np.ndarray:
        """Interpolate between two plans in latent space via diffusion."""
        latent_a = self.encode_plan(plan_a)
        latent_b = self.encode_plan(plan_b)

        # Noisy interpolation
        t = int(self.config.num_timesteps * (1.0 - alpha))
        noise = np.random.randn(*latent_a.shape)

        x_t = self.q_sample(latent_a, t, noise)
        plan = self.generate_plan(noise=x_t, num_steps=t)

        return self.decode_plan(plan)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "type": "DiffusionPlanner",
            "num_timesteps": self.config.num_timesteps,
            "plan_dim": self.config.plan_dim,
            "schedule": self.config.schedule,
            "generation_count": self.generation_count,
        }
