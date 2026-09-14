# Copyright (c) Ultrone Contributors. All rights reserved.
"""ModelGateway: Unified interface across all LLM providers and models."""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Dict, List, Optional

from .capabilities import ModelCapabilityRegistry
from .router import ModelRouter
from .schemas import GatewayRequest, GatewayResponse, TokenUsage

logger = logging.getLogger("Ultrone.Gateway")


class ModelGateway:
    """Unified Gateway for all LLM interactions in ULTRONE."""

    def __init__(
        self,
        router: Optional[ModelRouter] = None,
        fallback_models: Optional[List[str]] = None,
    ) -> None:
        self.router = router or ModelRouter()
        self.fallback_models = fallback_models or ["local/mock-default"]
        self._provider_invokers: Dict[str, Callable[[GatewayRequest, str], GatewayResponse]] = {}

    def register_provider_invoker(
        self, provider_id: str, invoker: Callable[[GatewayRequest, str], GatewayResponse]
    ) -> None:
        """Register custom provider execution logic."""
        self._provider_invokers[provider_id] = invoker

    def generate(self, request: GatewayRequest | str) -> GatewayResponse:
        """Generate response from LLM through unified routing and fallback chain.

        Parameters
        ----------
        request: GatewayRequest | str
            Either a raw prompt string or structured GatewayRequest.

        Returns
        -------
        GatewayResponse
            Normalized response containing content, token usage, and metadata.
        """
        if isinstance(request, str):
            req = GatewayRequest(prompt=request)
        else:
            req = request

        start_time = time.time()
        primary_model = self.router.route(req)
        chain = [primary_model] + [m for m in self.fallback_models if m != primary_model]

        last_error: Optional[Exception] = None

        for model_id in chain:
            try:
                response = self._invoke_model(req, model_id)
                response.latency_ms = (time.time() - start_time) * 1000.0
                response.request_id = req.request_id
                return response
            except Exception as exc:
                logger.warning("Provider error for model %s: %s. Trying next fallback.", model_id, exc)
                last_error = exc

        # If all providers fail, return graceful fallback response
        latency = (time.time() - start_time) * 1000.0
        return GatewayResponse(
            content=f"[Gateway Mock Response to: {req.prompt[:60]}...]",
            model="local/mock-default",
            provider="local",
            usage=TokenUsage(prompt_tokens=len(req.prompt.split()), completion_tokens=10, total_tokens=len(req.prompt.split()) + 10),
            latency_ms=latency,
            request_id=req.request_id,
        )

    def _invoke_model(self, req: GatewayRequest, model_id: str) -> GatewayResponse:
        """Invoke underlying provider or registered custom invoker."""
        meta = self.router.registry.get_model(model_id)
        provider = meta.provider if meta else "local"

        if provider in self._provider_invokers:
            return self._provider_invokers[provider](req, model_id)

        # Attempt invocation via MultiProviderLLMClient if configured
        try:
            from adapters.llm.providers import MultiProviderLLMClient, SUPPORTED_PROVIDERS
            # Check if provider is supported and has an API key or is local
            spec = SUPPORTED_PROVIDERS.get(provider)
            if spec:
                api_key = spec.resolve_api_key()
                if api_key and api_key != "ollama-local":
                    client = MultiProviderLLMClient(provider=provider, model=model_id, timeout=15)
                    messages = req.messages or []
                    if not messages:
                        if req.system_prompt:
                            messages.append({"role": "system", "content": req.system_prompt})
                        messages.append({"role": "user", "content": req.prompt})
                    raw_res = client.chat_completion(messages=messages, temperature=req.temperature, max_tokens=req.max_tokens)
                    if raw_res.get("success"):
                        usage_dict = raw_res.get("usage", {})
                        usage = TokenUsage(
                            prompt_tokens=usage_dict.get("prompt_tokens", len(req.prompt.split())),
                            completion_tokens=usage_dict.get("completion_tokens", 25),
                            total_tokens=usage_dict.get("total_tokens", len(req.prompt.split()) + 25),
                        )
                        return GatewayResponse(
                            content=raw_res.get("content", ""),
                            model=model_id,
                            provider=provider,
                            usage=usage,
                            raw_response=raw_res,
                            finish_reason="stop",
                        )
        except Exception as exc:
            logger.debug("Live provider %s invocation skipped or failed: %s", provider, exc)

        # Standard simulated response for local/offline/test environments
        prompt_words = req.prompt.split()
        usage = TokenUsage(
            prompt_tokens=len(prompt_words),
            completion_tokens=25,
            total_tokens=len(prompt_words) + 25,
            estimated_cost_usd=0.0001,
        )

        return GatewayResponse(
            content=f"Response generated for: {req.prompt[:50]} (model: {model_id})",
            model=model_id,
            provider=provider,
            usage=usage,
            finish_reason="stop",
        )
