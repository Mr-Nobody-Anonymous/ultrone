# Copyright (c) Ultrone Contributors. All rights reserved.
"""Model Gateway request, response, and metadata schemas."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TokenUsage:
    """Token consumption statistics for a model invocation."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0


@dataclass
class GatewayRequest:
    """Standardized request payload for ModelGateway."""

    prompt: str
    model: Optional[str] = None
    system_prompt: Optional[str] = None
    messages: Optional[List[Dict[str, str]]] = None
    temperature: float = 0.7
    max_tokens: int = 2048
    tools: Optional[List[Dict[str, Any]]] = None
    required_capabilities: Optional[List[str]] = None
    stop_sequences: Optional[List[str]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    request_id: str = field(default_factory=lambda: f"req-{uuid.uuid4().hex[:8]}")


@dataclass
class GatewayResponse:
    """Standardized response payload from ModelGateway."""

    content: str
    model: str
    provider: str
    usage: TokenUsage = field(default_factory=TokenUsage)
    finish_reason: str = "stop"
    raw_response: Optional[Dict[str, Any]] = None
    latency_ms: float = 0.0
    request_id: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class ModelMetadata:
    """Capabilities and specification of an LLM."""

    model_id: str
    provider: str
    context_window: int = 128000
    max_output_tokens: int = 4096
    supports_tools: bool = True
    supports_vision: bool = False
    supports_structured_output: bool = True
    reasoning_score: float = 0.8
    coding_score: float = 0.8
    cost_per_1k_prompt: float = 0.001
    cost_per_1k_completion: float = 0.002
