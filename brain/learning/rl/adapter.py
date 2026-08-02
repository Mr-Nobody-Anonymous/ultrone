# Copyright (c) Ultrone Contributors. All rights reserved.
"""Stable-Baselines3 adapter layer for RL algorithms.

Wraps SB3 algorithm implementations behind the existing ``BaseRLAlgorithm``
interface so that all RL algorithms in this module are interchangeable
through configuration.  If SB3 is not installed, falls back to a
rule-based heuristic policy for graceful degradation.

Integration
-----------
Each concrete algorithm class (PPO, SAC, etc.) inherits from
``SB3Adapter`` and overrides ``_create_model()`` to instantiate
the correct SB3 algorithm.  Users continue to import from
``brain.learning.rl`` as before.
"""

from __future__ import annotations

import logging
import os
import pickle
import numpy as np
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union

from .base import BaseRLAlgorithm, RLConfig, RLExperience

logger = logging.getLogger("Ultrone.Brain.Learning.RL.Adapter")

# ── SB3 availability ────────────────────────────────────────────────

try:
    import stable_baselines3 as sb3
    from stable_baselines3.common.base_class import BaseAlgorithm
    from stable_baselines3.common.vec_env import DummyVecEnv, VecEnv, SubprocVecEnv
    from stable_baselines3.common.callbacks import BaseCallback, EvalCallback
    from stable_baselines3.common.monitor import Monitor
    import gymnasium as gym
    SB3_AVAILABLE = True
except ImportError:
    SB3_AVAILABLE = False
    sb3 = None  # type: ignore
    BaseAlgorithm = object  # type: ignore
    logger.info("stable-baselines3 not installed — RL algorithms will use fallback heuristic policies.")


# ── Helper: Create a Gymnasium wrapper for ULTRONE environments ─────

class _UltroneEnvWrapper(gym.Env):
    """Wraps an ULTRONE environment (step returns done, not terminated/truncated)
    into a Gymnasium-compatible interface."""

    def __init__(self, env_fn: Callable, observation_space: gym.Space, action_space: gym.Space):
        super().__init__()
        self._env = env_fn() if callable(env_fn) else env_fn
        self.observation_space = observation_space
        self.action_space = action_space

    def reset(self, *, seed: Optional[int] = None, options: Optional[Dict] = None) -> Tuple[np.ndarray, Dict]:
        obs = self._env.reset()
        if isinstance(obs, tuple):
            obs = obs[0]
        return np.asarray(obs, dtype=np.float32), {}

    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        result = self._env.step(action)
        if len(result) == 4:
            obs, reward, done, info = result
            truncated = False
        else:
            obs, reward, done, truncated, info = result
        return np.asarray(obs, dtype=np.float32), float(reward), bool(done), bool(truncated), info


# ── Adapter Configuration ───────────────────────────────────────────

@dataclass
class SB3AdapterConfig:
    """Configuration for SB3 adapter behaviour.

    Attributes
    ----------
    policy_type:
        SB3 policy network type (e.g. "MlpPolicy", "CnnPolicy").
    n_steps:
        Number of steps per rollout (for on-policy algorithms).
    verbose:
        SB3 verbosity level (0 = silent, 1 = info, 2 = debug).
    tensorboard_log:
        Optional TensorBoard log directory.
    policy_kwargs:
        Additional keyword arguments passed to the policy network.
    """
    policy_type: str = "MlpPolicy"
    n_steps: int = 2048
    verbose: int = 0
    tensorboard_log: Optional[str] = None
    policy_kwargs: Dict[str, Any] = field(default_factory=lambda: dict(
        net_arch=[256, 256],
    ))


# ── Heuristic Fallback Policy ───────────────────────────────────────

