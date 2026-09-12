# Copyright (c) Ultrone Contributors. All rights reserved.
"""Expert module for Mixture-of-Experts.

A single expert is a feed-forward network (typically a 2-layer MLP with
activation). Tracks per-expert statistics for load balancing and routing
analysis.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F

    TORCH_AVAILABLE = True
except ImportError:  # pragma: no cover
    TORCH_AVAILABLE = False

from .activation import get_activation
from .model_config import ActivationType, ModelConfig

logger = logging.getLogger("Ultrone.Frontier.Model.Expert")


class Expert:
    """A single expert in a Mixture-of-Experts layer.

    Implements a standard 2-layer feed-forward network:
        hidden = activation(x @ W1 + b1)
        output = hidden @ W2 + b2

    Tracks token counts and utilization for load-balancing metrics.
    """

    def __init__(self, config: ModelConfig, expert_id: int = 0):
        self.config = config
        self.expert_id = expert_id
        self.hidden_size = config.hidden_size
        self.intermediate_size = config.intermediate_size
        self.activation = get_activation(config.activation)

        # Always create pure-Python weights so we can dispatch on input type.
        import random

        rng = random.Random(hash((config.seed, "expert", expert_id)) & 0xFFFF)
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

        # Statistics
        self.tokens_processed: int = 0
        self.total_routing_weight: float = 0.0
        self._calls: int = 0

    def forward(self, hidden_states):
        """Process hidden states through the expert.

        Parameters
        ----------
        hidden_states : tensor [batch, seq, hidden] or [num_tokens, hidden]

        Returns
        -------
        tensor of the same shape as input.
        """
        self._calls += 1
        if TORCH_AVAILABLE and hasattr(hidden_states, "requires_grad"):
            hidden = self.activation(self.w1(hidden_states))
            output = self.w2(hidden)
            # Track token count
            num_tokens = hidden_states.size(0) * hidden_states.size(1) if hidden_states.dim() == 3 else hidden_states.size(0)
            self.tokens_processed += num_tokens
            return output
        # Pure-Python fallback
        if hasattr(hidden_states[0], "__iter__"):
            num_tokens = len(hidden_states) * len(hidden_states[0])
        else:
            num_tokens = len(hidden_states)
        self.tokens_processed += num_tokens
        return self._forward_python(hidden_states)

    def _forward_python(self, x):
        """Pure-Python forward pass."""
        # x is [batch, seq, hidden] or [num_tokens, hidden]
        if hasattr(x[0], "__iter__") and hasattr(x[0][0], "__iter__"):
            # 3D: [batch, seq, hidden]
            out = []
            for batch in x:
                out.append(self._forward_2d(batch))
            return out
        return self._forward_2d(x)

    def _forward_2d(self, x):
        """Forward for 2D input [num_tokens, hidden]."""
        # First layer
        hidden = []
        for vec in x:
            h = [sum(v * w for v, w in zip(vec, col)) for col in self.w1_w]
            hidden.append(self.activation(h))
        # Second layer
        out = []
        for vec in hidden:
            o = [sum(v * w for v, w in zip(vec, col)) for col in self.w2_w]
            out.append(o)
        return out

    def record_routing(self, weight: float) -> None:
        """Record a routing weight for this expert."""
        self.total_routing_weight += weight

    def get_stats(self) -> Dict[str, Any]:
        """Return expert statistics."""
        return {
            "expert_id": self.expert_id,
            "tokens_processed": self.tokens_processed,
            "total_routing_weight": self.total_routing_weight,
            "calls": self._calls,
            "utilization": self.tokens_processed,
        }

    def reset_stats(self) -> None:
        """Reset statistics."""
        self.tokens_processed = 0
        self.total_routing_weight = 0.0
        self._calls = 0

    def __call__(self, hidden_states):
        return self.forward(hidden_states)