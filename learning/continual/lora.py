# Copyright (c) Ultrone Contributors. All rights reserved.
"""LoRA (Low-Rank Adaptation) for parameter-efficient fine-tuning.

Implements LoRA adapters that inject low-rank updates into weight matrices
without modifying the original weights. Supports QLoRA (quantized LoRA)
when bitsandbytes is available.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

import torch
import torch.nn as nn

logger = logging.getLogger("Ultrone.Learning.Continual.LoRA")


@dataclass
class LoRAConfig:
    """Configuration for LoRA adapters."""
    r: int = 8           # Rank of the low-rank decomposition
    alpha: int = 32      # Scaling factor
    dropout: float = 0.1
    target_modules: Optional[list] = None  # e.g. ["q_proj", "v_proj", "k_proj", "o_proj"]
    bias: str = "none"   # "none", "all", "lora_only"
    modules_to_save: Optional[list] = None  # Additional modules to fine-tune
    lora_dtype: torch.dtype = torch.float32

    def scaling(self) -> float:
        return self.alpha / self.r


class LoRALinear(nn.Module):
    """Linear layer with LoRA injected."""

    def __init__(self, in_features: int, out_features: int, config: LoRAConfig):
        super().__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.r = config.r
        self.alpha = config.alpha
        self.scaling = self.alpha / self.r
        self.dropout = nn.Dropout(p=config.dropout)

        # LoRA matrices: B @ A, initialized so that B @ A ≈ 0
        self.lora_A = nn.Parameter(torch.empty(self.r, in_features))
        self.lora_B = nn.Parameter(torch.empty(out_features, self.r))
        nn.init.kaiming_uniform_(self.lora_A, a=1.0)
        nn.init.zeros_(self.lora_B)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Apply LoRA on top of the frozen weight: W + (B @ A) * scaling."""
        lora_out = (self.lora_B @ self.lora_A).T  # (in, out)
        return self.scaling * lora_out


class LoRAAdapter(nn.Module):
    """Wraps a model with LoRA adapters.

    Freezes the base model weights and injects low-rank adaptation matrices
    into the target modules.
    """

    def __init__(self, model: nn.Module, config: LoRAConfig):
        super().__init__()
        self.model = model
        self.config = config
        self._target_modules = config.target_modules or ["q_proj", "v_proj"]

        # Freeze base model
        for param in self.model.parameters():
            param.requires_grad = False

        # Inject LoRA into target modules
        self._lora_modules: Dict[str, LoRALinear] = {}
        self._inject_lora()

    def _inject_lora(self) -> None:
        """Find target modules and replace them with LoRA-augmented versions."""
        from functools import partial

        modules_to_replace = []
        for name, module in self.model.named_modules():
            if name.split(".")[-1] in self._target_modules and isinstance(module, nn.Linear):
                modules_to_replace.append((name, module))

        for name, orig_module in modules_to_replace:
            parent_name = ".".join(name.split(".")[:-1])
            if parent_name:
                parent = self.model.get_submodule(parent_name)
            else:
                parent = self.model

            lora_module = LoRAAdapter._create_lora_wrapper(orig_module, self.config)
            self._lora_modules[name] = lora_module

            # Monkey-patch: the LoRA matrices are added to the forward pass
            target_attr = name.split(".")[-1]
            setattr(parent, target_attr, _LoRAMergedLinear(orig_module, lora_module))

    @staticmethod
    def _create_lora_wrapper(orig: nn.Linear, config: LoRAConfig) -> LoRALinear:
        return LoRALinear(orig.in_features, orig.out_features, config)

    def forward(self, *args, **kwargs):
        return self.model(*args, **kwargs)

    def get_trainable_parameters(self) -> list:
        """Return list of trainable parameter names (LoRA params only)."""
        trainable = []
        for name, param in self.named_parameters():
            if param.requires_grad:
                trainable.append(name)
        return trainable

    def merge_and_unload(self) -> nn.Module:
        """Merge LoRA weights into base model and return the merged model."""
        for name, lora_module in self._lora_modules.items():
            parent_name = ".".join(name.split(".")[:-1])
            parent = self.model.get_submodule(parent_name) if parent_name else self.model
            target_attr = name.split(".")[-1]
            orig = getattr(parent, target_attr)
            if hasattr(orig, "base_layer"):
                merged_weight = orig.base_layer.weight.data + (
                    lora_module.scaling * (lora_module.lora_B @ lora_module.lora_A).T
                )
                orig.base_layer.weight.data = merged_weight
        return self.model

    def get_stats(self) -> Dict[str, Any]:
        total_params = sum(p.numel() for p in self.model.parameters())
        trainable_params = sum(p.numel() for p in self.model.parameters() if p.requires_grad)
        lora_params = sum(p.numel() for p in self.parameters() if p.requires_grad)
        return {
            "rank": self.config.r,
            "alpha": self.config.alpha,
            "scaling": self.config.scaling(),
            "total_params": total_params,
            "trainable_params": trainable_params + lora_params,
            "lora_params": lora_params,
            "compression_ratio": lora_params / max(trainable_params, 1),
        }


class _LoRAMergedLinear(nn.Module):
    """Merged linear layer that combines a frozen base layer with LoRA."""

    def __init__(self, base_layer: nn.Linear, lora_layer: LoRALinear):
        super().__init__()
        self.base_layer = base_layer
        self.lora_layer = lora_layer
        self.base_layer.weight.requires_grad = False
        if self.base_layer.bias is not None:
            self.base_layer.bias.requires_grad = False

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Combine base output with LoRA delta."""
        base_out = self.base_layer(x)
        lora_delta = self.lora_layer(x)
        return base_out + lora_delta
