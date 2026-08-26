# Copyright (c) Ultrone Contributors. All rights reserved.
"""Bounded telemetry recording for subsystem-controlled platforms.

Two streams, both size-capped and deterministic:

- **command log** -- every :class:`~agents.commands.CommandResult` routed
  through the platform's CommandBus;
- **snapshot history** -- periodic unified platform states.

``export()`` returns a plain dict suitable for experiment checkpoints.
"""

from __future__ import annotations

from collections import deque
from typing import Any, Deque, Dict, List, Optional


class TelemetryRecorder:
    """Ring-buffer telemetry for one simulated platform."""

    def __init__(self, source_id: str = "",
                 snapshot_limit: int = 200,
                 command_limit: int = 500) -> None:
        self.source_id = source_id
        self._snapshots: Deque[Dict[str, Any]] = deque(maxlen=snapshot_limit)
        self._commands: Deque[Dict[str, Any]] = deque(maxlen=command_limit)

    # -- recording ------------------------------------------------------------ #
    def record_command(self, result, tick: Optional[int] = None) -> None:
        self._commands.append({
            "tick": tick,
            "subsystem": getattr(result, "subsystem", ""),
            "action": getattr(result, "action", ""),
            "success": bool(getattr(result, "success", False)),
            "reason": getattr(result, "reason", "") or "",
        })

    def record_snapshot(self, state: Dict[str, Any],
                        tick: Optional[int] = None) -> None:
        entry = dict(state)
        if tick is not None:
            entry["recorded_at"] = tick
        self._snapshots.append(entry)

    # -- access ---------------------------------------------------------------- #
    def commands(self) -> List[Dict[str, Any]]:
        return list(self._commands)

    def snapshots(self) -> List[Dict[str, Any]]:
        return list(self._snapshots)

    def latest(self) -> Optional[Dict[str, Any]]:
        return self._snapshots[-1] if self._snapshots else None

    def last_command(self) -> Optional[Dict[str, Any]]:
        return self._commands[-1] if self._commands else None

    # -- export ------------------------------------------------------------------ #
    def export(self) -> Dict[str, Any]:
        return {"source_id": self.source_id,
                "commands": self.commands(),
                "snapshots": self.snapshots()}
