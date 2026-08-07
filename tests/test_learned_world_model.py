#!/usr/bin/env python3
"""Tests for LearnedWorldModel (DreamerV3-style latent dynamics)."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
import numpy as np
import torch

from brain.learning.world_model import (
    WorldModelConfig,
    LearnedWorldModel,
    ReplayBuffer,
    Encoder,
    Decoder,
    RSSM,
    Actor,
    Critic,
)


class TestWorldModelConfig(unittest.TestCase):
    def test_defaults(self):
        cfg = WorldModelConfig()
        self.assertEqual(cfg.latent_dim, 32)
        self.assertEqual(cfg.hidden_dim, 256)
        self.assertEqual(cfg.num_categories, 32)
        self.assertEqual(cfg.action_dim, 1)
        self.assertEqual(cfg.device, "cpu")

    def test_custom_values(self):
        cfg = WorldModelConfig(
            latent_dim=64,
            hidden_dim=128,
            num_categories=16,
            action_dim=4,
            device="cpu",
        )
        self.assertEqual(cfg.latent_dim, 64)
        self.assertEqual(cfg.hidden_dim, 128)
        self.assertEqual(cfg.num_categories, 16)
        self.assertEqual(cfg.action_dim, 4)


class TestReplayBuffer(unittest.TestCase):
    def test_push_and_len(self):
        buf = ReplayBuffer(capacity=100, obs_shape=(4,), action_dim=2)
        self.assertEqual(len(buf), 0)
        buf.push(np.zeros(4), np.zeros(2), reward=1.0, done=False)
        self.assertEqual(len(buf), 1)

    def test_circular_overflow(self):
        buf = ReplayBuffer(capacity=3, obs_shape=(2,), action_dim=1)
        for i in range(5):
            buf.push(np.ones(2) * i, np.zeros(1), float(i), False)
        self.assertEqual(len(buf), 3)
        # Oldest transitions should be overwritten
        batch = buf.sample(batch_size=1, seq_len=1)
        self.assertIsNotNone(batch)
        self.assertEqual(batch["observations"].shape[0], 1)
        self.assertEqual(batch["observations"].shape[1], 1)
        self.assertEqual(batch["observations"].shape[2], 2)

    def test_sample_returns_tensors(self):
        buf = ReplayBuffer(capacity=100, obs_shape=(3,), action_dim=2)
        for _ in range(50):
            buf.push(np.random.randn(3), np.random.randn(2), 0.0, False)
        batch = buf.sample(batch_size=8, seq_len=10)
        self.assertIsNotNone(batch)
        self.assertIsInstance(batch["observations"], torch.Tensor)
        self.assertEqual(batch["observations"].shape, (8, 10, 3))
        self.assertEqual(batch["actions"].shape, (8, 10, 2))
        self.assertEqual(batch["rewards"].shape, (8, 10, 1))
        self.assertEqual(batch["dones"].shape, (8, 10, 1))

    def test_sample_insufficient_data(self):
        buf = ReplayBuffer(capacity=100, obs_shape=(2,), action_dim=1)
        buf.push(np.zeros(2), np.zeros(1), 0.0, False)
        batch = buf.sample(batch_size=1, seq_len=10)
        self.assertIsNone(batch)


class TestEncoderDecoder(unittest.TestCase):
    def test_encoder_forward(self):
        enc = Encoder(obs_shape=(4,), hidden_dim=64)
        obs = torch.randn(8, 4)
        out = enc(obs)
        self.assertEqual(out.shape, (8, 64))

    def test_decoder_forward(self):
        dec = Decoder(latent_dim=32, hidden_dim=64, obs_shape=(4,))
        latent = torch.randn(8, 32)
        out = dec(latent)
        self.assertEqual(out.shape, (8, 4))


class TestRSSM(unittest.TestCase):
    def test_rssm_step_with_obs(self):
        rssm = RSSM(latent_dim=8, hidden_dim=64, action_dim=4, num_categories=16)
        hidden = torch.zeros(2, 64)
        action = torch.zeros(2, 4)
        obs_enc = torch.randn(2, 64)
        h, prior, post = rssm(hidden, action, obs_enc)
        self.assertEqual(h.shape, (2, 64))
        self.assertEqual(prior.shape, (2, 8, 16))
        self.assertEqual(post.shape, (2, 8, 16))

    def test_rssm_imagine_step(self):
        rssm = RSSM(latent_dim=8, hidden_dim=64, action_dim=4, num_categories=16)
        hidden = torch.zeros(2, 64)
        action = torch.zeros(2, 4)
        h, prior = rssm.imagine_step(hidden, action)
        self.assertEqual(h.shape, (2, 64))
        self.assertEqual(prior.shape, (2, 8, 16))


class TestActorCritic(unittest.TestCase):
    def test_actor(self):
        actor = Actor(latent_dim=32, hidden_dim=64, action_dim=5)
        latent = torch.randn(8, 32)
        logits = actor(latent)
        self.assertEqual(logits.shape, (8, 5))

    def test_critic(self):
        critic = Critic(latent_dim=32, hidden_dim=64)
        latent = torch.randn(8, 32)
        values = critic(latent)
        self.assertEqual(values.shape, (8,))


class TestLearnedWorldModel(unittest.TestCase):
    def setUp(self):
        self.cfg = WorldModelConfig(
            obs_shape=(4,),
            action_dim=3,
            latent_dim=16,
            hidden_dim=64,
            num_categories=8,
            buffer_size=500,
            warmup_steps=10,
            device="cpu",
        )
        self.wm = LearnedWorldModel(self.cfg)

    def test_initialization(self):
        self.assertIsNotNone(self.wm.encoder)
        self.assertIsNotNone(self.wm.decoder)
        self.assertIsNotNone(self.wm.rssm)
        self.assertIsNotNone(self.wm.reward_model)
        self.assertIsNotNone(self.wm.value_model)
        self.assertIsNotNone(self.wm.actor)

    def test_reset(self):
        self.wm._hidden = torch.ones(1, 64)
        self.wm.reset()
        self.assertIsNone(self.wm._hidden)

    def test_encode_observation(self):
        obs = np.random.randn(4).astype(np.float32)
        encoded = self.wm.encode_observation(obs)
        self.assertEqual(encoded.shape, (1, 64))

    def test_update_buffer(self):
        obs = np.random.randn(4).astype(np.float32)
        action = np.random.randn(3).astype(np.float32)
        self.wm.update_buffer(obs, action, reward=1.0, done=False)
        self.assertEqual(len(self.wm._buffer), 1)

    def test_act_returns_numpy(self):
        obs = np.random.randn(4).astype(np.float32)
        action = self.wm.act(obs, deterministic=True)
        self.assertIsInstance(action, np.ndarray)
        # action is flattened, so it should be a scalar array or shape (1,)
        self.assertTrue(action.shape == () or action.shape == (1,))

    def test_train_step_insufficient_data(self):
        # No data in buffer
        losses = self.wm.train_step()
        self.assertEqual(losses, {})

        # Fill buffer below sequence length
        for _ in range(5):
            obs = np.random.randn(4).astype(np.float32)
            action = np.random.randn(3).astype(np.float32)
            self.wm.update_buffer(obs, action, 0.0, False)
        losses = self.wm.train_step()
        self.assertEqual(losses, {})

    def test_train_step_with_data(self):
        # Fill buffer above warmup and sequence length
        for _ in range(200):
            obs = np.random.randn(4).astype(np.float32)
            action = np.random.randn(3).astype(np.float32)
            done = np.random.rand() < 0.1
            self.wm.update_buffer(obs, action, float(np.random.randn()), done)
        losses = self.wm.train_step()
        self.assertIsInstance(losses, dict)
        self.assertTrue(len(losses) > 0)
        for key in ["world_loss", "recon_loss", "reward_loss", "kl_loss", "actor_loss", "critic_loss"]:
            self.assertIn(key, losses)
            self.assertIsInstance(losses[key], float)

    def test_imagine_rollout(self):
        initial_obs = np.random.randn(4).astype(np.float32)
        latents, rewards = self.wm.imagine_rollout(initial_obs, horizon=5)
        self.assertEqual(latents.shape[0], 5)
        self.assertEqual(rewards.shape[0], 5)

    def test_save_and_load(self):
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".pt", delete=False) as f:
            path = f.name
        try:
            self.wm.save(path)
            self.assertTrue(os.path.exists(path))
            self.wm.load(path)
        finally:
            os.unlink(path)

    def test_train_eval_mode(self):
        self.wm.train()
        # Should not raise
        self.wm.eval()
        self.wm.train()


if __name__ == "__main__":
    unittest.main(verbosity=2)
