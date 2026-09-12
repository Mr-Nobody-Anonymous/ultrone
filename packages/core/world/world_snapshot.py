# Copyright (c) Ultrone Contributors. All rights reserved.
"""Point-in-time state capture snapshots for replay and digital twin."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List
from packages.core.entities import Entity


@dataclass
class WorldSnapshot:
    """Immutable snapshot of the world model at a given timestamp."""
    snapshot_id: str
    timestamp: float = field(default_factory=time.time)
    entity_count: int = 0
    entities: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def capture(cls, entities: List[Entity], snapshot_id: str = "", metadata: Dict[str, Any] = None) -> WorldSnapshot:
        return cls(
            snapshot_id=snapshot_id or f"snap_{int(time.time() * 1000)}",
            timestamp=time.time(),
            entity_count=len(entities),
            entities=[e.to_dict() for e in entities],
            metadata=metadata or {},
        )