class _HeuristicPolicy(BaseRLAlgorithm):
    """Rule-based heuristic fallback when SB3 is unavailable.

    Implements a simple tactical policy:
    - If threat detected → engage (action=1)
    - If no threat → move (action=0)
    - If ECM active → jam (action=2)
    """

    def __init__(self, config: RLConfig):
        super().__init__(config)
        self._last_threat = 0.0

    def act(self, state: np.ndarray, deterministic: bool = False) -> np.ndarray:
        if state.ndim == 0 or state.size == 0:
            return np.array([0])
        threat_level = float(np.mean(state)) if state.size > 0 else 0.0
        self._last_threat = threat_level
        if threat_level > 0.7:
            return np.array([1])  # engage
        elif threat_level > 0.4:
            return np.array([2])  # jam
        return np.array([0])  # move

    def update(self, experience: RLExperience) -> Dict[str, float]:
        return {"heuristic_loss": 0.0}

    def save(self, path: str) -> None:
        with open(path, "wb") as f:
            pickle.dump({"last_threat": self._last_threat}, f)

    def load(self, path: str) -> None:
        if os.path.exists(path):
            with open(path, "rb") as f:
                data = pickle.load(f)
                self._last_threat = data.get("last_threat", 0.0)


# ── Abstract SB3 Adapter ────────────────────────────────────────────

