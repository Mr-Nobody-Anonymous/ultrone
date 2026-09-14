# Copyright (c) Ultrone Contributors. All rights reserved.
import time

from packages.agents.liveness import (
    HealthStatus,
    HeartbeatRecord,
    LivenessRegistry,
    LivenessWatchdog,
)


def test_heartbeat_status_classification():
    record = HeartbeatRecord(
        agent_id="agent-01",
        task_id="task-01",
        state="EXECUTING",
        last_beat=1000.0,
    )

    # Within 30s -> HEALTHY
    assert record.compute_status(now=1010.0) == HealthStatus.HEALTHY

    # Between 30s and 120s -> SUSPECT
    assert record.compute_status(now=1045.0) == HealthStatus.SUSPECT

    # Over 120s -> STALLED
    assert record.compute_status(now=1150.0) == HealthStatus.STALLED


def test_liveness_registry_and_watchdog_recovery():
    registry = LivenessRegistry()
    recovered_agents = []

    def on_stalled(record):
        recovered_agents.append(record.agent_id)

    watchdog = LivenessWatchdog(registry=registry, recovery_callback=on_stalled)

    # Register healthy agent
    registry.record_heartbeat("agent-live", "task-live", now=2000.0)

    # Register stalled agent (beat recorded 150s ago)
    registry.record_heartbeat("agent-stuck", "task-stuck", now=1850.0)

    # Sweep at now=2000.0
    stalled = watchdog.check_and_recover(now=2000.0)

    assert len(stalled) == 1
    assert stalled[0].agent_id == "agent-stuck"
    assert "agent-stuck" in recovered_agents
    assert registry.get_status("agent-live", now=2000.0) == HealthStatus.HEALTHY
