# Copyright (c) Ultrone Contributors. All rights reserved.
"""LLM provider adapters — port for model providers.

Concrete wiring should wrap ``orchestration.model_registry`` /
``orchestration.router`` (model selection + fallback) and
``core.llm_service`` (hosted LLM calls). No provider logic lives here.
"""
from adapters.base import BaseAdapter, unavailable
from typing import Any, Dict

__all__ = ["LLMAdapter", "BaseAdapter"]


class LLMAdapter(BaseAdapter):
    """Port every LLM provider implementation must satisfy."""

    name = "llm"

    def connect(self) -> bool:  # pragma: no cover - placeholder
        return False

    def close(self) -> None:  # pragma: no cover - placeholder
        pass

    def health(self) -> Dict[str, Any]:  # pragma: no cover - placeholder
        return unavailable("no provider implementation wired; see "
                           "orchestration/model_registry and core/llm_service")
