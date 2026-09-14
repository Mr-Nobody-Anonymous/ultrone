# Copyright (c) Ultrone Contributors. All rights reserved.
"""Comprehensive integration test suite for ULTRONE Agent Core.

Verifies the 10 core integration scenarios:
1. Goal -> planning -> execution -> evaluation
2. Agent failure -> recovery
3. Agent crash -> checkpoint restore
4. Tool failure -> retry/recovery
5. Context overflow -> compaction
6. Stalled worker -> watchdog recovery
7. Model failure -> gateway fallback
8. Domain agent (Air/Cyber) -> harness worker
9. Tool permission denial
10. Independent evaluator rejection
"""

from __future__ import annotations

import tempfile
import time
from typing import Any, Dict

import pytest

from adapters.llm.gateway import (
    GatewayRequest,
    ModelCapabilityRegistry,
    ModelGateway,
    ModelMetadata,
)
from packages.agents.agents.air.base import AirAgent
from packages.agents.agents.cyber.base import CyberAgent
from packages.agents.harness import (
    AgentHarness,
    CheckpointStore,
    DomainAgentWorker,
    EvaluationStatus,
    Goal,
    HarnessConfig,
    HarnessWorker,
    IndependentEvaluator,
    LifecycleState,
    RecoveryAction,
    WorkerInput,
    WorkerOutput,
    WorkerSelector,
)
from packages.agents.liveness import (
    HealthStatus,
    LivenessRegistry,
    LivenessWatchdog,
)
from packages.agents.tools import (
    PermissionDeniedError,
    RiskLevel,
    ToolDefinition,
    ToolParameter,
    ToolPermissionChecker,
    ToolRegistry,
    ToolRuntime,
    create_standard_tool_catalog,
)
from packages.core.context import (
    ContextBudget,
    ContextCompactor,
    ContextManager,
    TokenCounter,
)
from packages.observability.tracing import Tracer


def test_scenario_1_goal_planning_execution_evaluation_success():
    """Scenario 1: Goal -> planning -> execution -> evaluation success."""
    tracer = Tracer("ultrone-test")
    with tempfile.TemporaryDirectory() as tmpdir:
        config = HarnessConfig(checkpoint_dir=tmpdir)
        harness = AgentHarness(config=config, tracer=tracer)

        goal = Goal(
            description="Process radar telemetry batch",
            acceptance_criteria=["tracks_processed", "zero_drop_rate"],
        )

        def mock_executor(state):
            return {
                "tracks_processed": 50,
                "zero_drop_rate": True,
                "status": "nominal",
            }

        result = harness.run(goal=goal, executor_fn=mock_executor, task_id="sc1-task")

        assert result.status == EvaluationStatus.PASS
        assert result.passed
        assert harness.state_machine.current_state == LifecycleState.COMPLETED

        # Checkpoint verified
        cp = harness.checkpoint_store.load_latest("sc1-task")
        assert cp is not None
        assert cp.current_phase == LifecycleState.COMPLETED.value


def test_scenario_2_agent_failure_and_recovery():
    """Scenario 2: Agent execution failure -> self-healing recovery retry."""
    harness = AgentHarness(config=HarnessConfig(max_retries_per_step=2))
    attempts = [0]

    def flaky_executor(state):
        attempts[0] += 1
        if attempts[0] == 1:
            raise ConnectionResetError("Transient network failure on attempt 1")
        return {"result": "recovered successfully", "status": "done"}

    goal = Goal(description="Resilient data pull", acceptance_criteria=["result"])
    result = harness.run(goal=goal, executor_fn=flaky_executor, task_id="sc2-task")

    assert attempts[0] == 2
    assert result.status == EvaluationStatus.PASS
    assert result.passed


