# Copyright (c) Ultrone Contributors. All rights reserved.
"""Normalization layers for frontier models.

Provides LayerNorm, RMSNorm, and BatchNorm implementations with pure-Python
fallbacks so the model layer works without PyTorch.
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

from .model_config import NormType


class RMSNorm:
    """Root Mean Square Normalization.

    Normalizes by the RMS of the input, then scales by a learned weight.
    Used by LLaMA, Mistral, and other modern transformers.
    """

    def __init__(self, hidden_size: int, eps: float = 1e-5):
        self.hidden_size = hidden_size
        self.eps = eps
        if TORCH_AVAILABLE:
            self.weight = nn.Parameter(torch.ones(hidden_size))
        else:
            self.weight = [1.0] * hidden_size

    def forward(self, x):
        """Apply RMS normalization."""
        if TORCH_AVAILABLE and hasattr(x, "requires_grad"):
            variance = x.to(torch.float32).pow(2).mean(-1, keepdim=True)
            x = x * torch.rsqrt(variance + self.eps)
            return self.weight * x.to(x.dtype)
        # Pure-Python fallback
        if hasattr(x, "__iter__") and not isinstance(x, (str, bytes)):
            mean_sq = sum(v * v for v in x) / len(x)
            scale = 1.0 / math.sqrt(mean_sq + self.eps)
            return [v * scale * w for v, w in zip(x, self.weight)]
        return x * (1.0 / math.sqrt(x * x + self.eps)) * self.weight[0]

    def __call__(self, x):
        return self.forward(x)


class LayerNorm:
    """Layer Normalization.

    Normalizes across the feature dimension with learned weight and bias.
    """

    def __init__(self, hidden_size: int, eps: float = 1e-5):
        self.hidden_size = hidden_size
        self.eps = eps
        if TORCH_AVAILABLE:
            self.weight = nn.Parameter(torch.ones(hidden_size))
            self.bias = nn.Parameter(torch.zeros(hidden_size))
        else:
            self.weight = [1.0] * hidden_size
            self.bias = [0.0] * hidden_size

    def forward(self, x):
        """Apply layer normalization."""
        if TORCH_AVAILABLE and hasattr(x, "requires_grad"):
            mean = x.mean(-1, keepdim=True)
            var = x.var(-1, keepdim=True, unbiased=False)
            x = (x - mean) / torch.sqrt(var + self.eps)
            return self.weight * x + self.bias
        # Pure-Python fallback
        if hasattr(x, "__iter__") and not isinstance(x, (str, bytes)):
            n = len(x)
            mean = sum(x) / n
            var = sum((v - mean) ** 2 for v in x) / n
            scale = 1.0 / math.sqrt(var + self.eps)
            return [(v - mean) * scale * w + b for v, w, b in zip(x, self.weight, self.bias)]
        return x

    def __call__(self, x):
        return self.forward(x)


class BatchNorm:
    """Batch Normalization (simplified, inference-mode).

    Uses running statistics for normalization. Training mode updates running
    statistics from batch statistics.
    """

    def __init__(self, hidden_size: int, eps: float = 1e-5, momentum: float = 0.1):
        self.hidden_size = hidden_size
        self.eps = eps
        self.momentum = momentum
        self.training = True
        if TORCH_AVAILABLE:
            self.weight = nn.Parameter(torch.ones(hidden_size))
            self.bias = nn.Parameter(torch.zeros(hidden_size))
            self.register_buffer = lambda name, val: setattr(self, name, val)
            self.register_buffer("running_mean", torch.zeros(hidden_size))
            self.register_buffer("running_var", torch.ones(hidden_size))
        else:
            self.weight = [1.0] * hidden_size
            self.bias = [0.0] * hidden_size
            self.running_mean = [0.0] * hidden_size
            self.running_var = [1.0] * hidden_size

    def forward(self, x):
        """Apply batch normalization."""
        if TORCH_AVAILABLE:
            if self.training:
                batch_mean = x.mean(dim=0)
                batch_var = x.var(dim=0, unbiased=False)
                self.running_mean = (1 - self.momentum) * self.running_mean + self.momentum * batch_mean.detach()
                self.running_var = (1 - self.momentum) * self.running_var + self.momentum * batch_var.detach()
                mean, var = batch_mean, batch_var
            else:
                mean, var = self.running_mean, self.running_var
            x = (x - mean) / torch.sqrt(var + self.eps)
            return self.weight * x + self.bias
        # Pure-Python fallback (per-feature)
        if hasattr(x, "__iter__") and not isinstance(x, (str, bytes)):
            # x is a list of feature vectors
            n = len(x)
            if n == 0:
                return x
            dim = len(x[0]) if hasattr(x[0], "__iter__") else 1
            if dim == 1:
                mean = sum(x) / n
                var = sum((v - mean) ** 2 for v in x) / n
                if self.training:
                    self.running_mean = [(1 - self.momentum) * rm + self.momentum * mean for rm in self.running_mean]
                    self.running_var = [(1 - self.momentum) * rv + self.momentum * var for rv in self.running_var]
                scale = 1.0 / math.sqrt(var + self.eps)
                return [(v - mean) * scale * w + b for v, w, b in zip(x, self.weight, self.bias)]
            # Multi-dim
            result = []
            for vec in x:
                normed = []
                for j, v in enumerate(vec):
                    mean = self.running_mean[j]
                    var = self.running_var[j]
                    scale = 1.0 / math.sqrt(var + self.eps)
                    normed.append((v - mean) * scale * self.weight[j] + self.bias[j])
                result.append(normed)
            return result
        return x

    def __call__(self, x):
        return self.forward(x)

    def eval(self):
        """Set to evaluation mode."""
        self.training = False

    def train(self):
        """Set to training mode."""
        self.training = True


def get_norm(norm_type: NormType, hidden_size: int, eps: float = 1e-5):
    """Get a normalization layer by type."""
    if norm_type == NormType.RMS_NORM:
        return RMSNorm(hidden_size, eps)
    if norm_type == NormType.BATCH_NORM:
        return BatchNorm(hidden_size, eps)
    return LayerNorm(hidden_size, eps)


def get_norm_from_string(name: str, hidden_size: int, eps: float = 1e-5):
    """Get a normalization layer from a string name."""
    return get_norm(NormType(name.lower()), hidden_size, eps)