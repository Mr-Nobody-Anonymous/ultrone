# Copyright (c) Ultrone Contributors. All rights reserved.
"""Model router for selecting optimal LLMs and providers."""

from __future__ import annotations

from typing import List, Optional

from .capabilities import ModelCapabilityRegistry
from .schemas import GatewayRequest


class ModelRouter:
    """Routes requests to appropriate models and providers."""

    def __init__(self, registry: Optional[ModelCapabilityRegistry] = None) -> None:
        self.registry = registry or ModelCapabilityRegistry()

    def route(self, request: GatewayRequest) -> str:
        """Select model ID for the given request."""
        # If model explicitly specified and known, use it
        if request.model and self.registry.get_model(request.model):
            return request.model

        # If required capabilities specified, find best match
        if request.required_capabilities:
            return self.registry.find_best_model(
                required_capabilities=request.required_capabilities,
                min_context=request.max_tokens * 2,
            )

        # Default fallback
        return request.model or "local/mock-default"
