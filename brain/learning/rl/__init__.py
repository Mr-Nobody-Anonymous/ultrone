"""Reinforcement Learning algorithms module.

Provides interchangeable RL algorithms for training agents:

- ``BaseRLAlgorithm``: Abstract interface for all RL algorithms
- ``PPO``: Proximal Policy Optimization
- ``SAC``: Soft Actor-Critic
- ``TD3``: Twin Delayed DDPG
- ``DDPG``: Deep Deterministic Policy Gradient
- ``DQN``: Deep Q-Network with extensions
- ``RainbowDQN``: Rainbow DQN (Prioritized Replay, Dueling, Noisy, C51, etc.)
- ``MARL``: Multi-Agent RL wrapper
- ``SelfPlay``: Self-play learning wrapper
- ``CurriculumLearning``: Curriculum learning scheduler
- ``QMIX``: Monotonic Value Function Factorization (MARL) 🆕
- ``MADDPG``: Multi-Agent DDPG 🆕
- ``VDN``: Value Decomposition Networks (MARL) 🆕
"""

from .base import (
    BaseRLAlgorithm, RLConfig, RLExperience, RLTrainer,
    ExperienceBuffer, RLMetrics,
)
from .ppo import PPO, PPOConfig
from .sac import SAC, SACConfig
from .td3 import TD3, TD3Config
from .ddpg import DDPG, DDPGConfig
from .dqn import DQN, DQNConfig, DoubleDQN, PrioritizedReplay
from .rainbow import RainbowDQN, RainbowConfig
from .marl import MARL, MARLConfig, CentralizedCritic, DecentralizedActor
from .self_play import SelfPlay, SelfPlayConfig
from .curriculum import CurriculumLearning, CurriculumConfig, TaskGenerator
from .qmix import QMIX, QMIXConfig
from .maddpg import MADDPG, MADDPGConfig
from .vdn import VDN, VDNConfig

__all__ = [
    "BaseRLAlgorithm", "RLConfig", "RLExperience", "RLTrainer",
    "ExperienceBuffer", "RLMetrics",
    "PPO", "PPOConfig",
    "SAC", "SACConfig",
    "TD3", "TD3Config",
    "DDPG", "DDPGConfig",
    "DQN", "DQNConfig", "DoubleDQN", "PrioritizedReplay",
    "RainbowDQN", "RainbowConfig",
    "MARL", "MARLConfig", "CentralizedCritic", "DecentralizedActor",
    "SelfPlay", "SelfPlayConfig",
    "CurriculumLearning", "CurriculumConfig", "TaskGenerator",
    "QMIX", "QMIXConfig",
    "MADDPG", "MADDPGConfig",
    "VDN", "VDNConfig",
]
