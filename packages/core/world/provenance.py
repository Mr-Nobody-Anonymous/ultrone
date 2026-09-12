# Copyright (c) Ultrone Contributors. All rights reserved.
"""Provenance graph and decision trail tracking for explainable trust."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ProvenanceRecord:
    """A record representing one node in the derivation graph."""
    record_id: str
    source_type: str             # 'sensor', 'model', 'fusion', 'human', 'simulation'
    source_id: str
    description: str
    model_name: Optional[str] = None
    confidence: float = 1.0
    timestamp: float = field(default_factory=time.time)
    parent_ids: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ProvenanceTracker:
    """Manages lineage graph across sensory ingest, AI reasoning, and human actions."""

    def __init__(self) -> None:
        self._records: Dict[str, ProvenanceRecord] = {}

    def record(self, rec: ProvenanceRecord) -> None:
        self._records[rec.record_id] = rec

    def get_lineage(self, record_id: str) -> List[ProvenanceRecord]:
        """Traverse ancestors back to raw sensory ingest."""
        chain: List[ProvenanceRecord] = []
        curr = self._records.get(record_id)
        while curr:
            chain.append(curr)
            curr = self._records.get(curr.parent_ids[0]) if curr.parent_ids else None
        return chain