class SB3Adapter(BaseRLAlgorithm):
    """Adapter that wraps a Stable-Baselines3 algorithm behind ``BaseRLAlgorithm``.

    Subclasses must implement ``_create_model()`` to return the specific
    SB3 algorithm instance.  If SB3 is not installed, falls back to
    ``_HeuristicPolicy`` automatically.

    Attributes
    ----------
    model:
        The underlying SB3 model (None if SB3 unavailable).
    _adapter_config:
        SB3-specific configuration.
    """

    def __init__(self, config: RLConfig, adapter_config: Optional[SB3AdapterConfig] = None):
        super().__init__(config)
        self._adapter_config = adapter_config or SB3AdapterConfig()
        self.model: Optional[BaseAlgorithm] = None
        self._env_wrapper: Optional[gym.Env] = None
        self._last_obs: Optional[np.ndarray] = None
        self._fallback: Optional[_HeuristicPolicy] = None

        if not SB3_AVAILABLE:
            logger.warning(
                "%s: stable-baselines3 not installed — using heuristic fallback.",
                type(self).__name__,
            )
            self._fallback = _HeuristicPolicy(config)

    # ── To be implemented by subclasses ──────────────────────────────

    @abstractmethod
    def _create_model(self, env: gym.Env) -> BaseAlgorithm:
        """Instantiate the SB3 algorithm for the given environment.

        Called once during the first ``act()`` or ``update()`` call.
        """
        ...

    # ── Public API ───────────────────────────────────────────────────

    def act(self, state: np.ndarray, deterministic: bool = False) -> np.ndarray:
        """Select an action using the SB3 model or fallback."""
        if self._fallback is not None:
            return self._fallback.act(state, deterministic)

        # Lazy init: first call creates the model
        if self.model is None:
            self._ensure_env(state)
            self.model = self._create_model(self._env_wrapper)

        self._last_obs = np.asarray(state, dtype=np.float32)
        action, _ = self.model.predict(self._last_obs, deterministic=deterministic)
        return action

    def update(self, experience: RLExperience) -> Dict[str, float]:
        """Train the SB3 model (on-policy updates happen during ``train()``).

        For off-policy algorithms, stores experience for later training.
        Returns empty losses dict since SB3 handles training internally.
        """
        if self._fallback is not None:
            return self._fallback.update(experience)

        # SB3 handles its own replay buffer; we just track steps
        self._total_steps += 1
        return {}

    def train(self) -> None:
        """Set both adapter and SB3 model to training mode."""
        super().train()
        if self.model is not None:
            self.model.policy.set_training_mode(True)

    def eval(self) -> None:
        """Set both adapter and SB3 model to evaluation mode."""
        super().eval()
        if self.model is not None:
            self.model.policy.set_training_mode(False)

    def save(self, path: str) -> None:
        """Save the trained model."""
        if self._fallback is not None:
            self._fallback.save(path)
            return
        if self.model is not None:
            logger.info("Saving model to %s", path)
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            self.model.save(path)

    def load(self, path: str) -> None:
        """Load a trained model."""
        if self._fallback is not None:
            self._fallback.load(path)
            return
        if os.path.exists(f"{path}.zip") or os.path.exists(path):
            logger.info("Loading model from %s", path)
            try:
                # Subclass-specific loading — requires knowing the algorithm type
                pass
            except Exception as e:
                logger.warning("Failed to load model from %s: %s", path, e)

    # ── Internals ────────────────────────────────────────────────────

    def _create_obs_space(self, state: np.ndarray) -> gym.Space:
        """Create an observation space matching the given state shape."""
        obs_dim = state.shape[-1] if state.ndim > 0 else 1
        return gym.spaces.Box(low=-np.inf, high=np.inf, shape=(obs_dim,), dtype=np.float32)

    def _create_action_space(self) -> gym.Space:
        """Create the action space for this algorithm.

        DQN (and other discrete-action algorithms) override this to
        return a Discrete space; continuous algorithms use a Box space.
        """
        action_dim = self._infer_action_dim()
        return gym.spaces.Box(low=-1.0, high=1.0, shape=(action_dim,), dtype=np.float32)

    def _ensure_env(self, state: np.ndarray) -> None:
        """Create a dummy environment for SB3 from the observation shape."""
        if self._env_wrapper is not None:
            return
        obs_dim = state.shape[-1] if state.ndim > 0 else 1

        # Create a minimal environment wrapper
        obs_space = self._create_obs_space(state)
        action_space = self._create_action_space()
        n_actions = self._n_discrete_actions()

        class _MinimalEnv(gym.Env):
            def __init__(self):
                super().__init__()
                self.observation_space = obs_space
                self.action_space = action_space

            def reset(self, *, seed=None, options=None):
                return np.zeros(obs_dim, dtype=np.float32), {}

            def step(self, action):
                return np.zeros(obs_dim, dtype=np.float32), 0.0, False, False, {}

            def render(self): pass

        self._env_wrapper = _MinimalEnv()

    def _n_discrete_actions(self) -> int:
        """Number of discrete actions for discrete-space algorithms."""
        return 4

    def _policy_kwargs(self) -> Dict[str, Any]:
        """Return policy kwargs appropriate for this algorithm family.

        For off-policy algorithms (SAC/TD3/DDPG), returns ``net_arch`` with
        ``pi`` and ``qf`` keys. For on-policy algorithms (PPO), returns
        ``net_arch`` with ``pi`` and ``vf`` keys.
        """
        kwargs = dict(self._adapter_config.policy_kwargs)
        # Ensure net_arch is in dict format with algorithm-specific keys
        if "net_arch" in kwargs:
            arch = kwargs["net_arch"]
            if isinstance(arch, dict):
                # Already in dict format - use as-is
                return kwargs
            elif isinstance(arch, list):
                # Convert list to dict format
                if arch and isinstance(arch[0], dict):
                    # Old format: [dict(pi=..., vf=...)] -> convert to dict
                    flat = {}
                    for item in arch:
                        if isinstance(item, dict):
                            for key, value in item.items():
                                flat[key] = value
                    kwargs["net_arch"] = flat if flat else dict(pi=[256, 256])
                else:
                    # Flat list format: [256, 256] -> wrap in dict with 'pi' key
                    kwargs["net_arch"] = dict(pi=arch)
        return kwargs

    def _infer_action_dim(self) -> int:
        """Infer action dimension from config or defaults."""
        return 1


# ═══════════════════════════════════════════════════════════════════════
#  Concrete SB3 Algorithm Adapters
# ═══════════════════════════════════════════════════════════════════════

