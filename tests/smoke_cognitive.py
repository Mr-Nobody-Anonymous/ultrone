"""Smoke test for the ULTRONE cognitive architecture."""
import asyncio
from cognitive import (
    CognitiveAgent,
    CognitiveAgentConfig,
    CognitiveIntegration,
    CognitiveIntegrationConfig,
    Observation,
    Modality,
    CognitiveEventType,
)


async def smoke_test():
    # Test 1: Create agent and run a decision cycle
    agent = CognitiveAgent(CognitiveAgentConfig(agent_id="smoke-test"))
    obs = Observation(
        modalities={Modality.TEXT: "Analyze the research landscape"},
        confidence=0.9,
    )
    ctx = await agent.perceive(obs)
    print(f"[OK] Agent perceived: cycle={ctx.cycle_id[:8]}, confidence={ctx.confidence:.2f}")
    print(f"[OK] Decision traces: {len(agent.get_decision_traces())}")

    # Test 2: Decision with goals
    obs2 = Observation(modalities={Modality.TEXT: "Deploy new model"}, confidence=0.85)
    actions = await agent.decide(obs2, goals=["improve_accuracy"])
    print(f"[OK] Actions generated: {len(actions)}")

    # Test 3: Integration facade with benchmark
    integration = CognitiveIntegration(CognitiveIntegrationConfig())
    observations = [
        Observation(modalities={Modality.TEXT: f"Task {i}"}, confidence=0.9)
        for i in range(5)
    ]
    result = await integration.run_benchmark("smoke_benchmark", observations)
    print(f"[OK] Benchmark: cycles={result['cycles']}, success_rate={result['success_rate']:.2f}")

    # Test 4: Event subscription
    received = []

    def on_event(event):
        received.append(event.event_type.value)

    integration.subscribe(CognitiveEventType.PERCEPTION, on_event)
    await integration.run_cycle(
        Observation(modalities={Modality.TEXT: "Test event"}, confidence=0.9)
    )
    print(f"[OK] Events received: {len(received)}")

    print()
    print("ALL SMOKE TESTS PASSED")


if __name__ == "__main__":
    asyncio.run(smoke_test())