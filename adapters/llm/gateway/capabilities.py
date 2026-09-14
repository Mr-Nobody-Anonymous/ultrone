# Copyright (c) Ultrone Contributors. All rights reserved.
"""Model capability discovery and matching matrix."""

from __future__ import annotations

from typing import Dict, List, Optional

from .schemas import ModelMetadata


class ModelCapabilityRegistry:
    """Registry of known model specifications and capabilities."""

    DEFAULT_MODELS: Dict[str, ModelMetadata] = {
        "anthropic/claude-3.5-sonnet": ModelMetadata(
            model_id="anthropic/claude-3.5-sonnet",
            provider="anthropic",
            context_window=200000,
            max_output_tokens=8192,
            supports_tools=True,
            supports_vision=True,
            supports_structured_output=True,
            reasoning_score=0.98,
            coding_score=0.98,
            cost_per_1k_prompt=0.003,
            cost_per_1k_completion=0.015,
        ),
        "openai/gpt-4o": ModelMetadata(
            model_id="openai/gpt-4o",
            provider="openai",
            context_window=128000,
            max_output_tokens=4096,
            supports_tools=True,
            supports_vision=True,
            supports_structured_output=True,
            reasoning_score=0.95,
            coding_score=0.94,
            cost_per_1k_prompt=0.0025,
            cost_per_1k_completion=0.010,
        ),
        "deepseek/deepseek-r1": ModelMetadata(
            model_id="deepseek/deepseek-r1",
            provider="deepseek",
            context_window=64000,
            max_output_tokens=8192,
            supports_tools=False,
            supports_vision=False,
            supports_structured_output=True,
            reasoning_score=0.97,
            coding_score=0.93,
            cost_per_1k_prompt=0.00055,
            cost_per_1k_completion=0.00219,
        ),
        "qwen/qwen-2.5-72b-instruct": ModelMetadata(
            model_id="qwen/qwen-2.5-72b-instruct",
            provider="qwen",
            context_window=131072,
            max_output_tokens=8192,
            supports_tools=True,
            supports_vision=False,
            supports_structured_output=True,
            reasoning_score=0.91,
            coding_score=0.92,
            cost_per_1k_prompt=0.0004,
            cost_per_1k_completion=0.0008,
        ),
        "glm/glm-4-plus": ModelMetadata(
            model_id="glm/glm-4-plus",
            provider="glm",
            context_window=128000,
            max_output_tokens=4096,
            supports_tools=True,
            supports_vision=False,
            supports_structured_output=True,
            reasoning_score=0.90,
            coding_score=0.89,
            cost_per_1k_prompt=0.001,
            cost_per_1k_completion=0.002,
        ),
        "local/mock-default": ModelMetadata(
            model_id="local/mock-default",
            provider="local",
            context_window=32768,
            max_output_tokens=2048,
            supports_tools=True,
            supports_vision=False,
            supports_structured_output=True,
            reasoning_score=0.75,
            coding_score=0.75,
            cost_per_1k_prompt=0.0,
            cost_per_1k_completion=0.0,
        ),
    }

    def __init__(self) -> None:
        self._models: Dict[str, ModelMetadata] = dict(self.DEFAULT_MODELS)

    def register_model(self, meta: ModelMetadata) -> None:
        self._models[meta.model_id] = meta

    def get_model(self, model_id: str) -> Optional[ModelMetadata]:
        return self._models.get(model_id)

    def find_best_model(
        self,
        required_capabilities: Optional[List[str]] = None,
        min_context: int = 0,
        prefer_low_cost: bool = False,
    ) -> str:
        """Select best candidate model matching criteria."""
        reqs = set(c.lower() for c in (required_capabilities or []))
        candidates: List[ModelMetadata] = []

        for m in self._models.values():
            if m.context_window < min_context:
                continue
            if "vision" in reqs and not m.supports_vision:
                continue
            if "tools" in reqs and not m.supports_tools:
                continue
            candidates.append(m)

        if not candidates:
            return "local/mock-default"

        if prefer_low_cost:
            candidates.sort(key=lambda x: (x.cost_per_1k_prompt + x.cost_per_1k_completion))
        else:
            candidates.sort(key=lambda x: (x.reasoning_score + x.coding_score), reverse=True)

        return candidates[0].model_id
