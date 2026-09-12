# Copyright (c) Ultrone Contributors. All rights reserved.
"""Temporal state management for historical replay and digital twin."""
from __future__ import annotations

import time
from typing import Dict, List, Optional
from packages.core.world.world_snapshot import WorldSnapshot


class TemporalStateManager:
    """Maintains time-series snapshots for scrubbing, replaying, and simulation."""

    def __init__(self, max_snapshots: int = 1000) -> None:
        self._snapshots: List[WorldSnapshot] = []
        self._max = max_snapshots

    def record_snapshot(self, snapshot: WorldSnapshot) -> None:
        self._snapshots.append(snapshot)
        if len(self._snapshots) > self._max:
            self._snapshots.pop(0)

    def get_snapshot_at(self, timestamp: float) -> Optional[WorldSnapshot]:
        """Find the closest snapshot at or before the given timestamp."""
        best: Optional[WorldSnapshot] = None
        for s in self._snapshots:
            if s.timestamp <= timestamp:
                best = s
            else:
                break
        return best or (self._snapshots[0] if self._snapshots else None)

    def count(self) -> int:
        return len(self._snapshots)
