# Copyright (c) Ultrone Contributors. All rights reserved.
"""Unit tests for MultiProviderLLMClient and AI router."""

import pytest
from adapters.llm.providers import (
    SUPPORTED_PROVIDERS,
    MultiProviderLLMClient,
    ProviderSpec,
)
from apps.api.routers.ai import router
from fastapi.testclient import TestClient
from fastapi import FastAPI


def test_supported_providers_inventory():
    """Verify that all requested providers are present in the catalog."""
    expected = ["openrouter", "google", "openai", "claude", "deepseek", "ollama", "lmstudio"]
    for provider_id in expected:
        assert provider_id in SUPPORTED_PROVIDERS, f"Missing provider: {provider_id}"
        spec = SUPPORTED_PROVIDERS[provider_id]
        assert isinstance(spec, ProviderSpec)
        assert len(spec.recommended_models) > 0
        assert spec.default_base_url.startswith("http")


def test_local_ai_defaults():
    """Verify local Ollama provider configuration defaults."""
    ollama = SUPPORTED_PROVIDERS["ollama"]
    assert ollama.is_local is True
    assert "localhost:11434" in ollama.default_base_url

    client = MultiProviderLLMClient(provider="ollama")
    assert client.provider_id == "ollama"
    assert "qwen" in client.model.lower()


def test_provider_api_key_resolution(monkeypatch):
    """Verify custom key takes precedence over environment fallback."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "env-key-123")
    client_env = MultiProviderLLMClient(provider="openrouter")
    assert client_env.api_key == "env-key-123"

    client_custom = MultiProviderLLMClient(provider="openrouter", api_key="custom-key-456")
    assert client_custom.api_key == "custom-key-456"


def test_ai_router_endpoints():
    """Test FastAPI router for AI provider metadata and test-connection."""
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    # 1. GET /api/ai/providers
    res = client.get("/api/ai/providers")
    assert res.status_code == 200
    data = res.json()
    assert "providers" in data
    assert "openrouter" in data["providers"]
    assert "ollama" in data["providers"]
    assert "google" in data["providers"]
    assert "deepseek" in data["providers"]

    # 2. POST /api/ai/test-connection without key
    test_res = client.post("/api/ai/test-connection", json={"provider": "openrouter"})
    assert test_res.status_code == 200
    test_data = test_res.json()
    assert "available" in test_data
