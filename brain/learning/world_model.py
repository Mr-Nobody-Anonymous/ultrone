# Copyright (c) Ultrone Contributors. All rights reserved.
"""Learned predictive world model based on DreamerV3-style latent dynamics.

This module implements a latent world model that learns to predict future
states, rewards, and episode terminations from experience. The model
uses a recurrent state-space architecture with:
- Encoder: raw observations → latent states
- Deterministic RNN: latent history → stochastic latent state
- Transition prior/posterior: latent dynamics
- Reward predictor: latent state → expected reward
- Decoder: latent state → reconstructed observation

Integration
-----------
The world model can be trained alongside RL algorithms (PPO, SAC, etc.)
or used standalone for planning via imagination rollouts.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.optim import Adam

try:
    from torch.amp import GradScaler
except ImportError:
    from torch.cuda.amp import GradScaler

logger = logging.getLogger("Ultrone.Brain.Learning.WorldModel")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass
class WorldModelConfig:
    """Configuration for the learned world model."""

    # Architecture
    latent_dim: int = 32
    hidden_dim: int = 256
    num_layers: int = 2
    num_categories: int = 32  # for discrete latent (DreamerV3 uses 32)

    # Observation/action spaces (set dynamically)
    obs_shape: Tuple[int, ...] = (1,)  # placeholder; updated at init
    action_dim: int = 1

    # Training
    learning_rate: float = 3e-4
    batch_size: int = 256
    sequence_length: int = 50  # unroll length for training
    gamma: float = 0.995  # discount for return estimation
    lambda_: float = 0.95  # GAE-like lambda for value targets

    # Replay buffer
    buffer_size: int = 1_000_000
    warmup_steps: int = 5000

    # Regularization
    kl_weight: float = 1.0  # weight on KL divergence loss
    free_nats: float = 3.0  # free bits for KL
    grad_clip_norm: float = 100.0

    # Misc
    device: str = "cpu"
    seed: int = 42
    use_amp: bool = False  # automatic mixed precision


# ---------------------------------------------------------------------------
# Neural Network Components
# ---------------------------------------------------------------------------


class Encoder(nn.Module):
    """Maps raw observation to deterministic features."""

    def __init__(self, obs_shape: Tuple[int, ...], hidden_dim: int):
        super().__init__()
        input_dim = int(np.prod(obs_shape))
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ELU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ELU(),
        )
        self._hidden_dim = hidden_dim

    def forward(self, obs: torch.Tensor) -> torch.Tensor:
        x = obs.reshape(obs.size(0), -1)
        return self.net(x)


class Decoder(nn.Module):
    """Maps latent state to reconstructed observation."""

    def __init__(self, latent_dim: int, hidden_dim: int, obs_shape: Tuple[int, ...]):
        super().__init__()
        self.obs_shape = obs_shape
        self.obs_dim = int(np.prod(obs_shape))
        self.net = nn.Sequential(
            nn.Linear(latent_dim, hidden_dim),
            nn.ELU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ELU(),
            nn.Linear(hidden_dim, self.obs_dim),
        )

    def forward(self, latent: torch.Tensor) -> torch.Tensor:
        x = self.net(latent)
        return x.reshape(-1, *self.obs_shape)


class RSSM(nn.Module):
    """Recurrent State-Space Model (deterministic + stochastic state)."""

    def __init__(
        self,
        latent_dim: int,
        hidden_dim: int,
        action_dim: int,
        num_categories: int,
    ):
        super().__init__()
        self.latent_dim = latent_dim
        self.hidden_dim = hidden_dim
        self.num_categories = num_categories

        # Deterministic GRU
        self.gru = nn.GRUCell(hidden_dim + action_dim, hidden_dim)

        # Prior: p(z_t | h_t)
        self.prior_net = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.ELU(),
            nn.Linear(hidden_dim, num_categories * latent_dim),
        )

        # Posterior: q(z_t | h_t, o_t)
        self.posterior_net = nn.Sequential(
            nn.Linear(hidden_dim + hidden_dim, hidden_dim),  # h_t + encoder(o_t)
            nn.ELU(),
            nn.Linear(hidden_dim, num_categories * latent_dim),
        )

    def forward(
        self,
        prev_hidden: torch.Tensor,
        prev_action: torch.Tensor,
        obs_encoded: Optional[torch.Tensor] = None,
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Single step through the RSSM.

        Returns
        -------
        hidden : (B, H)
        prior_logits : (B, latent_dim, num_categories)
        posterior_logits : (B, latent_dim, num_categories)
        """
        # Update deterministic state
        x = torch.cat([prev_hidden, prev_action], dim=-1)
        hidden = self.gru(x, prev_hidden)

        # Prior (used at imagination time)
        prior_logits = self.prior_net(hidden).reshape(-1, self.latent_dim, self.num_categories)

        # Posterior (used during training with observations)
        if obs_encoded is not None:
            post_input = torch.cat([hidden, obs_encoded], dim=-1)
            posterior_logits = self.posterior_net(post_input).reshape(
                -1, self.latent_dim, self.num_categories
            )
        else:
            posterior_logits = prior_logits

        return hidden, prior_logits, posterior_logits

    def imagine_step(
        self, prev_hidden: torch.Tensor, prev_action: torch.Tensor
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """Imagination step: return hidden and prior logits (no observation)."""
        hidden, prior_logits, _ = self.forward(prev_hidden, prev_action)
        return hidden, prior_logits


class Actor(nn.Module):
    """Policy network: latent state → action logits."""

    def __init__(self, latent_dim: int, hidden_dim: int, action_dim: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(latent_dim, hidden_dim),
            nn.ELU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ELU(),
            nn.Linear(hidden_dim, action_dim),
        )

    def forward(self, latent: torch.Tensor) -> torch.Tensor:
        return self.net(latent)


class Critic(nn.Module):
    """Value network: latent state → state value."""

    def __init__(self, latent_dim: int, hidden_dim: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(latent_dim, hidden_dim),
            nn.ELU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ELU(),
            nn.Linear(hidden_dim, 1),
        )

    def forward(self, latent: torch.Tensor) -> torch.Tensor:
        return self.net(latent).squeeze(-1)


# ---------------------------------------------------------------------------
# Replay Buffer
# ---------------------------------------------------------------------------


@dataclass
class Transition:
    """Single step transition."""
    obs: np.ndarray
    action: np.ndarray
    reward: float
    done: bool
    next_obs: np.ndarray


class ReplayBuffer:
    """Stores trajectories for world model + actor-critic training."""

    def __init__(self, capacity: int, obs_shape: Tuple[int, ...], action_dim: int):
        self.capacity = capacity
        self.obs_shape = obs_shape
        self.action_dim = action_dim
        self.position = 0
        self.size = 0

        self.observations = np.zeros((capacity, *obs_shape), dtype=np.float32)
        self.actions = np.zeros((capacity, action_dim), dtype=np.float32)
        self.rewards = np.zeros((capacity,), dtype=np.float32)
        self.dones = np.zeros((capacity,), dtype=np.bool_)

    def push(self, obs: np.ndarray, action: np.ndarray, reward: float, done: bool) -> None:
        idx = self.position
        self.observations[idx] = obs.astype(np.float32)
        self.actions[idx] = action.astype(np.float32)
        self.rewards[idx] = reward
        self.dones[idx] = done
        self.position = (self.position + 1) % self.capacity
        self.size = min(self.size + 1, self.capacity)

    def sample(self, batch_size: int, seq_len: int) -> Optional[Dict[str, torch.Tensor]]:
        """Sample a batch of sequences for training."""
        if self.size < seq_len + 1:
            return None

        indices = np.random.randint(0, self.size - seq_len, size=batch_size)
        start = np.random.randint(0, self.size - seq_len - 1, size=batch_size)
        # Ensure valid sequences
        start = np.clip(start, 0, self.size - seq_len - 1)

        obs_batch = []
        act_batch = []
        rew_batch = []
        done_batch = []

        for s in start:
            end = s + seq_len
            obs_batch.append(self.observations[s:end])
            act_batch.append(self.actions[s:end])
            rew_batch.append(self.rewards[s:end])
            done_batch.append(self.dones[s:end])

        obs_batch = torch.tensor(np.stack(obs_batch), dtype=torch.float32)
        act_batch = torch.tensor(np.stack(act_batch), dtype=torch.float32)
        rew_batch = torch.tensor(np.stack(rew_batch), dtype=torch.float32).unsqueeze(-1)
        done_batch = torch.tensor(np.stack(done_batch), dtype=torch.bool).unsqueeze(-1)

        return {
            "observations": obs_batch,
            "actions": act_batch,
            "rewards": rew_batch,
            "dones": done_batch,
        }

    def __len__(self) -> int:
        return self.size


# ---------------------------------------------------------------------------
# Learned World Model
# ---------------------------------------------------------------------------


class LearnedWorldModel:
    """DreamerV3-style latent world model.

    Combines an RSSM (Recurrent State Space Model) with separate encoder,
    decoder, reward predictor, and value predictor. Trained on environment
    interactions to predict future states and rewards.

    Parameters
    ----------
    config : WorldModelConfig
        Model hyperparameters.
    """

    def __init__(self, config: WorldModelConfig):
        self.config = config
        torch.manual_seed(config.seed)
        self.device = torch.device(config.device)

        flat_latent = config.latent_dim * config.num_categories

        # Networks
        self.encoder = Encoder(config.obs_shape, config.hidden_dim).to(self.device)
        self.decoder = Decoder(flat_latent, config.hidden_dim, config.obs_shape).to(
            self.device
        )
        self.rssm = RSSM(
            config.latent_dim,
            config.hidden_dim,
            config.action_dim,
            config.num_categories,
        ).to(self.device)
        self.reward_model = nn.Linear(flat_latent, 1).to(self.device)
        self.value_model = nn.Linear(flat_latent, 1).to(self.device)
        self.actor = nn.Linear(flat_latent, config.action_dim).to(self.device)

        # Optimizers
        self.world_optimizer = Adam(
            list(self.encoder.parameters())
            + list(self.decoder.parameters())
            + list(self.rssm.parameters())
            + list(self.reward_model.parameters()),
            lr=config.learning_rate,
        )
        self.ac_optimizer = Adam(
            list(self.actor.parameters()) + list(self.value_model.parameters()),
            lr=config.learning_rate,
        )

        # Mixed precision
        self.scaler = GradScaler() if config.use_amp else None

        # State
        self._hidden: Optional[torch.Tensor] = None
        self._prev_latent: Optional[torch.Tensor] = None
        self._buffer: Optional[ReplayBuffer] = None
        self._total_steps = 0

        logger.info("LearnedWorldModel initialized on %s", self.device)

    def reset(self) -> None:
        """Reset the recurrent state."""
        self._hidden = None
        self._prev_latent = None

    def encode_observation(self, obs: np.ndarray) -> torch.Tensor:
        """Encode a single observation to latent space (detached)."""
        with torch.no_grad():
            obs_t = torch.tensor(obs, dtype=torch.float32, device=self.device).unsqueeze(0)
            encoded = self.encoder(obs_t)
        return encoded

    def update_buffer(
        self, obs: np.ndarray, action: np.ndarray, reward: float, done: bool
    ) -> None:
        """Push a transition to the replay buffer."""
        if self._buffer is None:
            self._buffer = ReplayBuffer(
                self.config.buffer_size,
                self.config.obs_shape,
                self.config.action_dim,
            )
        self._buffer.push(obs, action, reward, done)
        self._total_steps += 1

    def act(self, obs: np.ndarray, deterministic: bool = False) -> np.ndarray:
        """Select an action given an observation (uses learned policy)."""
        if self._hidden is None:
            self._hidden = torch.zeros(1, self.config.hidden_dim, device=self.device)

        with torch.no_grad():
            obs_t = torch.tensor(obs, dtype=torch.float32, device=self.device).unsqueeze(0)
            encoded = self.encoder(obs_t)

            # Posterior to get current latent
            _, _, post_logits = self.rssm(self._hidden, torch.zeros(1, self.config.action_dim, device=self.device), encoded)
            latent = self._sample_discrete(post_logits)

            # Policy
            action_logits = self.actor(latent)
            if self.config.action_dim > 1:
                if deterministic:
                    action = torch.argmax(action_logits, dim=-1).float()
                else:
                    action = torch.distributions.Categorical(logits=action_logits).sample().float()
            else:
                action = torch.tanh(action_logits)

            # Update hidden state
            if self.config.action_dim > 1:
                action_input = F.one_hot(
                    action.long().clamp(0, self.config.action_dim - 1),
                    num_classes=self.config.action_dim,
                ).float()
            else:
                action_input = action.reshape(action.size(0), self.config.action_dim)
            self._hidden, _, _ = self.rssm(self._hidden, action_input, encoded)
            self._prev_latent = latent

        return action.cpu().numpy().flatten()

    def train_step(self) -> Dict[str, float]:
        """Perform one training step on the world model + actor-critic.

        Returns
        -------
        losses : dict
            Dictionary of loss names to values.
        """
        if self._buffer is None or len(self._buffer) < self.config.sequence_length:
            return {}

        batch = self._buffer.sample(self.config.batch_size, self.config.sequence_length)
        if batch is None:
            return {}

        obs_seq = batch["observations"].to(self.device)  # (B, T, *obs_shape)
        act_seq = batch["actions"].to(self.device)  # (B, T, action_dim)
        rew_seq = batch["rewards"].to(self.device)  # (B, T, 1)
        done_seq = batch["dones"].to(self.device)  # (B, T, 1)

        batch_size, seq_len = obs_seq.shape[0], obs_seq.shape[1]
        flat_latent = self.config.latent_dim * self.config.num_categories

        # Flatten time for encoder
        obs_flat = obs_seq.reshape(batch_size * seq_len, *self.config.obs_shape)
        encoded = self.encoder(obs_flat).reshape(batch_size, seq_len, -1)

        # Roll out RSSM
        hidden = torch.zeros(batch_size, self.config.hidden_dim, device=self.device)
        prior_logits_seq = []
        post_logits_seq = []
        latent_seq = []

        for t in range(seq_len):
            act_t = act_seq[:, t]
            hidden, prior_logits, post_logits = self.rssm(hidden, act_t, encoded[:, t])
            prior_logits_seq.append(prior_logits)
            post_logits_seq.append(post_logits)
            latent_seq.append(self._sample_discrete(post_logits))

        latent_seq = torch.stack(latent_seq, dim=1)  # (B, T, flat_latent)
        prior_logits_seq = torch.stack(prior_logits_seq, dim=1)
        post_logits_seq = torch.stack(post_logits_seq, dim=1)

        # ---- World model losses ----
        # 1. Reconstruction loss
        recon = self.decoder(latent_seq.reshape(batch_size * seq_len, flat_latent))
        recon = recon.reshape(batch_size, seq_len, *self.config.obs_shape)
        recon_loss = F.mse_loss(recon, obs_seq.reshape_as(recon))

        # 2. Reward prediction loss
        rew_pred = self.reward_model(latent_seq.reshape(batch_size * seq_len, flat_latent)).reshape(
            batch_size, seq_len, 1
        )
        reward_loss = F.mse_loss(rew_pred, rew_seq.reshape_as(rew_pred))

        # 3. KL divergence (posterior vs prior)
        kl_loss = self._kl_divergence(post_logits_seq, prior_logits_seq)
        kl_loss = kl_loss.clamp(min=self.config.free_nats).mean()

        world_loss = recon_loss + reward_loss + self.config.kl_weight * kl_loss

        # ---- Actor-Critic losses ----
        with torch.no_grad():
            values = self.value_model(latent_seq.detach().reshape(-1, flat_latent)).reshape(
                batch_size, seq_len
            )
            returns = self._compute_returns(rew_seq.squeeze(-1), done_seq.squeeze(-1))
            advantages = returns - values.detach()
            advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)

        # Actor loss (behavior cloning on replay states)
        action_logits = self.actor(latent_seq.detach().reshape(-1, flat_latent))
        act_target = act_seq.reshape(-1, self.config.action_dim)
        if self.config.action_dim > 1:
            act_idx = torch.argmax(act_target, dim=-1)
            actor_loss = F.cross_entropy(action_logits, act_idx)
        else:
            actor_loss = F.mse_loss(torch.tanh(action_logits), act_target)

        # Critic loss
        values_pred = self.value_model(latent_seq.detach().reshape(-1, flat_latent)).reshape(
            batch_size, seq_len
        )
        critic_loss = F.mse_loss(values_pred, returns)

        ac_loss = actor_loss + 0.5 * critic_loss

        # ---- Optimization ----
        self.world_optimizer.zero_grad()
        if self.scaler:
            self.scaler.scale(world_loss).backward()
            self.scaler.unscale_(self.world_optimizer)
            nn.utils.clip_grad_norm_(
                list(self.encoder.parameters())
                + list(self.decoder.parameters())
                + list(self.rssm.parameters())
                + list(self.reward_model.parameters()),
                self.config.grad_clip_norm,
            )
            self.scaler.step(self.world_optimizer)
        else:
            world_loss.backward()
            nn.utils.clip_grad_norm_(
                list(self.encoder.parameters())
                + list(self.decoder.parameters())
                + list(self.rssm.parameters())
                + list(self.reward_model.parameters()),
                self.config.grad_clip_norm,
            )
            self.world_optimizer.step()

        self.ac_optimizer.zero_grad()
        if self.scaler:
            self.scaler.scale(ac_loss).backward()
            self.scaler.unscale_(self.ac_optimizer)
            nn.utils.clip_grad_norm_(
                list(self.actor.parameters()) + list(self.value_model.parameters()),
                self.config.grad_clip_norm,
            )
            self.scaler.step(self.ac_optimizer)
        else:
            ac_loss.backward()
            nn.utils.clip_grad_norm_(
                list(self.actor.parameters()) + list(self.value_model.parameters()),
                self.config.grad_clip_norm,
            )
            self.ac_optimizer.step()

        return {
            "world_loss": float(world_loss.item()),
            "recon_loss": float(recon_loss.item()),
            "reward_loss": float(reward_loss.item()),
            "kl_loss": float(kl_loss.item()),
            "actor_loss": float(actor_loss.item()),
            "critic_loss": float(critic_loss.item()),
        }

    def imagine_rollout(
        self, initial_obs: np.ndarray, horizon: int = 15
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Perform imagination rollouts from an initial observation.

        Parameters
        ----------
        initial_obs : np.ndarray
            Starting observation.
        horizon : int
            Number of imagination steps.

        Returns
        -------
        imagined_states : np.ndarray
            Latent states for each step.
        imagined_rewards : np.ndarray
            Predicted rewards.
        """
        self.eval()
        with torch.no_grad():
            obs_t = torch.tensor(initial_obs, dtype=torch.float32, device=self.device).unsqueeze(0)
            encoded = self.encoder(obs_t)
            hidden = torch.zeros(1, self.config.hidden_dim, device=self.device)
            _, _, post_logits = self.rssm(hidden, torch.zeros(1, self.config.action_dim, device=self.device), encoded)
            latent = self._sample_discrete(post_logits)

            imagined_latents = [latent.cpu().numpy()]
            imagined_rewards = []

            for _ in range(horizon):
                action_logits = self.actor(latent)
                if self.config.action_dim > 1:
                    action = torch.distributions.Categorical(logits=action_logits).sample()
                    action_input = F.one_hot(
                        action.long().clamp(0, self.config.action_dim - 1),
                        num_classes=self.config.action_dim,
                    ).float()
                else:
                    action = torch.tanh(action_logits)
                    action_input = action.reshape(action.size(0), self.config.action_dim)
                hidden, prior_logits = self.rssm.imagine_step(hidden, action_input)
                latent = self._sample_discrete(prior_logits)
                reward_pred = self.reward_model(latent)
                imagined_latents.append(latent.cpu().numpy())
                imagined_rewards.append(reward_pred.cpu().numpy())

        self.train()
        return np.array(imagined_latents[1:]), np.array(imagined_rewards)

    def save(self, path: str) -> None:
        """Save model state to disk."""
        import pathlib
        pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
        torch.save(
            {
                "encoder": self.encoder.state_dict(),
                "decoder": self.decoder.state_dict(),
                "rssm": self.rssm.state_dict(),
                "reward_model": self.reward_model.state_dict(),
                "value_model": self.value_model.state_dict(),
                "actor": self.actor.state_dict(),
                "world_optimizer": self.world_optimizer.state_dict(),
                "ac_optimizer": self.ac_optimizer.state_dict(),
                "config": self.config,
                "total_steps": self._total_steps,
            },
            path,
        )
        logger.info("World model saved to %s", path)

    def load(self, path: str) -> None:
        """Load model state from disk."""
        if not path.endswith(".pt") and not path.endswith(".pth"):
            path = f"{path}.pt"
        # weights_only=False is used because the checkpoint contains non-weight objects (config)
        checkpoint = torch.load(path, map_location=self.device, weights_only=False)
        self.encoder.load_state_dict(checkpoint["encoder"])
        self.decoder.load_state_dict(checkpoint["decoder"])
        self.rssm.load_state_dict(checkpoint["rssm"])
        self.reward_model.load_state_dict(checkpoint["reward_model"])
        self.value_model.load_state_dict(checkpoint["value_model"])
        self.actor.load_state_dict(checkpoint["actor"])
        self.world_optimizer.load_state_dict(checkpoint["world_optimizer"])
        self.ac_optimizer.load_state_dict(checkpoint["ac_optimizer"])
        self._total_steps = checkpoint.get("total_steps", 0)
        logger.info("World model loaded from %s", path)

    # ---- Internal helpers ----

    def _sample_discrete(self, logits: torch.Tensor) -> torch.Tensor:
        """Sample from discrete categorical distribution (straight-through).

        Parameters
        ----------
        logits : (B, latent_dim, num_categories)

        Returns
        -------
        sample : (B, latent_dim * num_categories)
            Flattened one-hot representation for downstream networks.
        """
        probs = F.softmax(logits, dim=-1)
        sample = torch.distributions.Categorical(probs=probs).sample()
        sample_onehot = F.one_hot(sample, num_classes=self.config.num_categories).float()
        # Straight-through estimator: (sample - probs) stops gradient, + probs preserves flow
        straight_through = (sample_onehot - probs).detach() + probs
        # Use reshape for safety; straight_through may be non-contiguous after detach
        return straight_through.reshape(straight_through.size(0), -1)

    def _kl_divergence(
        self, post_logits: torch.Tensor, prior_logits: torch.Tensor
    ) -> torch.Tensor:
        """KL(q || p) for discrete categorical distributions.

        Parameters
        ----------
        post_logits : (B, T, latent_dim, num_categories)
        prior_logits : (B, T, latent_dim, num_categories)

        Returns
        -------
        kl : (B, T, latent_dim)
        """
        post_probs = F.softmax(post_logits, dim=-1)
        prior_probs = F.softmax(prior_logits, dim=-1)
        kl = (post_probs * (torch.log(post_probs + 1e-8) - torch.log(prior_probs + 1e-8))).sum(
            dim=-1
        )
        return kl

    def _compute_returns(
        self, rewards: torch.Tensor, dones: torch.Tensor
    ) -> torch.Tensor:
        """Compute discounted returns."""
        batch_size, seq_len = rewards.shape
        returns = torch.zeros_like(rewards)
        last_return = torch.zeros(batch_size, device=rewards.device)
        for t in reversed(range(seq_len)):
            last_return = rewards[:, t] + self.config.gamma * last_return * (1.0 - dones[:, t].float())
            returns[:, t] = last_return
        return returns

    def train(self) -> None:
        for m in [self.encoder, self.decoder, self.rssm, self.reward_model, self.value_model, self.actor]:
            m.train()

    def eval(self) -> None:
        for m in [self.encoder, self.decoder, self.rssm, self.reward_model, self.value_model, self.actor]:
            m.eval()
