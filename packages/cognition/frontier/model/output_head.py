# Copyright (c) Ultrone Contributors. All rights reserved.
"""Output head for frontier models.

Maps hidden states to vocabulary logits. Supports tied embeddings and
temperature scaling.
"""

from __future__ import annotations

import math
from typing import Any, Dict, Optional

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F

    TORCH_AVAILABLE = True
except ImportError:  # pragma: no cover
    TORCH_AVAILABLE = False

from .model_config import ModelConfig


class OutputHead:
    """Maps hidden states to vocabulary logits.

    Parameters
    ----------
    config : ModelConfig
        Model configuration.
    embedding_weight : Optional
        The token embedding weight (for tied embeddings).
    """

    def __init__(self, config: ModelConfig, embedding_weight: Optional[Any] = None):
        self.config = config
        self.vocab_size = config.vocab_size
        self.hidden_size = config.hidden_size
        self.tie_embeddings = config.tie_word_embeddings

        # Always create pure-Python weights so we can dispatch on input type.
        import random

        rng = random.Random(hash((config.seed, "output")) & 0xFFFF)
        self.py_weight = [
            [rng.gauss(0.0, config.initializer_range) for _ in range(config.hidden_size)]
            for _ in range(config.vocab_size)
        ]
        self.py_bias = [0.0] * config.vocab_size if config.use_bias else None

        if TORCH_AVAILABLE:
            if self.tie_embeddings and embedding_weight is not None:
                self.weight = embedding_weight
            else:
                self.weight = nn.Parameter(torch.zeros(config.vocab_size, config.hidden_size))
                nn.init.normal_(self.weight, mean=0.0, std=config.initializer_range)
            self.bias = nn.Parameter(torch.zeros(config.vocab_size)) if config.use_bias else None

    def forward(self, hidden_states, temperature: float = 1.0):
        """Compute logits from hidden states.

        Parameters
        ----------
        hidden_states : tensor [batch, seq, hidden] or [num_tokens, hidden]
        temperature : float
            Temperature for logit scaling.

        Returns
        -------
        logits : tensor [batch, seq, vocab] or [num_tokens, vocab]
        """
        if TORCH_AVAILABLE and hasattr(hidden_states, "requires_grad"):
            logits = F.linear(hidden_states, self.weight, self.bias)
            if temperature != 1.0:
                logits = logits / temperature
            return logits
        # Pure-Python
        if hasattr(hidden_states[0], "__iter__") and hasattr(hidden_states[0][0], "__iter__"):
            return [self._forward_2d(b, temperature) for b in hidden_states]
        return self._forward_2d(hidden_states, temperature)

    def _forward_2d(self, x, temperature: float):
        """Forward for 2D input [num_tokens, hidden]."""
        out = []
        for vec in x:
            logits = [sum(v * w for v, w in zip(vec, col)) for col in self.py_weight]
            if self.py_bias is not None:
                logits = [l + b for l, b in zip(logits, self.py_bias)]
            if temperature != 1.0:
                logits = [l / temperature for l in logits]
            out.append(logits)
        return out

    def get_stats(self) -> Dict[str, Any]:
        """Return output head statistics."""
        return {
            "type": "OutputHead",
            "vocab_size": self.vocab_size,
            "hidden_size": self.hidden_size,
            "tie_embeddings": self.tie_embeddings,
        }

    def __call__(self, *args, **kwargs):
        return self.forward(*args, **kwargs)