class PPOAdapter(SB3Adapter):
    """Adapter for Stable-Baselines3 PPO."""

    def _create_model(self, env: gym.Env) -> BaseAlgorithm:
        if not SB3_AVAILABLE:
            return None  # type: ignore[return-value]
        # PPO requires dict(pi=..., vf=...) format in net_arch (SB3 v1.8.0+)
        net_arch = self._adapter_config.policy_kwargs.get("net_arch", [256, 256])
        if isinstance(net_arch, list) and not (net_arch and isinstance(net_arch[0], dict)):
            net_arch = dict(pi=net_arch, vf=net_arch)
        elif isinstance(net_arch, list) and net_arch and isinstance(net_arch[0], dict):
            net_arch_dict = {}
            for item in net_arch:
                if isinstance(item, dict):
                    for key, value in item.items():
                        net_arch_dict[key] = value
            net_arch = net_arch_dict if net_arch_dict else dict(pi=[256, 256], vf=[256, 256])
        return sb3.PPO(
            policy=self._adapter_config.policy_type,
            env=env,
            learning_rate=self.config.learning_rate,
            n_steps=self._adapter_config.n_steps,
            batch_size=self.config.batch_size,
            gamma=self.config.gamma,
            gae_lambda=0.95,
            clip_range=0.2,
            ent_coef=0.01,
            vf_coef=0.5,
            max_grad_norm=0.5,
            verbose=self._adapter_config.verbose,
            tensorboard_log=self._adapter_config.tensorboard_log,
            policy_kwargs=dict(self._adapter_config.policy_kwargs, net_arch=net_arch),
            seed=self.config.seed,
            device=self.config.device,
        )


class SACAdapter(SB3Adapter):
    """Adapter for Stable-Baselines3 SAC."""

    def _create_model(self, env: gym.Env) -> BaseAlgorithm:
        if not SB3_AVAILABLE:
            return None  # type: ignore[return-value]
        # SAC requires dict(pi=..., qf=...) format in net_arch
        net_arch = self._adapter_config.policy_kwargs.get("net_arch", [256, 256])
        if isinstance(net_arch, list) and not (net_arch and isinstance(net_arch[0], dict)):
            net_arch = dict(pi=net_arch, qf=net_arch)
        elif isinstance(net_arch, list) and net_arch and isinstance(net_arch[0], dict):
            net_arch_dict = {}
            for item in net_arch:
                if isinstance(item, dict):
                    for key, value in item.items():
                        if key == "vf":
                            net_arch_dict["qf"] = value
                        else:
                            net_arch_dict[key] = value
            net_arch = net_arch_dict if net_arch_dict else dict(pi=[256, 256], qf=[256, 256])
        return sb3.SAC(
            policy=self._adapter_config.policy_type,
            env=env,
            learning_rate=self.config.learning_rate,
            buffer_size=self.config.buffer_size,
            batch_size=self.config.batch_size,
            gamma=self.config.gamma,
            tau=self.config.tau,
            ent_coef="auto_0.2",
            verbose=self._adapter_config.verbose,
            tensorboard_log=self._adapter_config.tensorboard_log,
            policy_kwargs=dict(self._adapter_config.policy_kwargs, net_arch=net_arch),
            seed=self.config.seed,
            device=self.config.device,
        )


class TD3Adapter(SB3Adapter):
    """Adapter for Stable-Baselines3 TD3."""

    def _create_model(self, env: gym.Env) -> BaseAlgorithm:
        if not SB3_AVAILABLE:
            return None  # type: ignore[return-value]
        return sb3.TD3(
            policy=self._adapter_config.policy_type,
            env=env,
            learning_rate=self.config.learning_rate,
            buffer_size=self.config.buffer_size,
            batch_size=self.config.batch_size,
            gamma=self.config.gamma,
            tau=self.config.tau,
            policy_delay=2,
            verbose=self._adapter_config.verbose,
            tensorboard_log=self._adapter_config.tensorboard_log,
            policy_kwargs=self._policy_kwargs(),
            seed=self.config.seed,
            device=self.config.device,
        )


