# Copyright (c) Ultrone Contributors. All rights reserved.
"""Adapter modules for parameter-efficient fine-tuning.

Adapters are small bottleneck feed-forward networks inserted between
existing layers. Only adapters are trained; the base model is frozen.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import torch
import torch.nn as nn

logger = logging.getLogger("Ultrone.Learning.Continual.Adapter")


@dataclass
class AdapterConfig:
    """Configuration for adapter modules."""
    reduction_factor: int = 16  # Bottleneck: hidden // reduction_factor
    non_linearity: str = "relu"
    residual: bool = True
    adapter_layers: Optional[List[str]] = None  # Layer names to attach adapters to
    init_scale: float = 1e-3  # Initial weight scale for residual path


class Adapter(nn.Module):
    """A single adapter module (bottleneck feed-forward).

    Architecture: Linear(down) → Activation → Linear(up) → Residual
    """

    def __init__(self, input_dim: int, config: AdapterConfig):
        super().__init__()
        self.config = config
        bottleneck_dim = max(1, input_dim // config.reduction_factor)

        self.down = nn.Linear(input_dim, bottleneck_dim)
        self.activation = nn.ReLU() if config.non_linearity == "relu" else nn.GELU()
        self.up = nn.Linear(bottleneck_dim, input_dim)

        # Initialize to near-zero so residual is small initially
        nn.init.kaiming_uniform_(self.down.weight, a=2.0)
        nn.init.zeros_(self.up.weight)
        nn.init.zeros_(self.up.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.up(self.activation(self.down(x)))


class AdapterModule(nn.Module):
    """Holds adapters for a specific layer in the base model.

    The adapter output is added to the layer's output as a residual delta.
    """

    def __init__(self, input_dim: int, config: AdapterConfig):
        super().__init__()
        self.adapter = Adapter(input_dim, config)
        self.config = config

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Apply adapter with a scaled residual."""
        delta = self.adapter(x)
        return x + self.config.init_scale * delta


class AdapterManager:
    """Manages adapter modules across a model.

    Attaches adapters to specified layers, manages training, and can
    enable/disable specific adapters for task switching.
    """

    def __init__(self, model: nn.Module, config: AdapterConfig):
        self.model = model
        self.config = config
        self._adapters: Dict[str, AdapterModule] = {}

        # Freeze the base model
        for param in self.model.parameters():
            param.requires_grad = False

        self._attach_adapters()

    def _attach_adapters(self) -> None:
        """Attach adapter modules to target layers."""
        target_names = self.config.adapter_layers or []
        for name, module in self.model.named_modules():
            if not target_names or name.split(".")[-1] in target_names:
                if isinstance(module, (nn.Linear, nn.LayerNorm)):
                    input_dim = module.in_features if hasattr(module, "in_features") else module.normalized_shape[0]
                    adapter = AdapterModule(input_dim, self.config)
                    self._adapters[name] = adapter
                    setattr(
                        module,
                        "_ultrone_adapter",
                        adapter,
                    )

    def get_trainable_parameters(self) -> List[nn.Parameter]:
        """Return only adapter parameters that require gradients."""
        params = []
        for adapter in self._adapters.values():
            params.extend(adapter.parameters())
        return params

    def enable_adapter(self, name: str) -> None:
        """Enable a specific adapter by name."""
        if name in self._adapters:
            for param in self._adapters[name].parameters():
                param.requires_grad = True

    def disable_adapter(self, name: str) -> None:
        """Disable a specific adapter."""
        if name in self._adapters:
            for param in self._adapters[name].parameters():
                param.requires_grad = False

    def save_adapter(self, name: str, path: str) -> None:
        """Save a single adapter's weights."""
        adapter = self._adapters.get(name)
        if adapter:
            torch.save({"adapter_state": adapter.state_dict(), "config": self.config}, path)

    def load_adapter(self, name: str, path: str) -> None:
        """Load adapter weights from a file."""
        ckpt = torch.load(path, map_location="cpu")
        adapter = self._adapters.get(name)
        if adapter:
            adapter.load_state_dict(ckpt["adapter_state"])

    def get_stats(self) -> Dict[str, Any]:
        total = sum(p.numel() for p in self.get_trainable_parameters())
        base = sum(p.numel() for p in self.model.parameters())
        return {
            "num_adapters": len(self._adapters),
            "adapter_params": total,
            "base_model_params": base,
            "param_ratio": total / max(base, 1),
            "reduction_factor": self.config.reduction_factor,
        }
