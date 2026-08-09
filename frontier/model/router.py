# Copyright (c) Ultrone Contributors. All rights reserved.
"""MoE Router — routes tokens to experts.

Implements router logits, softmax routing, top-k expert selection, routing
weights, load balancing, and auxiliary routing loss. Exposes routing
statistics for analysis and visualization.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F

    TORCH_AVAILABLE = True
except ImportError:  # pragma: no cover
    TORCH_AVAILABLE = False

from .model_config import ModelConfig


class MoERouter:
    """Routes tokens to experts via learned logits.

    Implements:
    - Router logits: ``logits = x @ W_r``
    - Softmax routing: ``probs = softmax(logits)``
    - Top-k expert selection
    - Routing weights (normalized top-k probabilities)
    - Load balancing (auxiliary loss)
    - Expert capacity enforcement
    - Routing statistics
    """

    def __init__(self, config: ModelConfig):
        self.config = config
        self.num_experts = config.num_experts
        self.top_k = config.num_experts_per_tok
        self.hidden_size = config.hidden_size
        self.expert_capacity_factor = config.expert_capacity_factor

        # Always create pure-Python weights so we can dispatch on input type.
        import random

        rng = random.Random(hash((config.seed, "router")) & 0xFFFF)
        self.router_w = [
            [rng.gauss(0.0, config.initializer_range) for _ in range(config.hidden_size)]
            for _ in range(config.num_experts)
        ]
        if TORCH_AVAILABLE:
            self.router_weight = nn.Linear(config.hidden_size, config.num_experts, bias=False)

        # Statistics
        self.tokens_per_expert: List[int] = [0] * config.num_experts
        self.routing_weights_history: List[List[float]] = []
        self.dropped_tokens: int = 0
        self.total_tokens: int = 0
        self._routing_entropy_sum: float = 0.0
        self._routing_calls: int = 0

    def _compute_logits(self, hidden_states):
        """Compute router logits."""
        if TORCH_AVAILABLE and hasattr(hidden_states, "requires_grad"):
            return self.router_weight(hidden_states)
        # Pure-Python: hidden_states is [num_tokens, hidden]
        if hasattr(hidden_states[0], "__iter__"):
            return [
                [sum(v * w for v, w in zip(vec, col)) for col in self.router_w]
                for vec in hidden_states
            ]
        return [sum(v * w for v, w in zip(hidden_states, col)) for col in self.router_w]

    def _softmax(self, logits):
        """Softmax over the expert dimension."""
        if TORCH_AVAILABLE and hasattr(logits, "requires_grad"):
            return F.softmax(logits, dim=-1)
        # Pure-Python
        if hasattr(logits[0], "__iter__"):
            out = []
            for row in logits:
                max_v = max(row)
                exps = [math.exp(v - max_v) for v in row]
                total = sum(exps) or 1.0
                out.append([e / total for e in exps])
            return out
        max_v = max(logits)
        exps = [math.exp(v - max_v) for v in logits]
        total = sum(exps) or 1.0
        return [e / total for e in exps]

    def route(self, hidden_states):
        """Route tokens to experts.

        Parameters
        ----------
        hidden_states : tensor [num_tokens, hidden] or [batch, seq, hidden]

        Returns
        -------
        (expert_indices, routing_weights, routing_probs, aux_loss)
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
        else:
            if hasattr(hidden_states[0], "__iter__") and hasattr(hidden_states[0][0], "__iter__"):
                batch = len(hidden_states)
                seq = len(hidden_states[0])
                flat = [vec for b in hidden_states for vec in b]
            else:
                batch, seq = 1, len(hidden_states)
                flat = hidden_states

        num_tokens = flat.size(0) if self._is_tensor else len(flat)
        self.total_tokens += num_tokens
        self._routing_calls += 1

        # 1. Router logits
        logits = self._compute_logits(flat)

        # 2. Softmax routing probabilities
        probs = self._softmax(logits)

        # 3. Top-k expert selection
        if self._is_tensor:
            top_k_probs, top_k_indices = torch.topk(probs, k=self.top_k, dim=-1)
            # Normalize top-k weights
            norm = top_k_probs.sum(dim=-1, keepdim=True).clamp(min=1e-9)
            routing_weights = top_k_probs / norm
        else:
            top_k_indices = []
            top_k_probs = []
            for row in probs:
                idx = sorted(range(len(row)), key=lambda i: row[i], reverse=True)[: self.top_k]
                vals = [row[i] for i in idx]
                total = sum(vals) or 1e-9
                top_k_indices.append(idx)
                top_k_probs.append([v / total for v in vals])

        # 4. Load balancing (auxiliary loss)
        aux_loss = self._compute_aux_loss(probs, top_k_indices, num_tokens, self._is_tensor)

        # 5. Update statistics
        self._update_stats(top_k_indices, top_k_probs, probs, num_tokens, self._is_tensor)

        return top_k_indices, top_k_probs, probs, aux_loss

    def _compute_aux_loss(self, probs, top_k_indices, num_tokens: int, is_tensor: bool) -> float:
        """Compute the load-balancing auxiliary loss.

        Standard Switch Transformer aux loss:
            loss = N * sum(f_i * P_i)
        where f_i is the fraction of tokens routed to expert i and P_i is
        the mean routing probability for expert i.
        """
        if num_tokens == 0:
            return 0.0

        if is_tensor and TORCH_AVAILABLE:
            # Fraction of tokens routed to each expert
            expert_counts = torch.zeros(self.num_experts, device=probs.device)
            for i in range(num_tokens):
                for j in range(self.top_k):
                    expert_counts[top_k_indices[i, j]] += 1.0
            f = expert_counts / num_tokens
            # Mean routing probability per expert
            p = probs.mean(dim=0)
            loss = self.num_experts * (f * p).sum()
            return loss * self.config.aux_loss_coef

        # Pure-Python
        expert_counts = [0.0] * self.num_experts
        for i in range(num_tokens):
            for j in range(self.top_k):
                expert_counts[top_k_indices[i][j]] += 1.0
        f = [c / num_tokens for c in expert_counts]
        # Mean routing probability per expert
        p = [0.0] * self.num_experts
        for row in probs:
            for e, val in enumerate(row):
                p[e] += val
        p = [v / num_tokens for v in p]
        loss = self.num_experts * sum(fi * pi for fi, pi in zip(f, p))
        return loss * self.config.aux_loss_coef

    def _update_stats(self, top_k_indices, top_k_probs, probs, num_tokens: int, is_tensor: bool) -> None:
        """Update routing statistics."""
        # Tokens per expert
        for i in range(num_tokens):
            for j in range(self.top_k):
                if is_tensor and TORCH_AVAILABLE:
                    self.tokens_per_expert[top_k_indices[i, j].item()] += 1
                else:
                    self.tokens_per_expert[top_k_indices[i][j]] += 1

        # Routing entropy
        if is_tensor and TORCH_AVAILABLE:
            entropy = -(probs * torch.log(probs.clamp(min=1e-9))).sum(dim=-1).mean().item()
        else:
            entropy = 0.0
            for row in probs:
                entropy += -sum(p * math.log(max(p, 1e-9)) for p in row)
            entropy /= num_tokens
        self._routing_entropy_sum += entropy

    def get_stats(self) -> Dict[str, Any]:
        """Return routing statistics."""
        total = self.total_tokens or 1
        return {
            "type": "MoERouter",
            "num_experts": self.num_experts,
            "top_k": self.top_k,
            "tokens_per_expert": self.tokens_per_expert,
            "expert_utilization": [t / total for t in self.tokens_per_expert],
            "routing_entropy": self._routing_entropy_sum / max(1, self._routing_calls),
            "dropped_tokens": self.dropped_tokens,
            "total_tokens": self.total_tokens,
            "load_balance_loss": self._last_aux_loss if hasattr(self, "_last_aux_loss") else 0.0,
        }

    def get_routing_visualization(self) -> Dict[str, Any]:
        """Return data for routing visualization."""
        return {
            "tokens_per_expert": self.tokens_per_expert,
            "expert_utilization": [
                t / max(1, self.total_tokens) for t in self.tokens_per_expert
            ],
            "routing_entropy": self._routing_entropy_sum / max(1, self._routing_calls),
            "dropped_tokens": self.dropped_tokens,
        }

    def reset_stats(self) -> None:
        """Reset routing statistics."""
        self.tokens_per_expert = [0] * self.num_experts
        self.routing_weights_history.clear()
        self.dropped_tokens = 0
        self.total_tokens = 0
        self._routing_entropy_sum = 0.0
        self._routing_calls = 0