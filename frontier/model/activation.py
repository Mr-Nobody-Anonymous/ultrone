# Copyright (c) Ultrone Contributors. All rights reserved.
"""Activation functions for frontier models.

Provides a registry of activation functions compatible with PyTorch. All
activations are real computations (no stubs). Falls back to pure-Python
implementations when PyTorch is unavailable.
"""

from __future__ import annotations

import math
from typing import Callable, Dict

try:
    import torch
    import torch.nn.functional as F

    TORCH_AVAILABLE = True
except ImportError:  # pragma: no cover
    TORCH_AVAILABLE = False

from .model_config import ActivationType


def _gelu_python(x):
    """Gaussian Error Linear Unit (HuggingFace approximation)."""
    return 0.5 * x * (1.0 + math.tanh(math.sqrt(2.0 / math.pi) * (x + 0.044715 * x**3)))


def _relu_python(x):
    return max(0.0, x)


def _silu_python(x):
    return x / (1.0 + math.exp(-x))


def _mish_python(x):
    return x * math.tanh(math.log(1.0 + math.exp(x)))


def _tanh_python(x):
    return math.tanh(x)


def _quick_gelu_python(x):
    return x * (1.0 / (1.0 + math.exp(-1.702 * x)))


class ActivationFunction:
    """A callable activation function.

    Wraps either a PyTorch implementation or a pure-Python fallback so the
    model layer works even without torch installed.
    """

    def __init__(self, activation_type: ActivationType):
        self.activation_type = activation_type
        self._torch_fn = self._get_torch_fn(activation_type)
        self._python_fn = self._get_python_fn(activation_type)

    def _get_torch_fn(self, activation_type: ActivationType):
        if not TORCH_AVAILABLE:
            return None
        mapping = {
            ActivationType.GELU: F.gelu,
            ActivationType.RELU: F.relu,
            ActivationType.SILU: F.silu,
            ActivationType.SWISH: F.silu,
            ActivationType.MISH: F.mish,
            ActivationType.TANH: torch.tanh,
            ActivationType.QUICK_GELU: lambda x: x * torch.sigmoid(1.702 * x),
        }
        return mapping.get(activation_type)

    def _get_python_fn(self, activation_type: ActivationType) -> Callable:
        mapping = {
            ActivationType.GELU: _gelu_python,
            ActivationType.RELU: _relu_python,
            ActivationType.SILU: _silu_python,
            ActivationType.SWISH: _silu_python,
            ActivationType.MISH: _mish_python,
            ActivationType.TANH: _tanh_python,
            ActivationType.QUICK_GELU: _quick_gelu_python,
        }
        return mapping.get(activation_type, _relu_python)

    def __call__(self, x):
        """Apply the activation function."""
        if TORCH_AVAILABLE and self._torch_fn is not None:
            return self._torch_fn(x)
        # Pure-Python fallback for scalars / lists
        if hasattr(x, "__iter__") and not isinstance(x, (str, bytes)):
            return [self._python_fn(v) for v in x]
        return self._python_fn(x)

    def __repr__(self) -> str:
        return f"ActivationFunction({self.activation_type.value})"


def get_activation(activation_type: ActivationType) -> ActivationFunction:
    """Get an activation function by type."""
    return ActivationFunction(activation_type)


def get_activation_from_string(name: str) -> ActivationFunction:
    """Get an activation function from a string name."""
    return ActivationFunction(ActivationType(name.lower()))


# Registry for quick lookup
ACTIVATION_REGISTRY: Dict[str, Callable] = {
    "gelu": lambda: get_activation(ActivationType.GELU),
    "relu": lambda: get_activation(ActivationType.RELU),
    "silu": lambda: get_activation(ActivationType.SILU),
    "swish": lambda: get_activation(ActivationType.SWISH),
    "mish": lambda: get_activation(ActivationType.MISH),
    "tanh": lambda: get_activation(ActivationType.TANH),
    "quick_gelu": lambda: get_activation(ActivationType.QUICK_GELU),
}