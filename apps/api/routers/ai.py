# Copyright (c) Ultrone Contributors. All rights reserved.
"""FastAPI router for Multi-Provider AI (OpenRouter, Google, OpenAI, Claude, DeepSeek, Local Qwen)."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from adapters.llm import SUPPORTED_PROVIDERS, MultiProviderLLMClient

router = APIRouter(prefix="/api/ai", tags=["ai"])


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    provider: str = "openrouter"
    model: Optional[str] = None
    messages: List[ChatMessage]
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0.3
    max_tokens: int = 1500


class ConnectionTestRequest(BaseModel):
    provider: str
    model: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None


@router.get("/providers")
def list_providers():
    """Return all available AI providers, configuration status, and recommended models."""
    out = {}
    for pid, spec in SUPPORTED_PROVIDERS.items():
        out[pid] = {
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
    return {"providers": out}


@router.post("/chat")
def chat_completion(req: ChatRequest):
    """Execute chat completion across any supported cloud or local provider."""
    client = MultiProviderLLMClient(
        provider=req.provider,
        model=req.model,
        api_key=req.api_key or "",
        base_url=req.base_url or "",
    )

    messages = [{"role": m.role, "content": m.content} for m in req.messages]
    result = client.chat_completion(
        messages=messages,
        temperature=req.temperature,
        max_tokens=req.max_tokens,
    )

    if not result.get("success"):
        raise HTTPException(status_code=502, detail=result)

    return result


@router.post("/test-connection")
def test_connection(req: ConnectionTestRequest):
    """Test connectivity to a specific provider and model."""
    client = MultiProviderLLMClient(
        provider=req.provider,
        model=req.model,
        api_key=req.api_key or "",
        base_url=req.base_url or "",
    )
    return client.health_check()
