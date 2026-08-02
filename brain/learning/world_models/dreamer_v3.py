# Copyright (c) Ultrone Contributors. All rights reserved.
"""DreamerV3-style world model implementation for ULTRONE.

This module implements a latent world model based on DreamerV3 (Hafner et al., 2023)
adapted for military simulation. The model learns to predict future states, rewards,
and episode terminations from experience, enabling imagination-based planning.

Architecture (Recurrent State-Space Model, RSSM)
-----------------------------------------------
- ``GridEncoder``: observation -> embedding
- ``TransitionModel``: p(s_t | s_{t-1}, a_{t-1})  (prior, used during imagination)
- ``RepresentationModel``: q(s_t | h_t, o_t)      (posterior, only during training)
- ``GridDecoder``: latent -> reconstructed observation
- Reward + continue (1 - done) predictors on the latent feature
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.distributions import Normal, kl_divergence

logger = logging.getLogger("Ultrone.Brain.Learning.WorldModels.DreamerV3")


@dataclass
class DreamerConfig:
    """Configuration for DreamerV3 world model."""
    latent_dim: int = 32
    stoch_dim: int = 32
    discrete_classes: int = 32  # DreamerV3 uses discrete representations
    rnn_hidden: int = 256
    action_dim: int = 1
    obs_shape: Tuple[int, ...] = (1, 64, 64)
    recon_coef: float = 1.0
    kl_coef: float = 0.5
    reward_coef: float = 1.0
    continue_coef: float = 1.0
    free_nats: float = 1.0  # Prevents KL from going to zero
    learning_rate: float = 3e-4
    grad_clip: float = 100.0
    device: str = "cpu"


class GridEncoder(nn.Module):
    """Encoder for grid-based battlefield observations with dynamic sizing."""

    def __init__(self, input_channels: int, latent_dim: int, input_size: int = 64):
        super().__init__()
        # Calculate output size dynamically
        self.conv = nn.Sequential(
            nn.Conv2d(input_channels, 32, kernel_size=4, stride=2, padding=1),
            nn.ELU(),
            nn.Conv2d(32, 64, kernel_size=4, stride=2, padding=1),
            nn.ELU(),
            nn.Conv2d(64, 128, kernel_size=4, stride=2, padding=1),
            nn.ELU(),
            nn.Conv2d(128, 256, kernel_size=4, stride=2, padding=1),
            nn.ELU(),
        )
        # Calculate flattened size
        with torch.no_grad():
            dummy = torch.zeros(1, input_channels, input_size, input_size)
            conv_out = self.conv(dummy)
            self.flat_dim = conv_out.numel() // conv_out.size(0)

        self.fc = nn.Linear(self.flat_dim, latent_dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.dim() == 2:  # (H, W) single grayscale frame -> (1, 1, H, W)
            x = x.unsqueeze(0).unsqueeze(1)
        elif x.dim() == 3:  # (C, H, W) single frame -> (1, C, H, W)
            x = x.unsqueeze(0)
        x = self.conv(x)
        x = x.reshape(x.size(0), -1)
        return self.fc(x)


class GridDecoder(nn.Module):
    """Decoder for reconstructing grid-based observations with dynamic sizing."""

    def __init__(self, latent_dim: int, output_channels: int, output_size: int = 64):
        super().__init__()
        self.output_size = output_size

        # Calculate the size after convolutions (reverse of encoder)
        self.conv_out_size = output_size // 16  # 4 stride-2 convolutions

        self.fc = nn.Linear(latent_dim, 256 * self.conv_out_size * self.conv_out_size)
        self.deconv = nn.Sequential(
            nn.ConvTranspose2d(256, 128, kernel_size=4, stride=2, padding=1),
            nn.ELU(),
            nn.ConvTranspose2d(128, 64, kernel_size=4, stride=2, padding=1),
            nn.ELU(),
            nn.ConvTranspose2d(64, 32, kernel_size=4, stride=2, padding=1),
            nn.ELU(),
            nn.ConvTranspose2d(32, output_channels, kernel_size=4, stride=2, padding=1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.fc(x)
        x = x.reshape(-1, 256, self.conv_out_size, self.conv_out_size)
        x = self.deconv(x)
        # Ensure output matches expected size
        if x.size(-1) != self.output_size:
            x = F.interpolate(x, size=self.output_size, mode='bilinear', align_corners=False)
        return x


class RSSMState:
    """Recurrent State-Space Model state container."""

    def __init__(
        self,
        deterministic: torch.Tensor,
        stochastic: torch.Tensor,
    ):
        self.deterministic = deterministic
        self.stochastic = stochastic

    @property
    def flat(self) -> torch.Tensor:
        return torch.cat([self.deterministic, self.stochastic], dim=-1)

    def __repr__(self) -> str:
        return f"RSSMState(det={self.deterministic.shape}, stoch={self.stochastic.shape})"


class TransitionModel(nn.Module):
    """RSSM Transition model: p(s_t | s_{t-1}, a_{t-1})"""

    def __init__(self, stoch_dim: int, action_dim: int, rnn_hidden: int):
        super().__init__()
        self.rnn_cell = nn.GRUCell(
            input_size=stoch_dim + action_dim,
            hidden_size=rnn_hidden
        )
        self.prior_net = nn.Linear(rnn_hidden, 2 * stoch_dim)

    def forward(
        self,
        prev_state: RSSMState,
        action: torch.Tensor
    ) -> Tuple[RSSMState, Normal]:
        """Compute prior for next state."""
        # Update deterministic state
        rnn_input = torch.cat([prev_state.stochastic, action], dim=-1)
        h = self.rnn_cell(rnn_input, prev_state.deterministic)

        # Compute prior distribution
        prior_params = self.prior_net(h)
        prior_mean, prior_std = prior_params.chunk(2, dim=-1)
        prior_std = F.softplus(prior_std) + 0.1
        prior_dist = Normal(prior_mean, prior_std)

        # Sample from prior
        prior_stoch = prior_dist.rsample()

        return RSSMState(h, prior_stoch), prior_dist


class RepresentationModel(nn.Module):
    """RSSM Representation model: q(s_t | h_t, o_t)"""

    def __init__(self, rnn_hidden: int, obs_embed_dim: int, stoch_dim: int):
        super().__init__()
        self.posterior_net = nn.Linear(rnn_hidden + obs_embed_dim, 2 * stoch_dim)

    def forward(
        self,
        deterministic: torch.Tensor,
        obs_embed: torch.Tensor
    ) -> Tuple[torch.Tensor, Normal]:
        """Compute posterior distribution."""
        post_input = torch.cat([deterministic, obs_embed], dim=-1)
        post_params = self.posterior_net(post_input)
        post_mean, post_std = post_params.chunk(2, dim=-1)
        post_std = F.softplus(post_std) + 0.1
        post_dist = Normal(post_mean, post_std)

        return post_dist.rsample(), post_dist


class ULTRONEDreamerV3(nn.Module):
    """DreamerV3 world model adapted for ULTRONE military simulation.

    Implements the Recurrent State-Space Model (RSSM) from DreamerV3 with:
    - Stochastic state representations
    - Recurrent deterministic hidden state
    - Separate transition (prior) and representation (posterior) models

    This enables:
    - Imagining future trajectories for planning
    - Learning compact latent representations of battlefield states
    - Training RL agents in imagination
    """

    def __init__(self, config: DreamerConfig):
        super().__init__()
        self.config = config

        # Infer input size from obs_shape
        input_channels = config.obs_shape[0] if len(config.obs_shape) >= 3 else 1
        input_size = config.obs_shape[-1] if len(config.obs_shape) >= 2 else config.obs_shape[0]

        # Encoder: Observation → embedding
        self.encoder = GridEncoder(
            input_channels=input_channels,
            latent_dim=config.latent_dim,
            input_size=input_size
        )

        # RSSM components
        self.transition = TransitionModel(
            stoch_dim=config.stoch_dim,
            action_dim=config.action_dim,
            rnn_hidden=config.rnn_hidden
        )

        self.representation = RepresentationModel(
            rnn_hidden=config.rnn_hidden,
            obs_embed_dim=config.latent_dim,
            stoch_dim=config.stoch_dim
        )

        # Decoder: Latent → Observation reconstruction
        self.decoder = GridDecoder(
            latent_dim=config.rnn_hidden + config.stoch_dim,
            output_channels=input_channels,
            output_size=input_size
        )

        # Reward predictor
        self.reward_predictor = nn.Sequential(
            nn.Linear(config.rnn_hidden + config.stoch_dim, 256),
            nn.ELU(),
            nn.Linear(256, 1)
        )

        # Continue (1 - done) predictor
        self.continue_predictor = nn.Sequential(
            nn.Linear(config.rnn_hidden + config.stoch_dim, 256),
            nn.ELU(),
            nn.Linear(256, 1)
        )

        # Backwards-compatible alias used by earlier audits/tests.
        self.done_predictor = self.continue_predictor

        self._init_weights()

    def _init_weights(self):
        """Initialize weights with Xavier initialization."""
        for module in self.modules():
            if isinstance(module, (nn.Linear, nn.Conv2d, nn.ConvTranspose2d)):
                nn.init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)

    def get_initial_state(self, batch_size: int, device: torch.device) -> RSSMState:
        """Get zero initial state."""
        return RSSMState(
            deterministic=torch.zeros(batch_size, self.config.rnn_hidden, device=device),
            stochastic=torch.zeros(batch_size, self.config.stoch_dim, device=device)
        )

    def imagine(
        self,
        initial_state: RSSMState,
        action_sequence: torch.Tensor,
        break_on_done: bool = True
    ) -> Dict[str, torch.Tensor]:
        """Imagine future trajectory given initial state and action sequence.

        Parameters
        ----------
        initial_state : RSSMState
            Starting RSSM state
        action_sequence : torch.Tensor
            Sequence of actions, shape (seq_len, batch_size, action_dim)
        break_on_done : bool
            Whether to stop imagining after done signal

        Returns
        -------
        Dict[str, torch.Tensor]
            Imagined trajectory with keys:
            - 'states': List of RSSMState
            - 'rewards': (seq_len, batch_size, 1)
            - 'continues': (seq_len, batch_size, 1)
            - 'actions': (seq_len, batch_size, action_dim)
        """
        seq_len = action_sequence.size(0)
        batch_size = action_sequence.size(1)

        states = []
        rewards = []
        continues = []

        state = initial_state

        for t in range(seq_len):
            action = action_sequence[t]

            # Transition: compute prior (no observation available)
            state, _ = self.transition(state, action)
            states.append(state)

            # Predict reward and continue
            feat = state.flat
            rewards.append(self.reward_predictor(feat))
            continues.append(torch.sigmoid(self.continue_predictor(feat)))

            # Optionally break on done
            if break_on_done and continues[-1].mean() < 0.1:
                # Pad remaining sequence
                for _ in range(t + 1, seq_len):
                    states.append(state)
                    rewards.append(torch.zeros_like(rewards[-1]))
                    continues.append(torch.zeros_like(continues[-1]))
                break

        return {
            'states': states,
            'rewards': torch.stack(rewards),
            'continues': torch.stack(continues),
            'actions': action_sequence
        }

    def observe(
        self,
        observations: torch.Tensor,
        actions: torch.Tensor,
        initial_state: Optional[RSSMState] = None
    ) -> Tuple[List[RSSMState], List[Normal], List[Normal]]:
        """Process a sequence of observations and actions.

        Parameters
        ----------
        observations : torch.Tensor
            Sequence of observations, shape (seq_len, batch_size, ...)
        actions : torch.Tensor
            Sequence of actions, shape (seq_len, batch_size, action_dim)
        initial_state : RSSMState, optional
            Initial state. If None, uses zero state.

        Returns
        -------
        Tuple[List[RSSMState], List[Normal], List[Normal]]
            - List of posterior states
            - List of posterior distributions
            - List of prior distributions (for KL computation)
        """
        seq_len = observations.size(0)
        batch_size = observations.size(1)
        device = observations.device

        if initial_state is None:
            initial_state = self.get_initial_state(batch_size, device)

        # Encode all observations
        obs_embeds = []
        for t in range(seq_len):
            obs_embeds.append(self.encoder(observations[t]))

        states = []
        posteriors = []
        priors = []

        state = initial_state

        for t in range(seq_len):
            # Get prior from transition
            state, prior_dist = self.transition(state, actions[t])
            priors.append(prior_dist)

            # Get posterior from observation
            post_stoch, post_dist = self.representation(
                state.deterministic,
                obs_embeds[t]
            )

            # Update state with posterior
            state = RSSMState(state.deterministic, post_stoch)
            states.append(state)
            posteriors.append(post_dist)

        return states, posteriors, priors

    def update(self, batch: Dict[str, torch.Tensor]) -> Dict[str, torch.Tensor]:
        """Update world model from batch of experiences.

        Parameters
        ----------
        batch : Dict[str, torch.Tensor]
            Must contain:
            - 'observations': (seq_len, batch_size, ...) or (batch_size, ...)
            - 'actions': (seq_len, batch_size, action_dim) or (batch_size, action_dim)
            - 'rewards': (seq_len, batch_size, 1) or (batch_size,)
            - 'dones': (seq_len, batch_size, 1) or (batch_size,)

        Returns
        -------
        Dict[str, torch.Tensor]
            Dictionary of loss values
        """
        # Reshape inputs to have sequence dimension
        observations = batch["observations"]
        actions = batch["actions"]
        rewards = batch["rewards"]
        dones = batch.get("dones", torch.zeros_like(rewards))

        # Add sequence dimension if missing
        if observations.dim() == len(self.config.obs_shape):
            observations = observations.unsqueeze(0)
        if actions.dim() == 1:
            actions = actions.unsqueeze(0).unsqueeze(-1)
        elif actions.dim() == 2:
            actions = actions.unsqueeze(0)
        if rewards.dim() == 1:
            rewards = rewards.unsqueeze(0).unsqueeze(-1)
        elif rewards.dim() == 2:
            rewards = rewards.unsqueeze(-1)
        if dones.dim() == 1:
            dones = dones.unsqueeze(0).unsqueeze(-1)
        elif dones.dim() == 2:
            dones = dones.unsqueeze(-1)

        seq_len, batch_size = observations.size(0), observations.size(1)

        if seq_len < 2:
            zero = observations.new_tensor(0.0, requires_grad=True)
            return {
                "recon": zero, "kl": zero, "reward": zero,
                "continue": zero, "total": zero
            }

        # Observe sequence
        states, posteriors, priors = self.observe(observations, actions)

        # Compute losses (skip first timestep as it has no prior)
        recon_losses = []
        kl_losses = []
        reward_losses = []
        continue_losses = []

        for t in range(1, seq_len):
            feat = states[t].flat

            # Reconstruction loss
            recon = self.decoder(feat)
            recon_target = observations[t].unsqueeze(1) if observations[t].dim() == 3 else observations[t]
            recon_losses.append(
                F.mse_loss(recon, recon_target, reduction='none')
                .sum(dim=list(range(1, recon.dim())))
                .mean()
            )

            # KL divergence (with free nats)
            kl = kl_divergence(posteriors[t], priors[t]).sum(dim=-1)
            kl = (kl - self.config.free_nats).clamp(min=0)
            kl_losses.append(kl.mean())

            # Reward prediction loss
            pred_reward = self.reward_predictor(feat)
            reward_losses.append(F.mse_loss(pred_reward, rewards[t]))

            # Continue prediction loss (binary cross entropy)
            pred_continue = self.continue_predictor(feat)
            target_continue = (1 - dones[t]).float()
            continue_losses.append(
                F.binary_cross_entropy_with_logits(pred_continue, target_continue)
            )

        # Aggregate losses
        losses = {
            "recon": torch.stack(recon_losses).mean(),
            "kl": torch.stack(kl_losses).mean(),
            "reward": torch.stack(reward_losses).mean(),
            "continue": torch.stack(continue_losses).mean(),
        }

        losses["total"] = (
            self.config.recon_coef * losses["recon"]
            + self.config.kl_coef * losses["kl"]
            + self.config.reward_coef * losses["reward"]
            + self.config.continue_coef * losses["continue"]
        )

        return losses

    def encode_observation(self, observation: torch.Tensor) -> torch.Tensor:
        """Encode a single observation to embedding."""
        return self.encoder(observation)

    def get_state_from_obs(
        self,
        observation: torch.Tensor,
        prev_state: Optional[RSSMState] = None,
        action: Optional[torch.Tensor] = None
    ) -> RSSMState:
        """Get latent state from observation."""
        batch_size = observation.size(0)
        device = observation.device

        if prev_state is None:
            prev_state = self.get_initial_state(batch_size, device)

        if action is None:
            action = torch.zeros(batch_size, self.config.action_dim, device=device)

        # Transition
        state, _ = self.transition(prev_state, action)

        # Representation
        obs_embed = self.encoder(observation)
        post_stoch, _ = self.representation(state.deterministic, obs_embed)

        return RSSMState(state.deterministic, post_stoch)


class WorldModelTrainer:
    """Utility class for training the world model."""

    def __init__(self, model: ULTRONEDreamerV3, config: DreamerConfig):
        self.model = model
        self.config = config
        self.optimizer = torch.optim.Adam(
            model.parameters(),
            lr=config.learning_rate,
            eps=1e-5
        )

    def train_step(self, batch: Dict[str, torch.Tensor]) -> Dict[str, float]:
        """Perform a single training step."""
        self.model.train()
        self.optimizer.zero_grad()

        losses = self.model.update(batch)

        losses["total"].backward()

        # Gradient clipping
        if self.config.grad_clip > 0:
            nn.utils.clip_grad_norm_(
                self.model.parameters(),
                self.config.grad_clip
            )

        self.optimizer.step()

        # Return scalar losses
        return {k: v.detach().cpu().item() for k, v in losses.items()}

    def imagine_trajectory(
        self,
        observation: torch.Tensor,
        policy_fn: Callable[[torch.Tensor], torch.Tensor],
        horizon: int = 15
    ) -> Dict[str, torch.Tensor]:
        """Imagine a trajectory using a policy function.

        Parameters
        ----------
        observation : torch.Tensor
            Starting observation
        policy_fn : callable
            Function that takes state feature and returns action
        horizon : int
            Number of steps to imagine

        Returns
        -------
        Dict[str, torch.Tensor]
            Imagined trajectory
        """
        self.model.eval()

        with torch.no_grad():
            # Get initial state
            state = self.model.get_state_from_obs(observation)

            # Generate actions from policy
            actions = []
            for _ in range(horizon):
                action = policy_fn(state.flat)
                actions.append(action)
                # Predict next state (using prior only)
                state, _ = self.model.transition(state, action)

            action_seq = torch.stack(actions, dim=0)

            # Re-imagine with collected actions for clean trajectory
            return self.model.imagine(
                self.model.get_state_from_obs(observation),
                action_seq
            )