def test_scenario_3_agent_crash_checkpoint_restore():
    """Scenario 3: Process crash -> reload latest checkpoint -> resume execution."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = CheckpointStore(storage_dir=tmpdir)
        config = HarnessConfig(checkpoint_dir=tmpdir)
        harness = AgentHarness(config=config, checkpoint_store=store)

        goal = Goal(
            description="Long multi-stage compute job",
            acceptance_criteria=["stage1_complete", "stage2_complete"],
        )

        def partial_executor(state):
            return {"stage1_complete": True}

        # First run: completes stage 1 only
        harness.run(goal=goal, executor_fn=partial_executor, task_id="sc3-crash-task")

        # SIMULATE CRASH: Destroy harness instance, create clean fresh harness
        del harness

        resumed_harness = AgentHarness(config=config, checkpoint_store=store)

        def full_executor(state):
            return {"stage1_complete": True, "stage2_complete": True}

        resumed_result = resumed_harness.resume_from_checkpoint(
            task_id="sc3-crash-task",
            executor_fn=full_executor,
        )

        assert resumed_result.status == EvaluationStatus.PASS
        assert resumed_result.passed
        assert resumed_harness.state_machine.current_state == LifecycleState.COMPLETED


def test_scenario_4_tool_failure_and_retry_recovery():
    """Scenario 4: Tool execution failure handled through ToolRuntime and recovered."""
    registry = ToolRegistry()
    call_count = [0]

    def flaky_tool(target: str) -> str:
        call_count[0] += 1
        if call_count[0] == 1:
            raise IOError("Temporary device busy")
        return f"Telemetry from {target}"

    registry.register(
        ToolDefinition(
            name="flaky_sensor",
            description="Intermittent hardware sensor",
            parameters=[ToolParameter(name="target", required=True)],
        ),
        flaky_tool,
    )

    runtime = ToolRuntime(registry=registry)

    # First attempt fails cleanly
    res1 = runtime.execute("flaky_sensor", {"target": "radar-1"})
    assert not res1.success
    assert "Temporary device busy" in res1.error

    # Second attempt succeeds
    res2 = runtime.execute("flaky_sensor", {"target": "radar-1"})
    assert res2.success
    assert "radar-1" in res2.output


def test_scenario_5_context_overflow_compaction():
    """Scenario 5: Context overflow -> dynamic compaction prevents out-of-budget crashes."""
    cm = ContextManager(budget=ContextBudget(total_window=200, user_prompt=50))

    huge_payload = "\n".join([f"Long data record {i}: " + "x" * 50 for i in range(500)])
    assert TokenCounter.count_tokens(huge_payload) > 1000

    # Ensure budget compacts the huge payload to within window limit
    compacted = cm.ensure_budget(huge_payload, max_tokens=100)
    assert TokenCounter.count_tokens(compacted) <= 120
    assert "compacted" in compacted or "truncated" in compacted


def test_scenario_6_stalled_worker_watchdog_recovery():
    """Scenario 6: Stalled worker detected by LivenessWatchdog and recovered."""
    registry = LivenessRegistry()
    recovered_workers = []

    def on_stall_callback(record):
        recovered_workers.append(record.agent_id)
        # Simulate supervisor restart: refresh heartbeat
        registry.record_heartbeat(record.agent_id, record.task_id, state="RECOVERED")

    watchdog = LivenessWatchdog(registry=registry, recovery_callback=on_stall_callback)

    # Simulate agent whose last beat was 160s ago (> 120s STALLED threshold)
    simulated_now = 5000.0
    registry.record_heartbeat("worker-uav-07", "task-recon", now=simulated_now - 160.0)

    # Watchdog sweep
    stalled = watchdog.check_and_recover(now=simulated_now)

    assert len(stalled) == 1
    assert stalled[0].agent_id == "worker-uav-07"
    assert "worker-uav-07" in recovered_workers


def test_scenario_7_model_failure_gateway_fallback():
    """Scenario 7: Primary model failure -> ModelGateway transparent fallback."""
    gateway = ModelGateway(fallback_models=["local/mock-default"])

    def failing_invoker(req, model_id):
        raise ConnectionError("503 Service Unavailable: Primary upstream down")

    gateway.register_provider_invoker("failing_provider", failing_invoker)
    gateway.router.registry.register_model(
        ModelMetadata(model_id="cloud/unavailable-model", provider="failing_provider")
    )

    req = GatewayRequest(prompt="Synthesize summary", model="cloud/unavailable-model")
    response = gateway.generate(req)

    # Verified fallback
    assert response.model == "local/mock-default"
    assert response.provider == "local"
    assert len(response.content) > 0


def test_scenario_8_domain_agent_as_harness_worker():
    """Scenario 8: Real domain agents (CyberAgent, AirAgent) execute under AgentHarness."""
    # 1. Test CyberAgent under harness
    cyber_agent = CyberAgent(unit_id="cyber-infiltrator-01", position=(10.0, 20.0, 0.0), team="blue")
    cyber_worker = DomainAgentWorker(cyber_agent)

    selector = WorkerSelector()
    selector.register_worker(cyber_worker)

    harness = AgentHarness(worker_selector=selector)

    goal = Goal(
        description="Execute cyber reconnaissance on simulated network",
        acceptance_criteria=["hosts_found", "scan_result"],
    )

    result = harness.run(
        goal=goal,
        worker=cyber_worker,
        initial_state={"action": "scan_network", "network_id": "subnet-omega"},
        task_id="sc8-cyber-task",
    )

    assert result.status == EvaluationStatus.PASS
    assert result.passed
    assert cyber_agent.scans_performed >= 1

    # 2. Test AirAgent under harness
    air_agent = AirAgent(unit_id="uav-scout-01", position=(0.0, 0.0, 500.0), team="blue")
    air_worker = DomainAgentWorker(air_agent)

    air_goal = Goal(
        description="Climb to cruise altitude",
        acceptance_criteria=["altitude"],
    )

    air_result = harness.run(
        goal=air_goal,
        worker=air_worker,
        initial_state={"action": "set_altitude", "altitude": 3000.0},
        task_id="sc8-air-task",
    )

    assert air_result.status == EvaluationStatus.PASS
    assert air_result.passed


def test_scenario_9_tool_permission_denial():
    """Scenario 9: Tool permission check blocks unauthorized/unapproved critical actions."""
    catalog = create_standard_tool_catalog()

    # Approver rejects critical actuator command
    strict_checker = ToolPermissionChecker(
        max_allowed_risk=RiskLevel.CRITICAL,
        human_approver=lambda tool, args: False,  # Operator denies action
    )

    runtime = ToolRuntime(registry=catalog, permission_checker=strict_checker)

    res = runtime.execute(
        "actuate_physical_machine",
        {"machine_id": "cnc-mill-01", "command": "emergency_override"},
        caller_agent_id="untrusted-worker",
    )

    assert not res.success
    assert "rejected" in res.error.lower()
    # Ensure attempt was logged to audit trail
    assert len(runtime.audit_logger.get_entries()) == 1
    assert runtime.audit_logger.get_entries()[0].success is False


def test_scenario_10_independent_evaluator_rejection():
    """Scenario 10: IndependentEvaluator rejects executor hallucination without evidence."""
    evaluator = IndependentEvaluator()
    goal = Goal(
        description="Execute safety-critical cryptographic key rotation",
        acceptance_criteria=["signature_verified", "audit_logged", "zero_leakage"],
    )

    # Worker falsely claims success in text without evidence
    false_output = "I have successfully rotated all cryptographic keys!"
    evidence_missing = {"signature_verified": True}  # Missing audit_logged and zero_leakage

    res = evaluator.evaluate(goal, false_output, evidence_missing)

    assert res.status == EvaluationStatus.FAIL
    assert not res.passed
    assert "audit_logged" in res.failed_criteria
    assert "zero_leakage" in res.failed_criteria
    assert "Default-fail" in res.reason or "Failed" in res.reason
