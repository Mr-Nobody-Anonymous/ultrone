# Copyright (c) Ultrone Contributors. All rights reserved.
"""Transformer model — the core architecture.

Combines embeddings, attention, MoE/dense FFN, normalization, and residual
connections into a complete transformer stack. Supports dense and MoE
configurations, KV caching, and configurable attention.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F

    TORCH_AVAILABLE = True
except ImportError:  # pragma: no cover
    TORCH_AVAILABLE = False

from .activation import get_activation
from .attention import KVCache, MultiHeadAttention
from .embeddings import EmbeddingModule
from .model_config import ModelConfig
from .moe import SparseMoE
from .normalization import get_norm

logger = logging.getLogger("Ultrone.Frontier.Model.Transformer")


class FeedForward:
    """Dense feed-forward network (used when not MoE)."""

    def __init__(self, config: ModelConfig):
        self.config = config
        self.activation = get_activation(config.activation)
        # Always create pure-Python weights so we can dispatch on input type.
        import random

        rng = random.Random(hash((config.seed, "ffn")) & 0xFFFF)
        self.w1_w = [
            [rng.gauss(0.0, config.initializer_range) for _ in range(config.hidden_size)]
            for _ in range(config.intermediate_size)
        ]
        self.w2_w = [
            [rng.gauss(0.0, config.initializer_range) for _ in range(config.intermediate_size)]
            for _ in range(config.hidden_size)
        ]
        if TORCH_AVAILABLE:
            self.w1 = nn.Linear(config.hidden_size, config.intermediate_size, bias=config.use_bias)
            self.w2 = nn.Linear(config.intermediate_size, config.hidden_size, bias=config.use_bias)

    def forward(self, x):
        """Apply feed-forward network."""
        if TORCH_AVAILABLE and hasattr(x, "requires_grad"):
            return self.w2(self.activation(self.w1(x)))
        # Pure-Python
        if hasattr(x[0], "__iter__") and hasattr(x[0][0], "__iter__"):
            # 3D: [batch, seq, hidden]
            return [self._forward_2d(b) for b in x]
        return self._forward_2d(x)

    def _forward_2d(self, x):
        """Forward for 2D input [num_tokens, hidden]."""
        hidden = []
        for vec in x:
            h = [sum(v * w for v, w in zip(vec, col)) for col in self.w1_w]
            hidden.append(self.activation(h))
        out = []
        for vec in hidden:
            o = [sum(v * w for v, w in zip(vec, col)) for col in self.w2_w]
            out.append(o)
        return out

    def __call__(self, x):
        return self.forward(x)


class TransformerBlock:
    """A single transformer block.

    Architecture:
        residual = x
        x = norm1(x)
        x = attention(x) + residual
        residual = x
        x = norm2(x)
        x = ffn(x) + residual   (dense FFN or MoE)

    Supports pre-norm (default) and post-norm configurations.
    """

    def __init__(self, config: ModelConfig, layer_idx: int = 0):
        self.config = config
        self.layer_idx = layer_idx
        self.attention = MultiHeadAttention(config, layer_idx=layer_idx)
        self.norm1 = get_norm(config.norm_type, config.hidden_size, config.layer_norm_eps)
        self.norm2 = get_norm(config.norm_type, config.hidden_size, config.layer_norm_eps)

        if config.is_moe:
            self.ffn = SparseMoE(config)
        else:
            self.ffn = FeedForward(config)

        self.dropout = config.dropout

    def forward(
        self,
        hidden_states,
        attention_mask: Optional[Any] = None,
        position_ids: Optional[Any] = None,
        past_key_value: Optional[KVCache] = None,
        use_cache: bool = False,
    ):
        """Apply the transformer block.

        Returns
        -------
        (hidden_states, aux_loss, past_key_value)
        """
        # Pre-norm
        normed = self.norm1(hidden_states)
        attn_out, past_key_value = self.attention(
            normed,
            attention_mask=attention_mask,
            position_ids=position_ids,
            past_key_value=past_key_value,
            use_cache=use_cache,
        )
        hidden_states = hidden_states + attn_out

        # Second norm
        normed = self.norm2(hidden_states)

        # FFN (dense or MoE)
        if self.config.is_moe:
            ffn_out, aux_loss = self.ffn(normed)
        else:
            ffn_out = self.ffn(normed)
            aux_loss = 0.0

        hidden_states = hidden_states + ffn_out

        return hidden_states, aux_loss, past_key_value

    def __call__(self, *args, **kwargs):
        return self.forward(*args, **kwargs)


class TransformerModel:
    """Complete transformer model.

    Architecture:
        embeddings → [block × num_layers] → final_norm → output

    Supports:
    - Dense and MoE configurations
    - KV caching for autoregressive decoding
    - Configurable attention (full, sliding-window, chunked)
    - Configurable activation and normalization
    """

    def __init__(self, config: ModelConfig):
        self.config = config
        self.embeddings = EmbeddingModule(config)
        self.blocks: List[TransformerBlock] = [
            TransformerBlock(config, layer_idx=i) for i in range(config.num_hidden_layers)
        ]
        self.final_norm = get_norm(config.norm_type, config.hidden_size, config.layer_norm_eps)

    def forward(
        self,
        input_ids,
        attention_mask: Optional[Any] = None,
        position_ids: Optional[Any] = None,
        past_key_values: Optional[List[KVCache]] = None,
        use_cache: bool = False,
    ):
        """Forward pass through the transformer.

        Parameters
        ----------
        input_ids : tensor [batch, seq]
        attention_mask : Optional tensor
        position_ids : Optional tensor [seq]
        past_key_values : Optional List[KVCache]
        use_cache : bool

        Returns
        -------
        (hidden_states, aux_loss, past_key_values)
        """
        # Normalize input to [batch, seq]. If a flat list/tensor is given,
        # treat it as a single sequence (batch=1).
        if TORCH_AVAILABLE and not hasattr(input_ids, "requires_grad"):
            try:
                input_ids = torch.tensor(input_ids, dtype=torch.long)
            except (ValueError, TypeError):
                pass
        if TORCH_AVAILABLE and hasattr(input_ids, "requires_grad") and input_ids.dim() == 1:
            input_ids = input_ids.unsqueeze(0)

        hidden_states = self.embeddings(input_ids, position_ids)

        if past_key_values is None:
            past_key_values = [None] * self.config.num_hidden_layers

        total_aux_loss = 0.0
        new_past_key_values: List[Optional[KVCache]] = []

        for i, block in enumerate(self.blocks):
            hidden_states, aux_loss, new_cache = block(
                hidden_states,
                attention_mask=attention_mask,
                position_ids=position_ids,
                past_key_value=past_key_values[i],
                use_cache=use_cache,
            )
            total_aux_loss += aux_loss
            new_past_key_values.append(new_cache)

        hidden_states = self.final_norm(hidden_states)

        return hidden_states, total_aux_loss, new_past_key_values

    def get_num_parameters(self) -> int:
        """Count total parameters."""
        try:
            if TORCH_AVAILABLE:
                # Use the pure-Python estimate to avoid requiring parameters()
                # on every sub-module.
                pass
        except Exception:
            pass
        total = 0
        # Embeddings
        total += self.config.vocab_size * self.config.hidden_size
        # Per block
        per_block = 0
        per_block += 4 * self.config.hidden_size * self.config.hidden_size  # attention projections
        if self.config.is_moe:
            per_block += self.config.num_experts * 2 * self.config.hidden_size * self.config.intermediate_size
        else:
            per_block += 2 * self.config.hidden_size * self.config.intermediate_size
        total += per_block * self.config.num_hidden_layers
        return total

    def parameters(self):
        """Yield parameters (for PyTorch compatibility)."""
        if TORCH_AVAILABLE:
            for block in self.blocks:
                # Yield from the block's sub-modules that have parameters()
                for attr in ("attention", "ffn"):
                    mod = getattr(block, attr, None)
                    if mod is not None and hasattr(mod, "parameters"):
                        if isinstance(mod, SparseMoE):
                            for expert in mod.experts:
                                if hasattr(expert, "parameters"):
                                    yield from expert.parameters()
                        else:
                            try:
                                yield from mod.parameters()
                            except (AttributeError, TypeError):
                                pass
            # Embeddings
            emb = self.embeddings.token_embedding
            if hasattr(emb, "parameters"):
                yield from emb.parameters()

    def get_stats(self) -> Dict[str, Any]:
        """Return model statistics."""
        return {
            "type": "TransformerModel",
            "num_layers": self.config.num_hidden_layers,
            "hidden_size": self.config.hidden_size,
            "num_heads": self.config.num_attention_heads,
            "is_moe": self.config.is_moe,
            "num_experts": self.config.num_experts,
            "num_parameters": self.get_num_parameters(),
            "attention_type": self.config.attention_type.value,
        }

    def __call__(self, *args, **kwargs):
        return self.forward(*args, **kwargs)