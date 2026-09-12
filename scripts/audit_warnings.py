#!/usr/bin/env python3
"""Audit script: exercises deep-learning code paths to surface runtime warnings.

Run with: python scripts/audit_warnings.py
"""
import sys
import os
import warnings

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import torch
import torch.nn.functional as F

warnings.simplefilter("always")

print("=" * 70)
print("WARNING AUDIT: world_model.py (LearnedWorldModel)")
print("=" * 70)


def exercise_learned_world_model():
    from brain.learning.world_model import WorldModelConfig, LearnedWorldModel

    cfg = WorldModelConfig(
        obs_shape=(4,),
        action_dim=3,
        latent_dim=16,
        hidden_dim=64,
        num_categories=8,
        buffer_size=2000,
        warmup_steps=10,
        sequence_length=10,
        device="cpu",
    )
    wm = LearnedWorldModel(cfg)

    # Fill buffer
    for _ in range(500):
        obs = np.random.randn(4).astype(np.float32)
        action = np.random.randn(3).astype(np.float32)
        done = np.random.rand() < 0.1
        wm.update_buffer(obs, action, float(np.random.randn()), done)

    # Act
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        a = wm.act(np.random.randn(4).astype(np.float32), deterministic=False)
    print(f"  act() returned {a}, warnings: {len(rec)}")
    for w in rec:
        print(f"    WARNING: {w.category.__name__}: {w.message}")

    # Train step
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        losses = wm.train_step()
    print(f"  train_step() losses keys: {list(losses.keys())}, warnings: {len(rec)}")
    for w in rec:
        print(f"    WARNING: {w.category.__name__}: {w.message}")

    # Imagine rollout
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        latents, rewards = wm.imagine_rollout(np.random.randn(4).astype(np.float32), horizon=5)
    print(f"  imagine_rollout() latents {latents.shape}, rewards {rewards.shape}, warnings: {len(rec)}")
    for w in rec:
        print(f"    WARNING: {w.category.__name__}: {w.message}")


print()
print("=" * 70)
print("WARNING AUDIT: world_models/dreamer_v3.py (ULTRONEDreamerV3)")
print("=" * 70)


def exercise_dreamer_v3():
    from brain.learning.world_models.dreamer_v3 import (
        DreamerConfig,
        ULTRONEDreamerV3,
    )

    cfg = DreamerConfig(
        latent_dim=32,
        stoch_dim=32,
        rnn_hidden=256,
        action_dim=4,
        obs_shape=(3, 96, 96),
        device="cpu",
    )
    model = ULTRONEDreamerV3(cfg)

    # Simulate a batch: (T, B, C, H, W) sequence
    T, B = 4, 2
    obs = torch.randn(T, B, 3, 96, 96)
    acts = torch.randn(T, B, 4)
    rews = torch.randn(T, B, 1)
    dones = torch.zeros(T, B, 1)

    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        try:
            losses = model.update(
                {"observations": obs, "actions": acts, "rewards": rews, "dones": dones}
            )
            print(f"  update() losses: { {k: (float(v) if torch.is_tensor(v) else v) for k, v in losses.items()} }")
        except Exception as e:
            print(f"  update() raised {type(e).__name__}: {e}")
    for w in rec:
        print(f"    WARNING: {w.category.__name__}: {w.message}")

    # Imagination: latent-space rollout using the transition prior.
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        try:
            initial = model.get_initial_state(B, torch.device("cpu"))
            actions = torch.randn(3, B, 4)
            traj = model.imagine(initial, actions)
            print(f"  imagine() states {len(traj['states'])}, "
                  f"rewards {tuple(traj['rewards'].shape)}, "
                  f"continues {tuple(traj['continues'].shape)}")
        except Exception as e:
            print(f"  imagine() raised {type(e).__name__}: {e}")
    for w in rec:
        print(f"    WARNING: {w.category.__name__}: {w.message}")


print()
print("=" * 70)
print("WARNING AUDIT: candidate tensor shapes (F.mse_loss etc.)")
print("=" * 70)


def exercise_loss_shapes():
    # Simulate critic_loss = F.mse_loss(values_pred, returns)
    # Predictions and targets MUST have identical shapes; no broadcasting.
    B, T = 32, 50
    values_pred = torch.randn(B, T)  # Critic outputs (B, T) after reshape
    returns = torch.randn(B, T)      # MC returns (B, T)
    loss = F.mse_loss(values_pred, returns)
    print(f"  values_pred {tuple(values_pred.shape)} vs returns {tuple(returns.shape)} -> mse {loss.item():.4f}")

    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        loss2 = F.mse_loss(torch.randn(B * T, 1), torch.randn(B, T).reshape(-1, 1))
    print(f"  (B*T,1) vs (B*T,1) -> {loss2.item():.4f}, warnings: {len(rec)}")


if __name__ == "__main__":
    exercise_learned_world_model()
    exercise_dreamer_v3()
    exercise_loss_shapes()
    print()
    print("Audit complete.")

