# Copyright (c) Ultrone Contributors. All rights reserved.
"""Liveness registry managing agent heartbeat records."""

from __future__ import annotations

import time
from typing import Dict, List, Optional

from .health import HealthStatus, HeartbeatRecord


class LivenessRegistry:
    """Central registry tracking active agent heartbeats."""

    def __init__(self) -> None:
        self._records: Dict[str, HeartbeatRecord] = {}

    def record_heartbeat(
        self,
        agent_id: str,
        task_id: str = "",
        state: str = "EXECUTING",
        metadata: Optional[Dict] = None,
        now: Optional[float] = None,
    ) -> HeartbeatRecord:
        """Register or update an agent heartbeat pulse."""
        ts = now if now is not None else time.time()
        record = HeartbeatRecord(
            agent_id=agent_id,
            task_id=task_id,
            state=state,
            last_beat=ts,
            metadata=metadata or {},
        )
        self._records[agent_id] = record
        return record

    def get_status(self, agent_id: str, now: Optional[float] = None) -> HealthStatus:
        """Query the health status of a specific agent."""
        record = self._records.get(agent_id)
        if not record:
            return HealthStatus.DEAD
        return record.compute_status(now or time.time())

    def get_stalled_agents(self, now: Optional[float] = None) -> List[HeartbeatRecord]:
        """Find all agents currently in STALLED status."""
        current_time = now or time.time()
        stalled: List[HeartbeatRecord] = []
        for record in self._records.values():
            if record.compute_status(current_time) == HealthStatus.STALLED:
                stalled.append(record)
        return stalled

    def deregister(self, agent_id: str) -> None:
        """Remove agent from monitoring upon graceful termination."""
        self._records.pop(agent_id, None)
