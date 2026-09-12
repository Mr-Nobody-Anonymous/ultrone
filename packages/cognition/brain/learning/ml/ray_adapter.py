"""Ray RLlib adapter for distributed reinforcement learning."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

logger = logging.getLogger("Ultrone.Brain.Learning.ML.Ray")


@dataclass
class RayRLlibConfig:
    """Configuration for Ray RLlib adapter."""
    algorithm: str = "PPO"
    num_workers: int = 4
    num_gpus: int = 0
    lr: float = 3e-4
    train_batch_size: int = 4000


class RayRLlibAdapter:
    """Adapter for Ray RLlib distributed RL training.

    Provides access to production-scale distributed RL algorithms
    with multi-node, multi-GPU support.

    Requires: ``pip install ray[rllib]``
    """

    def __init__(self, config: Optional[RayRLlibConfig] = None):
        self.config = config or RayRLlibConfig()
        self._trainer = None

    def train(self, env_creator: Any) -> Dict[str, Any]:
        """Train an RLlib agent."""
        try:
            import ray
            from ray.rllib.algorithms.ppo import PPOConfig
            ray.init(ignore_reinit_error=True)
            config = (
                PPOConfig()
                .environment(env_creator)
                .training(lr=self.config.lr, train_batch_size=self.config.train_batch_size)
                .resources(num_gpus=self.config.num_gpus)
            )
            algo = config.build()
            result = algo.train()
            return {"episode_reward_mean": result.get("episode_reward_mean", 0)}
        except ImportError:
            logger.warning("ray[rllib] not installed.")
            return {"error": "ray not installed"}

    def get_stats(self) -> Dict[str, Any]:
        return {"type": "RayRLlibAdapter", "algorithm": self.config.algorithm}
