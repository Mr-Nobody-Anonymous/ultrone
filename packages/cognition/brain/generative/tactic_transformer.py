"""Transformer-based Generative Model for tactical sequence generation."""

from __future__ import annotations

import math
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any


@dataclass
class TransformerConfig:
    """Configuration for the Tactical Transformer."""
    vocab_size: int = 128
    d_model: int = 64
    n_heads: int = 4
    n_layers: int = 3
    d_ff: int = 256
    max_seq_len: int = 32
    dropout: float = 0.1


class TacticTransformer:
    """Transformer-based generative model for tactical sequences.

    Generates full COA sequences (action sequences) using transformer
    decoder architecture with causal masking.
    """

    def __init__(self, config: Optional[TransformerConfig] = None):
        self.config = config or TransformerConfig()
        self._init_parameters()
        self.generation_count = 0

    def _init_parameters(self) -> None:
        """Initialize transformer parameters (simulated)."""
        d = self.config.d_model
        # Token embeddings
        self._token_embed = np.random.randn(self.config.vocab_size, d) * 0.02
        # Positional encodings
        self._pos_encoding = self._create_positional_encoding()
        # Layer weights (simplified - production would use proper attention)
        self._output_proj = np.random.randn(d, self.config.vocab_size) * 0.02

    def _create_positional_encoding(self) -> np.ndarray:
        """Create sinusoidal positional encodings."""
        d = self.config.d_model
        max_len = self.config.max_seq_len
        pe = np.zeros((max_len, d))
        position = np.arange(0, max_len, dtype=np.float32)[:, np.newaxis]
        div_term = np.exp(np.arange(0, d, 2, dtype=np.float32) * -(math.log(10000.0) / d))
        pe[:, 0::2] = np.sin(position * div_term)
        pe[:, 1::2] = np.cos(position * div_term)
        return pe

    def _simulate_attention(self, x: np.ndarray, mask: Optional[np.ndarray] = None) -> np.ndarray:
        """Simulated multi-head attention (simplified for non-GPU environment)."""
        # In production, this would be proper scaled dot-product attention
        noise = np.random.randn(*x.shape) * 0.01
        if mask is not None:
            noise = noise * mask[..., np.newaxis]
        return x + noise

    def _simulate_ffn(self, x: np.ndarray) -> np.ndarray:
        """Simulated feed-forward network."""
        d = self.config.d_model
        d_ff = self.config.d_ff
        # Random projection through FFN
        w1 = np.random.randn(d, d_ff) * 0.01
        w2 = np.random.randn(d_ff, d) * 0.01
        h = np.maximum(0, x @ w1)  # ReLU
        return h @ w2

    def generate(
        self,
        prompt: Optional[np.ndarray] = None,
        max_length: int = 10,
        temperature: float = 1.0,
    ) -> np.ndarray:
        """Generate a tactical action sequence.

        Args:
            prompt: Optional initial sequence tokens (seq_len,)
            max_length: Maximum sequence length to generate
            temperature: Sampling temperature (higher = more random)

        Returns:
            Generated token sequence (seq_len,)
        """
        d = self.config.d_model
        max_len = min(max_length, self.config.max_seq_len)

        if prompt is not None:
            seq = list(prompt[:max_len])
        else:
            seq = [0]  # Start token

        while len(seq) < max_len:
            # Embed tokens
            tokens = np.array(seq[-self.config.max_seq_len:])
            x = self._token_embed[tokens] + self._pos_encoding[:len(tokens)]

            # Pass through simulated transformer layers
            for _ in range(self.config.n_layers):
                x = self._simulate_attention(x)
                x = self._simulate_ffn(x)

            # Project to vocabulary
            logits = x[-1] @ self._output_proj  # Use last token

            # Temperature sampling
            logits = logits / max(temperature, 1e-6)
            probs = np.exp(logits - np.max(logits))
            probs = probs / probs.sum()

            # Sample next token
            next_token = np.random.choice(self.config.vocab_size, p=probs)
            seq.append(int(next_token))

        self.generation_count += 1
        return np.array(seq, dtype=int)

    def encode_tactics(self, actions: List[str]) -> np.ndarray:
        """Encode a list of action names into token IDs."""
        # Simple hash-based encoding
        tokens = []
        for action in actions:
            token = hash(action) % self.config.vocab_size
            tokens.append(token)
        return np.array(tokens, dtype=int)

    def decode_tactics(self, tokens: np.ndarray) -> List[str]:
        """Decode token IDs back to action names."""
        base_actions = ["locate", "track", "engage", "assess", "jam", "strike",
                        "hack", "decoy", "pinpoint", "suppress", "move", "wait"]
        actions = []
        for token in tokens:
            idx = token % len(base_actions)
            actions.append(base_actions[idx])
        return actions

    def get_stats(self) -> Dict[str, Any]:
        return {
            "type": "TacticTransformer",
            "d_model": self.config.d_model,
            "n_layers": self.config.n_layers,
            "n_heads": self.config.n_heads,
            "max_seq_len": self.config.max_seq_len,
            "generation_count": self.generation_count,
        }