class DDPGAdapter(SB3Adapter):
    """Adapter for Stable-Baselines3 DDPG."""

    def _create_model(self, env: gym.Env) -> BaseAlgorithm:
        if not SB3_AVAILABLE:
            return None  # type: ignore[return-value]
        return sb3.DDPG(
            policy=self._adapter_config.policy_type,
            env=env,
            learning_rate=self.config.learning_rate,
            buffer_size=self.config.buffer_size,
            batch_size=self.config.batch_size,
            gamma=self.config.gamma,
            tau=self.config.tau,
            verbose=self._adapter_config.verbose,
            tensorboard_log=self._adapter_config.tensorboard_log,
            policy_kwargs=self._policy_kwargs(),
            seed=self.config.seed,
            device=self.config.device,
        )


class DQNAdapter(SB3Adapter):
    """Adapter for Stable-Baselines3 DQN."""

    def _create_action_space(self) -> gym.Space:
        """DQN requires a Discrete action space."""
        return gym.spaces.Discrete(self._n_discrete_actions())

    def _n_discrete_actions(self) -> int:
        """Number of discrete actions for DQN."""
        return 4

    def _create_model(self, env: gym.Env) -> BaseAlgorithm:
        if not SB3_AVAILABLE:
            return None  # type: ignore[return-value]
        # DQN requires flat list format for net_arch
        net_arch = self._adapter_config.policy_kwargs.get("net_arch", [256, 256])
        if isinstance(net_arch, dict):
            # Extract 'pi' or 'qf' key, or use first value
            net_arch = net_arch.get("pi", net_arch.get("qf", list(net_arch.values())[0] if net_arch else [256, 256]))
        elif isinstance(net_arch, list) and net_arch and isinstance(net_arch[0], dict):
            # Extract from list-of-dicts format
            flat = []
            for item in net_arch:
                if isinstance(item, dict):
                    flat.extend(item.get("pi", item.get("qf", [])))
            net_arch = flat if flat else [256, 256]
        return sb3.DQN(
            policy=self._adapter_config.policy_type,
            env=env,
            learning_rate=self.config.learning_rate,
            buffer_size=self.config.buffer_size,
            batch_size=self.config.batch_size,
            gamma=self.config.gamma,
            tau=self.config.tau,
            verbose=self._adapter_config.verbose,
            tensorboard_log=self._adapter_config.tensorboard_log,
            policy_kwargs=dict(self._adapter_config.policy_kwargs, net_arch=net_arch),
            seed=self.config.seed,
            device=self.config.device,
        )


# ═══════════════════════════════════════════════════════════════════════
#  RL Algorithm Registry (plugin-style)
# ═══════════════════════════════════════════════════════════════════════

RL_REGISTRY: Dict[str, Type[BaseRLAlgorithm]] = {
    "PPO": PPOAdapter,
    "SAC": SACAdapter,
    "TD3": TD3Adapter,
    "DDPG": DDPGAdapter,
    "DQN": DQNAdapter,
    "RainbowDQN": DQNAdapter,  # Rainbow best-effort via DQN adapter
}


def create_rl_algorithm(
    algorithm_type: str,
    config: Optional[RLConfig] = None,
    adapter_config: Optional[SB3AdapterConfig] = None,
) -> BaseRLAlgorithm:
    """Factory method: instantiate an RL algorithm by name.

    Parameters
    ----------
    algorithm_type:
        Name of the algorithm (case-insensitive, e.g. ``"PPO"``, ``"SAC"``).
    config:
        Base RL configuration.
    adapter_config:
        SB3-specific configuration.

    Returns
    -------
    BaseRLAlgorithm
        An instance of the requested algorithm.
    """
    cls = RL_REGISTRY.get(algorithm_type)
    if cls is None:
        logger.warning("Unknown algorithm '%s', falling back to PPO.", algorithm_type)
        cls = PPOAdapter

    instance = cls(config=config or RLConfig(), adapter_config=adapter_config or SB3AdapterConfig())
    logger.info("Created RL algorithm: %s", algorithm_type)
    return instance

