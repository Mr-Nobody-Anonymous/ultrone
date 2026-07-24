"""Stable Baselines3 adapter for production RL algorithms."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("Ultrone.Brain.Learning.ML.SB3")


@dataclass
class SB3Config:
    """Configuration for SB3 adapter."""
    algorithm: str = "PPO"  # PPO, SAC, TD3, DQN, A2C
    policy: str = "MlpPolicy"
    learning_rate: float = 3e-4
    n_steps: int = 2048
    batch_size: int = 64
    n_epochs: int = 10
    gamma: float = 0.99
    seed: int = 42


RL_REGISTRY: Dict[str, str] = {
    "PPO": "stable_baselines3.PPO",
    "SAC": "stable_baselines3.SAC",
    "TD3": "stable_baselines3.TD3",
    "DQN": "stable_baselines3.DQN",
    "A2C": "stable_baselines3.A2C",
}


class SB3Adapter:
    """Stable Baselines3 adapter for production RL training.

    Provides a unified interface for all SB3 algorithms with
    automatic model creation, training, and evaluation.

    Requires: ``pip install stable-baselines3``
    """

    def __init__(self, config: Optional[SB3Config] = None):
        self.config = config or SB3Config()
        self._model = None
        self._env = None

    def create_model(self, env: Any) -> Any:
        """Create an SB3 model for the given environment."""
        try:
            import stable_baselines3 as sb3
            algo_map = {
                "PPO": sb3.PPO,
                "SAC": sb3.SAC,
                "TD3": sb3.TD3,
                "DQN": sb3.DQN,
                "A2C": sb3.A2C,
            }
            algo_class = algo_map.get(self.config.algorithm, sb3.PPO)
            self._model = algo_class(
                self.config.policy,
                env,
                learning_rate=self.config.learning_rate,
                n_steps=self.config.n_steps,
                batch_size=self.config.batch_size,
                n_epochs=self.config.n_epochs,
                gamma=self.config.gamma,
                seed=self.config.seed,
                verbose=0,
            )
            self._env = env
            logger.info("Created SB3 %s model", self.config.algorithm)
            return self._model
        except ImportError:
            logger.warning("stable-baselines3 not installed. Install with: pip install stable-baselines3")
            return None

    def train(self, total_timesteps: int = 100_000) -> Dict[str, Any]:
        """Train the model."""
        if self._model is None:
            return {"error": "No model created"}
        self._model.learn(total_timesteps=total_timesteps)
        return {"total_timesteps": total_timesteps}

    def predict(self, observation: Any, deterministic: bool = True) -> Any:
        """Get action from model."""
        if self._model is None:
            return None
        return self._model.predict(observation, deterministic=deterministic)[0]

    def save(self, path: str) -> None:
        if self._model:
            self._model.save(path)

    def load(self, path: str, env: Any) -> None:
        try:
            import stable_baselines3 as sb3
            algo_map = {"PPO": sb3.PPO, "SAC": sb3.SAC, "TD3": sb3.TD3, "DQN": sb3.DQN, "A2C": sb3.A2C}
            algo_class = algo_map.get(self.config.algorithm, sb3.PPO)
            self._model = algo_class.load(path, env=env)
        except Exception as e:
            logger.error("Failed to load model: %s", e)

    def get_stats(self) -> Dict[str, Any]:
        return {"type": "SB3Adapter", "algorithm": self.config.algorithm, "trained": self._model is not None}
