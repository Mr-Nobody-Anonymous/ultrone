# Copyright (c) Ultrone Contributors. All rights reserved.
"""Liveness Watchdog detecting stalled agents and invoking recovery."""

from __future__ import annotations

import logging
import time
from typing import Callable, List, Optional

from .health import HeartbeatRecord
from .registry import LivenessRegistry

logger = logging.getLogger("Ultrone.Watchdog")


class LivenessWatchdog:
    """Monitors registry and triggers mitigation upon stall detection."""

    def __init__(
        self,
        registry: Optional[LivenessRegistry] = None,
        recovery_callback: Optional[Callable[[HeartbeatRecord], None]] = None,
    ) -> None:
        self.registry = registry or LivenessRegistry()
        self.recovery_callback = recovery_callback

    def check_and_recover(self, now: Optional[float] = None) -> List[HeartbeatRecord]:
        """Perform a single watchdog sweep and invoke recovery for stalled agents."""
        current_time = now or time.time()
        stalled = self.registry.get_stalled_agents(current_time)

        for record in stalled:
            logger.warning(
                "Agent %s stalled! Last beat was %.1fs ago on task %s",
                record.agent_id,
                current_time - record.last_beat,
                record.task_id,
            )
            if self.recovery_callback:
                try:
                    self.recovery_callback(record)
                except Exception as e:
                    logger.error("Error invoking recovery callback for %s: %s", record.agent_id, e)

        return stalled
