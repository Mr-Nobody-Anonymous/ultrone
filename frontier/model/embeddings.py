# Copyright (c) Ultrone Contributors. All rights reserved.
"""Embedding layers for frontier models.

Provides token embeddings, position embeddings (learned/rotary/alibi), and
a unified embedding module. All implementations are real computations.
"""

from __future__ import annotations

import math
from typing import Optional

try:
    import torch
    import torch.nn as nn

    TORCH_AVAILABLE = True
except ImportError:  # pragma: no cover
    TORCH_AVAILABLE = False

from .model_config import ModelConfig, PositionEncodingType


class TokenEmbedding:
    """Token embedding table.

    Maps token IDs to dense vectors. Real implementation with learned
    parameters when PyTorch is available; deterministic hash-based fallback
    otherwise.
    """

    def __init__(self, vocab_size: int, hidden_size: int, initializer_range: float = 0.02):
        self.vocab_size = vocab_size
        self.hidden_size = hidden_size
        self.initializer_range = initializer_range
        if TORCH_AVAILABLE:
            self.weight = nn.Parameter(torch.zeros(vocab_size, hidden_size))
            nn.init.normal_(self.weight, mean=0.0, std=initializer_range)
        else:
            import random

            rng = random.Random(42)
            self.weight = [
                [rng.gauss(0.0, initializer_range) for _ in range(hidden_size)]
                for _ in range(vocab_size)
            ]

    def forward(self, input_ids):
        """Embed token IDs."""
        if TORCH_AVAILABLE and hasattr(input_ids, "requires_grad"):
            return self.weight[input_ids]
        if hasattr(input_ids, "__iter__"):
            return [self.weight[i] for i in input_ids]
        return self.weight[input_ids]

    def __call__(self, input_ids):
        return self.forward(input_ids)


class LearnedPositionEmbedding:
    """Learned position embeddings.

    Adds a learned vector for each absolute position.
    """

    def __init__(self, max_position: int, hidden_size: int, initializer_range: float = 0.02):
        self.max_position = max_position
        self.hidden_size = hidden_size
        if TORCH_AVAILABLE:
            self.weight = nn.Parameter(torch.zeros(max_position, hidden_size))
            nn.init.normal_(self.weight, mean=0.0, std=initializer_range)
        else:
            import random

            rng = random.Random(7)
            self.weight = [
                [rng.gauss(0.0, initializer_range) for _ in range(hidden_size)]
                for _ in range(max_position)
            ]

    def forward(self, position_ids):
        """Get position embeddings for position IDs."""
        if TORCH_AVAILABLE and hasattr(position_ids, "requires_grad"):
            return self.weight[position_ids]
        if hasattr(position_ids, "__iter__"):
            return [self.weight[p] for p in position_ids]
        return self.weight[position_ids]

    def __call__(self, position_ids):
        return self.forward(position_ids)


def compute_rotary_embeddings(
    positions, head_dim: int, theta: float = 10000.0
):
    """Compute rotary position embeddings (RoPE).

    Implements the standard frequency computation used by LLaMA/Mistral.

    Parameters
    ----------
    positions : tensor or list
        Position indices.
    head_dim : int
        Dimension of each attention head.
    theta : float
        Base frequency.

    Returns
    -------
    (cos, sin) tensors of shape (..., head_dim)
    """
    if TORCH_AVAILABLE and hasattr(positions, "requires_grad"):
        inv_freq = 1.0 / (theta ** (torch.arange(0, head_dim, 2, dtype=torch.float32) / head_dim))
        freqs = torch.outer(positions.to(torch.float32), inv_freq)
        emb = torch.cat((freqs, freqs), dim=-1)
        return torch.cos(emb), torch.sin(emb)
    # Pure-Python fallback
    import math

    inv_freq = [1.0 / (theta ** (i / head_dim)) for i in range(0, head_dim, 2)]
    cos_list, sin_list = [], []
    for pos in positions:
        emb = []
        for freq in inv_freq:
            emb.append(math.cos(pos * freq))
        for freq in inv_freq:
            emb.append(math.sin(pos * freq))
        cos_list.append(emb)
        sin_list.append(emb)
    return cos_list, sin_list


