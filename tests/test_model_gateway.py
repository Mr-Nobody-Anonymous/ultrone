# Copyright (c) Ultrone Contributors. All rights reserved.
from adapters.llm.gateway import (
    GatewayRequest,
    ModelCapabilityRegistry,
    ModelGateway,
    ModelMetadata,
    ModelRouter,
)


def test_gateway_generate_string_prompt():
    gateway = ModelGateway()
    resp = gateway.generate("Explain reinforcement learning in simple terms")

    assert resp.content is not None
    assert len(resp.content) > 0
    assert resp.usage.total_tokens > 0
    assert resp.latency_ms >= 0.0


def test_gateway_capability_routing():
    registry = ModelCapabilityRegistry()
    router = ModelRouter(registry)
    gateway = ModelGateway(router=router)

    # Request requiring vision
    req_vision = GatewayRequest(
        prompt="Describe this satellite image",
        required_capabilities=["vision"],
    )
    resp = gateway.generate(req_vision)
    assert resp.model in ("anthropic/claude-3.5-sonnet", "openai/gpt-4o")

    # Request requiring high-reasoning coding
    req_code = GatewayRequest(
        prompt="Write a distributed lock in Python",
        required_capabilities=["coding"],
    )
    resp_code = gateway.generate(req_code)
    assert resp_code.model is not None


def test_gateway_fallback_on_provider_error():
    gateway = ModelGateway(fallback_models=["local/mock-default"])

    def failing_invoker(req, model_id):
        raise ConnectionError("Primary cloud provider unreachable")

    gateway.register_provider_invoker("failing_provider", failing_invoker)

    # Register failing model
    gateway.router.registry.register_model(
        ModelMetadata(model_id="failing/cloud-1", provider="failing_provider")
    )

    req = GatewayRequest(prompt="Hello", model="failing/cloud-1")
    resp = gateway.generate(req)

    # Should have fallen back successfully
    assert resp.model == "local/mock-default"
    assert "Mock Response" in resp.content or "Response generated" in resp.content
