#!/usr/bin/env python3
"""Regression tests for ULTRONEDreamerV3 world model.

These tests guard against previously-fixed defects:

1. Decoder/predictor input-dimension mismatch
   ``mat1 and mat2 shapes cannot be multiplied (1x288 and 64x15488)``
   caused by passing ``[post, hidden]`` (stoch_dim + rnn_hidden) into
   networks sized for ``latent_dim + stoch_dim``.

2. Decoder output spatial-size mismatch with ``obs_shape`` causing a
   broadcast error inside ``F.mse_loss``.

3. Circular encoder(decoder(...)) logic in ``imagine()``: imagination now
   works entirely in latent space using the transition prior.

4. Missing done/continue prediction loss in ``update()``.

Running with warnings-as-errors is supported:

    python -m pytest tests/test_dreamer_v3.py -W error::UserWarning
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
import warnings

import torch


class TestULTRONEDreamerV3(unittest.TestCase):
    def setUp(self):
        from brain.learning.world_models.dreamer_v3 import (
            DreamerConfig,
            ULTRONEDreamerV3,
        )

        self.cfg = DreamerConfig(
            latent_dim=32,
            stoch_dim=32,
            rnn_hidden=256,
            action_dim=4,
            obs_shape=(3, 96, 96),
            device="cpu",
        )
        self.model = ULTRONEDreamerV3(self.cfg)

    def test_update_no_shape_error(self):
        """update() must execute without decoder/predictor shape errors."""
        T, B = 4, 2
        batch = {
            "observations": torch.randn(T, B, 3, 96, 96),
            "actions": torch.randn(T, B, 4),
            "rewards": torch.randn(T, B, 1),
            "dones": torch.zeros(T, B, 1),
        }
        with warnings.catch_warnings():
            warnings.simplefilter("error", UserWarning)
            losses = self.model.update(batch)
        self.assertIn("total", losses)
        self.assertTrue(torch.isfinite(losses["total"]))
        for key in ("recon", "kl", "reward", "continue"):
            self.assertIn(key, losses)
            self.assertTrue(torch.isfinite(losses[key]))

    def test_update_single_frame_returns_zero(self):
        """Sequences shorter than 2 timesteps return zero losses."""
        batch = {
            "observations": torch.randn(1, 3, 96, 96),
            "actions": torch.randn(1, 4),
            "rewards": torch.randn(1, 1),
        }
        losses = self.model.update(batch)
        self.assertEqual(float(losses["recon"]), 0.0)
        self.assertEqual(float(losses["total"]), 0.0)

    def test_imagine_rollout(self):
        """imagine() must work entirely in latent space (no circular encode)."""
        initial = self.model.get_initial_state(1, torch.device("cpu"))
        action_sequence = torch.randn(3, 1, 4)
        with warnings.catch_warnings():
            warnings.simplefilter("error", UserWarning)
            traj = self.model.imagine(initial, action_sequence)
        self.assertEqual(len(traj["states"]), 3)
        self.assertEqual(traj["rewards"].shape, (3, 1, 1))
        self.assertEqual(traj["continues"].shape, (3, 1, 1))
        # The imagined state lives in stochastic latent space of size stoch_dim.
        self.assertEqual(traj["states"][0].stochastic.shape[-1], self.cfg.stoch_dim)

    def test_decoder_output_matches_obs_shape(self):
        """Decoder output spatial dims must match obs_shape (no MSE broadcast)."""
        dec_input = torch.randn(1, self.cfg.stoch_dim + self.cfg.rnn_hidden)
        recon = self.model.decoder(dec_input)
        self.assertEqual(tuple(recon.shape[1:]), tuple(self.cfg.obs_shape))

    def test_continue_predictor_trained(self):
        """update() must produce a continue (done) loss; done alias works."""
        T, B = 4, 2
        batch = {
            "observations": torch.randn(T, B, 3, 96, 96),
            "actions": torch.randn(T, B, 4),
            "rewards": torch.randn(T, B, 1),
            "dones": torch.zeros(T, B, 1),
        }
        losses = self.model.update(batch)
        self.assertIn("continue", losses)
        self.assertTrue(torch.isfinite(losses["continue"]))
        # Backwards-compatible alias
        self.assertIs(self.model.done_predictor, self.model.continue_predictor)


if __name__ == "__main__":
    unittest.main(verbosity=2)

