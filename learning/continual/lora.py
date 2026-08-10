# Copyright (c) Ultrone Contributors. All rights reserved.
"""LoRA (Low-Rank Adaptation) for parameter-efficient fine-tuning."""
from __future__ import annotations
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import torch
import torch.nn as nn

logger = logging.getLogger("Ultrone.Learning.Continual.LoRA")


@dataclass
class LoRAConfig:
    r: int = 8
    alpha: int = 32
    dropout: float = 0.1
    target_modules: Optional[List[str]] = None
    bias: str = "none"
    modules_to_save: Optional[List[str]] = None
    lora_dtype: torch.dtype = torch.float32

    def scaling(self) -> float:
        return self.alpha / self.r


class LoRAAdapter(nn.Module):
    """Wraps a model with LoRA adapters using ParameterDict."""

    def __init__(self, model: nn.Module, config: LoRAConfig):
        super().__init__()
        self.model = model
        self.config = config
        self._target_modules = config.target_modules or []
        self._scaling = config.scaling()

        for param in self.model.parameters():
            param.requires_grad = False

        self.lora_A = nn.ParameterDict()
        self.lora_B = nn.ParameterDict()
        self._matched_modules: Dict[str, nn.Linear] = {}
        self._match_linear_modules()

    @staticmethod
    def _safe_name(name: str) -> str:
        return name.replace(".", "_") or "root"

    def _match_linear_modules(self) -> None:
        for name, module in self.model.named_modules():
            if not isinstance(module, nn.Linear):
                continue
            key = self._safe_name(name)
            param_name = name.split(".")[-1] if name else "weight"
            if (not self._target_modules or param_name in self._target_modules
                    or "weight" in self._target_modules):
                r = self.config.r
                self.lora_A[key] = nn.Parameter(torch.empty(r, module.in_features))
                self.lora_B[key] = nn.Parameter(torch.empty(module.out_features, r))
                nn.init.kaiming_uniform_(self.lora_A[key], a=1.0)
                nn.init.zeros_(self.lora_B[key])
                self._matched_modules[key] = module

    def forward(self, *args, **kwargs):
        return self.model(*args, **kwargs)

    def get_trainable_parameters(self) -> List[nn.Parameter]:
        params = list(self.model.parameters())
        params.extend(self.lora_A.parameters())
        params.extend(self.lora_B.parameters())
        return params

    def merge_and_unload(self) -> nn.Module:
        for name, module in self._matched_modules.items():
            delta = self._scaling * (self.lora_B[name] @ self.lora_A[name]).T
            module.weight.data += delta
        for name in list(self.lora_A.keys()):
            del self.lora_A[name]
            del self.lora_B[name]
        return self.model

    def get_stats(self) -> Dict[str, Any]:
        lora_params = sum(p.numel() for p in self.parameters())
        return {
            "rank": self.config.r, "alpha": self.config.alpha,
            "scaling": self.config.scaling(),
            "lora_params": lora_params,
            "num_adapters": len(self._matched_modules),
        }
