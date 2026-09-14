# Copyright (c) Ultrone Contributors. All rights reserved.
"""Liveness and health definitions for autonomous agents."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict


class HealthStatus(str, Enum):
    """Health classification based on heartbeat latency."""

    HEALTHY = "HEALTHY"    # 0 - 30s
    SUSPECT = "SUSPECT"    # 30 - 120s
    STALLED = "STALLED"    # > 120s
    DEAD = "DEAD"          # Explicitly terminated or unreachable


@dataclass
class HeartbeatRecord:
    """Telemetry captured from an agent heartbeat pulse."""

    agent_id: str
    task_id: str
    state: str
    last_beat: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    suspect_threshold_sec: float = 30.0
    stalled_threshold_sec: float = 120.0

    def compute_status(self, now: float = 0.0) -> HealthStatus:
        """Compute current health status based on time elapsed since last beat."""
        current_time = now if now > 0 else time.time()
        elapsed = current_time - self.last_beat

        if elapsed <= self.suspect_threshold_sec:
            return HealthStatus.HEALTHY
        elif elapsed <= self.stalled_threshold_sec:
            return HealthStatus.SUSPECT
        else:
            return HealthStatus.STALLED
