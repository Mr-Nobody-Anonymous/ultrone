# Copyright (c) Ultrone Contributors. All rights reserved.
"""Sparse Mixture-of-Experts layer.

Combines the MoE router and expert modules into a complete sparse MoE
layer with top-k routing, expert capacity, shared experts, and load
balancing. Exposes all required metrics.
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

from .expert import Expert
from .model_config import ModelConfig
from .router import MoERouter

logger = logging.getLogger("Ultrone.Frontier.Model.MoE")


class SparseMoE:
    """Sparse Mixture-of-Experts layer.

    Routes each token to its top-k experts, applies the experts, and
    combines the outputs using routing weights. Supports:

    - Top-k expert selection
    - Expert capacity (with token dropping)
    - Shared experts (always active)
    - Load-balancing auxiliary loss
    - Expert statistics
    - Routing visualization

    Parameters
    ----------
    config : ModelConfig
        Model configuration with ``num_experts > 0``.
    """

    def __init__(self, config: ModelConfig):
        if config.num_experts <= 0:
            raise ValueError("SparseMoE requires num_experts > 0")
        self.config = config
        self.num_experts = config.num_experts
        self.top_k = config.num_experts_per_tok
        self.shared_experts = config.shared_experts

        self.router = MoERouter(config)
        self.experts: List[Expert] = [
            Expert(config, expert_id=i) for i in range(config.num_experts)
        ]
        self.shared_expert_list: List[Expert] = [
            Expert(config, expert_id=config.num_experts + i)
            for i in range(config.shared_experts)
        ]

        # Statistics
        self.dropped_tokens: int = 0
        self.total_tokens: int = 0
        self._last_aux_loss: float = 0.0
        self._activated_parameters: int = 0

    def forward(self, hidden_states):
        """Apply sparse MoE to hidden states.

        Parameters
        ----------
        hidden_states : tensor [batch, seq, hidden] or [num_tokens, hidden]

        Returns
        -------
        (output, aux_loss)
        """
        # Flatten to [num_tokens, hidden]
        self._is_tensor = TORCH_AVAILABLE and hasattr(hidden_states, "requires_grad")
        if self._is_tensor:
            if hidden_states.dim() == 3:
                batch, seq, hidden = hidden_states.size()
                flat = hidden_states.reshape(-1, hidden)
            else:
                flat = hidden_states
                batch, seq = 1, flat.size(0)
            num_tokens = flat.size(0)
        else:
            if hasattr(hidden_states[0], "__iter__") and hasattr(hidden_states[0][0], "__iter__"):
                batch = len(hidden_states)
                seq = len(hidden_states[0])
                flat = [vec for b in hidden_states for vec in b]
            else:
                batch, seq = 1, len(hidden_states)
                flat = hidden_states
            num_tokens = len(flat)

        self.total_tokens += num_tokens

        # Route tokens
        top_k_indices, top_k_probs, probs, aux_loss = self.router.route(flat)
        self._last_aux_loss = aux_loss

        # Expert capacity
        capacity = int((num_tokens * self.top_k / self.num_experts) * self.config.expert_capacity_factor)
        capacity = max(1, capacity)

        # Compute expert outputs
        if self._is_tensor and TORCH_AVAILABLE:
            # Initialize output buffer
            output = torch.zeros_like(flat)
            expert_counts = [0] * self.num_experts

            for token_idx in range(num_tokens):
                for k in range(self.top_k):
                    expert_id = top_k_indices[token_idx, k].item()
                    weight = top_k_probs[token_idx, k].item()
                    if expert_counts[expert_id] >= capacity:
                        self.dropped_tokens += 1
                        continue
                    expert_counts[expert_id] += 1
                    expert_out = self.experts[expert_id](flat[token_idx].unsqueeze(0))
                    output[token_idx] += weight * expert_out.squeeze(0)
                    self.experts[expert_id].record_routing(weight)

            # Shared experts (always active)
            if self.shared_expert_list:
                shared_out = torch.zeros_like(flat)
                for expert in self.shared_expert_list:
                    shared_out += expert(flat)
                output = output + shared_out / max(1, len(self.shared_expert_list))

            # Reshape back
            if hidden_states.dim() == 3:
                output = output.reshape(batch, seq, -1)
            else:
                output = output.reshape(batch, seq, -1) if hasattr(hidden_states, 'dim') else output

            # Track activated parameters
            self._activated_parameters = self.top_k * self._expert_param_count() + (
                self.shared_experts * self._expert_param_count()
            )

            return output, aux_loss

        # Pure-Python fallback
        output = [[0.0] * self.config.hidden_size for _ in range(num_tokens)]
        expert_counts = [0] * self.num_experts

        for token_idx in range(num_tokens):
            for k in range(self.top_k):
                expert_id = top_k_indices[token_idx][k]
                weight = top_k_probs[token_idx][k]
                if expert_counts[expert_id] >= capacity:
                    self.dropped_tokens += 1
                    continue
                expert_counts[expert_id] += 1
                expert_out = self.experts[expert_id]([flat[token_idx]])[0]
                for d in range(self.config.hidden_size):
                    output[token_idx][d] += weight * expert_out[d]
                self.experts[expert_id].record_routing(weight)

        # Shared experts
        if self.shared_expert_list:
            for expert in self.shared_expert_list:
                shared_out = expert(flat)
                for i in range(num_tokens):
                    for d in range(self.config.hidden_size):
                        output[i][d] += shared_out[i][d] / max(1, len(self.shared_expert_list))

        # Reshape back
        if hasattr(hidden_states[0], "__iter__") and hasattr(hidden_states[0][0], "__iter__"):
            reshaped = []
            idx = 0
            for b in range(batch):
                row = []
                for s in range(seq):
                    row.append(output[idx])
                    idx += 1
                reshaped.append(row)
            output = reshaped

        self._activated_parameters = self.top_k * self._expert_param_count() + (
            self.shared_experts * self._expert_param_count()
        )

        return output, aux_loss

    def _expert_param_count(self) -> int:
        """Count parameters in a single expert."""
        expert = self.experts[0]
        # Count pure-Python weights (always available)
        count = len(expert.w1_w) * len(expert.w1_w[0]) + len(expert.w2_w) * len(expert.w2_w[0])
        # Also count torch weights if available
        if TORCH_AVAILABLE and hasattr(expert, "w1") and hasattr(expert, "w2"):
            torch_count = (
                expert.w1.weight.numel() + expert.w1.bias.numel() if expert.w1.bias is not None else expert.w1.weight.numel()
            ) + (
                expert.w2.weight.numel() + expert.w2.bias.numel() if expert.w2.bias is not None else expert.w2.weight.numel()
            )
            count = max(count, torch_count)
        return count

    def get_stats(self) -> Dict[str, Any]:
        """Return MoE statistics."""
        router_stats = self.router.get_stats()
        expert_stats = [e.get_stats() for e in self.experts]
        total_tokens = self.total_tokens or 1
        return {
            "type": "SparseMoE",
            "num_experts": self.num_experts,
            "top_k": self.top_k,
            "shared_experts": self.shared_experts,
            "tokens_per_expert": router_stats["tokens_per_expert"],
            "expert_utilization": router_stats["expert_utilization"],
            "routing_entropy": router_stats["routing_entropy"],
            "dropped_tokens": self.dropped_tokens,
            "load_balance_loss": self._last_aux_loss,
            "activated_parameters": self._activated_parameters,
            "total_tokens": self.total_tokens,
            "experts": expert_stats,
        }

    def get_routing_visualization(self) -> Dict[str, Any]:
        """Return data for routing visualization."""
        return self.router.get_routing_visualization()

    def reset_stats(self) -> None:
        """Reset all statistics."""
        self.router.reset_stats()
        for expert in self.experts:
            expert.reset_stats()
        for expert in self.shared_expert_list:
            expert.reset_stats()
        self.dropped_tokens = 0
        self.total_tokens = 0
        self._last_aux_loss = 0.0

    def __call__(self, hidden_states):
        return self.forward(hidden_states)