def apply_rotary_pos_emb(q, k, cos, sin):
    """Apply rotary position embeddings to query and key.

    Standard rotation: rotate the first half and second half of the
    head dimension.

    Parameters
    ----------
    q : tensor [..., seq_len, head_dim]
    k : tensor [..., seq_len, head_dim]
    cos : tensor [..., seq_len, head_dim]
    sin : tensor [..., seq_len, head_dim]

    Returns
    -------
    (q_rot, k_rot)
    """
    if TORCH_AVAILABLE and hasattr(q, "requires_grad"):
        head_dim = q.size(-1)
        half = head_dim // 2
        q1, q2 = q[..., :half], q[..., half:]
        k1, k2 = k[..., :half], k[..., half:]
        q_rot = torch.cat((q1 * cos[..., :half] - q2 * sin[..., :half],
                           q1 * sin[..., :half] + q2 * cos[..., :half]), dim=-1)
        k_rot = torch.cat((k1 * cos[..., :half] - k2 * sin[..., :half],
                           k1 * sin[..., :half] + k2 * cos[..., :half]), dim=-1)
        return q_rot, k_rot
    # Pure-Python fallback
    half = len(q[0]) // 2 if q else 0
    q_rot = []
    for i, vec in enumerate(q):
        q1 = vec[:half]
        q2 = vec[half:]
        c = cos[i][:half]
        s = sin[i][:half]
        q_rot.append([q1[j] * c[j] - q2[j] * s[j] for j in range(half)] +
                     [q1[j] * s[j] + q2[j] * c[j] for j in range(half)])
    k_rot = []
    for i, vec in enumerate(k):
        k1 = vec[:half]
        k2 = vec[half:]
        c = cos[i][:half]
        s = sin[i][:half]
        k_rot.append([k1[j] * c[j] - k2[j] * s[j] for j in range(half)] +
                     [k1[j] * s[j] + k2[j] * c[j] for j in range(half)])
    return q_rot, k_rot


class EmbeddingModule:
    """Unified embedding module combining token + position embeddings.

    Supports learned, rotary, and alibi position encodings.
    """

    def __init__(self, config: ModelConfig):
        self.config = config
        self.token_embedding = TokenEmbedding(
            config.vocab_size, config.hidden_size, config.initializer_range
        )
        self.position_embedding = None
        if config.position_encoding == PositionEncodingType.LEARNED:
            self.position_embedding = LearnedPositionEmbedding(
                config.max_position_embeddings, config.hidden_size, config.initializer_range
            )
        # For rotary embeddings, we store theta for the attention layer.
        self.rope_theta = config.rope_theta if config.position_encoding == PositionEncodingType.ROTARY else None
        self.alibi_slopes = None
        if config.position_encoding == PositionEncodingType.ALIBI:
            self.alibi_slopes = self._compute_alibi_slopes(config.num_attention_heads)

    @staticmethod
    def _compute_alibi_slopes(num_heads: int) -> list:
        """Compute ALiBi slopes for a given number of heads.

        Implements the geometric sequence: 2^(-8/h) for h in [1..num_heads].
        """
        import math

        closest_power_of_2 = 2 ** math.floor(math.log2(num_heads))
        base = 2 ** (-8.0 / closest_power_of_2)
        slopes = [base ** i for i in range(1, num_heads + 1)]
        return slopes

    def forward(self, input_ids, position_ids=None):
        """Embed input IDs.

        Returns
        -------
        hidden_states : tensor [..., seq_len, hidden_size]
        """
        # If torch is available and input is a plain list, convert to tensor
        # so the entire pipeline uses the torch path consistently.
        if TORCH_AVAILABLE and not hasattr(input_ids, "requires_grad"):
            try:
                input_ids = torch.tensor(input_ids, dtype=torch.long)
            except (ValueError, TypeError):
                pass

        embeddings = self.token_embedding(input_ids)

        if position_ids is None:
            if TORCH_AVAILABLE and hasattr(input_ids, "requires_grad"):
                position_ids = torch.arange(input_ids.size(-1), dtype=torch.long, device=input_ids.device)
            elif position_ids is None:
                position_ids = list(range(len(input_ids)))

        if self.position_embedding is not None:
            pos_embeds = self.position_embedding(position_ids)
            embeddings = embeddings + pos_embeds

        return embeddings

    def __call__(self, input_ids, position_ids=None):
        return self.forward(input_ids, position_ids)