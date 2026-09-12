# Copyright (c) Ultrone Contributors. All rights reserved.
"""Multi-provider LLM catalog and router definitions.

Supports:
- OpenRouter (Universal model hub)
- Google Gemini (Gemini 1.5 Pro, Flash, Gemini 2.0)
- OpenAI (GPT-4o, GPT-4o-mini, o1)
- Anthropic Claude (Claude 3.5 Sonnet, Haiku)
- DeepSeek (DeepSeek-V3 Chat, DeepSeek-R1 Reasoner)
- Local AI / Ollama / LM Studio / vLLM (Qwen 2.5, Llama 3, etc.)
"""
from __future__ import annotations

import json
import os
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ModelSpec:
    id: str
    name: str
    context_window: int
    description: str
    strengths: List[str] = field(default_factory=list)


@dataclass
class ProviderSpec:
    id: str
    name: str
    description: str
    default_base_url: str
    env_keys: List[str]
    is_local: bool
    recommended_models: List[ModelSpec]

    def resolve_api_key(self, custom_key: str = "") -> str:
        if custom_key and custom_key.strip():
            return custom_key.strip()
        for k in self.env_keys:
            val = os.environ.get(k, "").strip()
            if val:
                return val
        if self.is_local:
            return "ollama-local"
        return ""


SUPPORTED_PROVIDERS: Dict[str, ProviderSpec] = {
    "openrouter": ProviderSpec(
        id="openrouter",
        name="OpenRouter (Universal Router)",
        description="Access all models (Claude, GPT-4o, DeepSeek, Qwen) through one API key",
        default_base_url="https://openrouter.ai/api/v1",
        env_keys=["OPENROUTER_API_KEY"],
        is_local=False,
        recommended_models=[
            ModelSpec("anthropic/claude-3.5-sonnet", "Claude 3.5 Sonnet", 200000, "State of the art reasoning & coding", ["reasoning", "coding"]),
            ModelSpec("deepseek/deepseek-r1", "DeepSeek R1 (Reasoning)", 64000, "Open-weights frontier reasoning model", ["math", "reasoning"]),
            ModelSpec("qwen/qwen-2.5-72b-instruct", "Qwen 2.5 72B Instruct", 131072, "Alibaba flagship high-performance multilingual", ["multilingual", "reasoning"]),
            ModelSpec("openai/gpt-4o", "GPT-4o", 128000, "OpenAI flagship omni model", ["general", "vision"]),
            ModelSpec("google/gemini-2.0-flash-exp:free", "Gemini 2.0 Flash", 1000000, "Ultra-fast Google next-gen preview", ["speed", "long-context"]),
        ],
    ),
    "google": ProviderSpec(
        id="google",
        name="Google Gemini",
        description="Google Generative AI (Gemini 1.5 Pro, Flash, 2.0)",
        default_base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        env_keys=["GEMINI_API_KEY", "GOOGLE_API_KEY"],
        is_local=False,
        recommended_models=[
            ModelSpec("gemini-1.5-pro", "Gemini 1.5 Pro", 2000000, "2M token context, multimodal deep reasoning", ["long-context", "reasoning"]),
            ModelSpec("gemini-1.5-flash", "Gemini 1.5 Flash", 1000000, "Fast, lightweight multimodal model", ["speed", "efficiency"]),
            ModelSpec("gemini-2.0-flash-exp", "Gemini 2.0 Flash Experimental", 1000000, "Next-generation fast multimodal model", ["next-gen", "multimodal"]),
        ],
    ),
    "openai": ProviderSpec(
        id="openai",
        name="OpenAI",
        description="Official OpenAI API (GPT-4o, o1, o3-mini)",
        default_base_url="https://api.openai.com/v1",
        env_keys=["OPENAI_API_KEY"],
        is_local=False,
        recommended_models=[
            ModelSpec("gpt-4o", "GPT-4o", 128000, "Flagship high-intelligence model", ["general", "coding"]),
            ModelSpec("gpt-4o-mini", "GPT-4o Mini", 128000, "Fast, cost-efficient model", ["speed", "cost"]),
            ModelSpec("o1-preview", "OpenAI o1 Preview", 128000, "Chain-of-thought deep reasoning", ["reasoning", "stem"]),
        ],
    ),
    "claude": ProviderSpec(
        id="claude",
        name="Anthropic Claude",
        description="Direct or proxy Anthropic Claude models",
        default_base_url="https://api.anthropic.com/v1",
        env_keys=["ANTHROPIC_API_KEY"],
        is_local=False,
        recommended_models=[
            ModelSpec("claude-3-5-sonnet-20241022", "Claude 3.5 Sonnet (Latest)", 200000, "Top tier coding, analysis & agent control", ["coding", "agent"]),
            ModelSpec("claude-3-5-haiku-20241022", "Claude 3.5 Haiku", 200000, "Blazing fast response speed", ["speed"]),
            ModelSpec("claude-3-opus-20240229", "Claude 3 Opus", 200000, "Deep synthesis and nuance", ["writing", "analysis"]),
        ],
    ),
    "deepseek": ProviderSpec(
        id="deepseek",
        name="DeepSeek",
        description="Direct DeepSeek API (V3 and R1 reasoning)",
        default_base_url="https://api.deepseek.com/v1",
        env_keys=["DEEPSEEK_API_KEY"],
        is_local=False,
        recommended_models=[
            ModelSpec("deepseek-chat", "DeepSeek-V3", 64000, "High-efficiency general purpose chat model", ["chat", "coding"]),
            ModelSpec("deepseek-reasoner", "DeepSeek-R1", 64000, "Open reasoning model with visible CoT", ["math", "reasoning", "logic"]),
        ],
    ),
    "ollama": ProviderSpec(
        id="ollama",
        name="Local AI (Ollama / Qwen)",
        description="Private, local inference on your own hardware via Ollama",
        default_base_url="http://localhost:11434/v1",
        env_keys=["OLLAMA_HOST"],
        is_local=True,
        recommended_models=[
            ModelSpec("qwen2.5:7b", "Qwen 2.5 7B (Local)", 32768, "Fast, lightweight local battlefield agent", ["offline", "privacy"]),
            ModelSpec("qwen2.5:14b", "Qwen 2.5 14B (Local)", 32768, "High-grade local reasoning & tactical planning", ["offline", "reasoning"]),
            ModelSpec("qwen2.5-coder:7b", "Qwen 2.5 Coder 7B (Local)", 32768, "Local coding and tool-calling agent", ["offline", "coding"]),
            ModelSpec("deepseek-r1:7b", "DeepSeek R1 7B (Local Distill)", 32768, "Local distilled chain-of-thought reasoner", ["offline", "reasoning"]),
            ModelSpec("llama3.2:3b", "Llama 3.2 3B (Local)", 131072, "Ultra-compact edge deployment model", ["edge", "lightweight"]),
        ],
    ),
    "lmstudio": ProviderSpec(
        id="lmstudio",
        name="Local AI (LM Studio)",
        description="Local GUI inference server (OpenAI compatible endpoint)",
        default_base_url="http://localhost:1234/v1",
        env_keys=[],
        is_local=True,
        recommended_models=[
            ModelSpec("local-model", "LM Studio Loaded Model", 32768, "Currently loaded model in LM Studio", ["offline", "local"]),
        ],
    ),
}


