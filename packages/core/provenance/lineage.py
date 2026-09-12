"""ULTRONE Core Provenance - Lineage tracking for entities, observations, and inferences."""
from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class LineageNode:
    """A node in the provenance / lineage graph."""
    node_id: str
    node_type: str  # 'sensor', 'raw_observation', 'fusion_model', 'reasoning_agent', 'inference'
    source_name: str
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    payload_hash: str = ""

    def __post_init__(self):
        if not self.payload_hash:
            raw = f"{self.node_id}:{self.node_type}:{self.source_name}:{self.timestamp}"
            self.payload_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "source_name": self.source_name,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
            "confidence": self.confidence,
            "payload_hash": self.payload_hash,
        }


class LineageGraph:
    """Directed acyclic graph tracking the lineage of data from ingestion to decision."""

    def __init__(self):
        self._nodes: Dict[str, LineageNode] = {}
        self._edges: List[tuple[str, str, str]] = []  # (parent_id, child_id, relation)

    def add_node(self, node: LineageNode) -> LineageNode:
        self._nodes[node.node_id] = node
        return node

    def add_edge(self, parent_id: str, child_id: str, relation: str = "derived_from") -> None:
        self._edges.append((parent_id, child_id, relation))

    def get_node(self, node_id: str) -> Optional[LineageNode]:
        return self._nodes.get(node_id)

    def get_parents(self, node_id: str) -> List[LineageNode]:
        parent_ids = [p for p, c, _ in self._edges if c == node_id]
        return [self._nodes[pid] for pid in parent_ids if pid in self._nodes]

    def get_children(self, node_id: str) -> List[LineageNode]:
        child_ids = [c for p, c, _ in self._edges if p == node_id]
        return [self._nodes[cid] for cid in child_ids if cid in self._nodes]

    def trace_lineage(self, node_id: str) -> List[Dict[str, Any]]:
        """Return upstream lineage path up to raw sensor ingestion."""
        trace = []
        visited = set()
        queue = [node_id]

        while queue:
            curr = queue.pop(0)
            if curr in visited or curr not in self._nodes:
                continue
            visited.add(curr)
            node = self._nodes[curr]
            trace.append(node.to_dict())
            for p, c, _ in self._edges:
                if c == curr and p not in visited:
                    queue.append(p)

        return trace

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes": [n.to_dict() for n in self._nodes.values()],
            "edges": [{"from": p, "to": c, "relation": r} for p, c, r in self._edges],
        }
