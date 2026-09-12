# Copyright (c) Ultrone Contributors. All rights reserved.
"""LLM provider adapters — port for model providers.

Provides concrete integrations for:
- OpenRouter
- Google Gemini
- OpenAI
- Anthropic Claude
- DeepSeek
- Local AI (Ollama / Qwen / LM Studio / vLLM)
"""
from adapters.base import BaseAdapter
from .providers import SUPPORTED_PROVIDERS, MultiProviderLLMClient, ProviderSpec, ModelSpec
from typing import Any, Dict, List, Optional

__all__ = [
    "LLMAdapter",
    "BaseAdapter",
    "SUPPORTED_PROVIDERS",
    "MultiProviderLLMClient",
    "ProviderSpec",
    "ModelSpec",
]


class LLMAdapter(BaseAdapter):
    """Universal multi-provider LLM Adapter port."""

    name = "llm"

    def __init__(self, default_provider: str = "openrouter", **kwargs):
        self.default_provider = default_provider
        self.client = MultiProviderLLMClient(provider=default_provider, **kwargs)

    def connect(self) -> bool:
        check = self.client.health_check()
        return bool(check.get("available", False))

    def close(self) -> None:
        pass

    def health(self) -> Dict[str, Any]:
        return self.client.health_check()

    def get_supported_providers(self) -> Dict[str, Any]:
        """Return catalog of all supported providers and their recommended models."""
        return {
            pid: {
                "id": spec.id,
                "name": spec.name,
                "description": spec.description,
                "default_base_url": spec.default_base_url,
                "is_local": spec.is_local,
                "is_configured": bool(spec.resolve_api_key()),
                "models": [
                    {
                        "id": m.id,
                        "name": m.name,
                        "context_window": m.context_window,
                        "description": m.description,
                        "strengths": m.strengths,
                    }
                    for m in spec.recommended_models
                ],
            }
            for pid, spec in SUPPORTED_PROVIDERS.items()
        }