class MultiProviderLLMClient:
    """Universal client capable of executing chat completions across any provider."""

    def __init__(
        self,
        provider: str = "openrouter",
        model: Optional[str] = None,
        api_key: str = "",
        base_url: str = "",
        timeout: int = 45,
    ):
        self.provider_id = provider.lower().strip()
        self.provider_spec = SUPPORTED_PROVIDERS.get(self.provider_id, SUPPORTED_PROVIDERS["openrouter"])
        self.model = model or self.provider_spec.recommended_models[0].id
        self.api_key = self.provider_spec.resolve_api_key(api_key)
        self.base_url = (base_url or self.provider_spec.default_base_url).rstrip("/")
        self.timeout = timeout

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 1500,
    ) -> Dict[str, Any]:
        """Execute chat completion across OpenAI-compatible or Anthropic native endpoints."""
        is_anthropic_native = self.provider_id == "claude" and "anthropic.com" in self.base_url

        if is_anthropic_native:
            endpoint = f"{self.base_url}/messages"
            headers = {
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            }
            # Extract system message if present
            system_msg = ""
            non_system_messages = []
            for m in messages:
                if m.get("role") == "system":
                    system_msg = m.get("content", "")
                else:
                    non_system_messages.append(m)

            payload: Dict[str, Any] = {
                "model": self.model,
                "messages": non_system_messages or [{"role": "user", "content": "Hello"}],
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            if system_msg:
                payload["system"] = system_msg
        else:
            endpoint = f"{self.base_url}/chat/completions"
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "Ultrone-Operational-Console/2.0",
            }
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            if self.provider_id == "openrouter":
                headers["HTTP-Referer"] = "https://github.com/Mr-Nobody-Anonymous/ultrone"
                headers["X-Title"] = "ULTRONE Console"

            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if is_anthropic_native:
                    contents = data.get("content") or []
                    content = contents[0].get("text", "") if contents else ""
                    usage = data.get("usage", {})
                else:
                    choices = data.get("choices") or [{}]
                    choice = choices[0] if choices else {}
                    content = choice.get("message", {}).get("content", "")
                    usage = data.get("usage", {})

                return {
                    "success": True,
                    "content": content,
                    "provider": self.provider_id,
                    "model": self.model,
                    "usage": usage,
                    "raw": data,
                }
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            return {
                "success": False,
                "error": f"HTTP {e.code}: {e.reason}",
                "details": err_body,
                "provider": self.provider_id,
                "model": self.model,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "provider": self.provider_id,
                "model": self.model,
            }

    def health_check(self) -> Dict[str, Any]:
        """Verify connectivity to provider endpoint."""
        # For local providers, check if endpoint is reachable
        if self.provider_spec.is_local:
            try:
                test_url = f"{self.base_url}/models"
                req = urllib.request.Request(test_url, headers={"User-Agent": "Ultrone"}, method="GET")
                with urllib.request.urlopen(req, timeout=3) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    return {
                        "available": True,
                        "status": "connected",
                        "provider": self.provider_id,
                        "base_url": self.base_url,
                        "models_found": len(data.get("data", [])),
                    }
            except Exception as e:
                return {
                    "available": False,
                    "status": "unreachable",
                    "provider": self.provider_id,
                    "base_url": self.base_url,
                    "note": f"Local endpoint offline: {e}. Start Ollama or LM Studio.",
                }

        # For cloud providers, check if API key is present
        has_key = bool(self.api_key)
        return {
            "available": has_key,
            "status": "configured" if has_key else "missing_api_key",
            "provider": self.provider_id,
            "base_url": self.base_url,
            "model": self.model,
            "key_env_var": self.provider_spec.env_keys[0] if self.provider_spec.env_keys else None,
        }
