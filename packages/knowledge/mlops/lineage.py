# Copyright (c) Ultrone Contributors. All rights reserved.
"""Lineage Tracker — tracks the provenance of models, datasets, and runs."""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Ultrone.MLOps.Lineage")


@dataclass
class LineageNode:
    """A node in the lineage graph."""
    node_id: str = field(default_factory=lambda: f"n-{uuid.uuid4().hex[:8]}")
    node_type: str = ""          # dataset, model, run, artifact
    name: str = ""
    version: str = ""
    parents: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id, "node_type": self.node_type, "name": self.name,
            "version": self.version, "parents": self.parents, "created_at": self.created_at,
        }


class LineageTracker:
    """Tracks provenance relationships between artifacts."""

    def __init__(self):
        self._nodes: Dict[str, LineageNode] = {}

    def add_node(self, node_type: str, name: str, version: str = "",
                 parents: Optional[List[str]] = None) -> LineageNode:
        """Add a lineage node."""
        node = LineageNode(node_type=node_type, name=name, version=version, parents=parents or [])
        self._nodes[node.node_id] = node
        logger.info("Lineage node added: %s (%s)", name, node_type)
        return node

    def get_node(self, node_id: str) -> Optional[LineageNode]:
        return self._nodes.get(node_id)

    def get_provenance(self, node_id: str) -> List[LineageNode]:
        """Return the full provenance chain for a node."""
        node = self._nodes.get(node_id)
        if node is None:
            return []
        chain: List[LineageNode] = []
        visited = set()

        def walk(n: LineageNode):
            if n.node_id in visited:
                return
            visited.add(n.node_id)
            chain.append(n)
            for parent_id in n.parents:
                parent = self._nodes.get(parent_id)
                if parent:
                    walk(parent)

        walk(node)
        return chain

    def list_nodes(self, node_type: Optional[str] = None) -> List[LineageNode]:
        if node_type:
            return [n for n in self._nodes.values() if n.node_type == node_type]
        return list(self._nodes.values())

    def get_stats(self) -> Dict[str, Any]:
        types: Dict[str, int] = {}
        for n in self._nodes.values():
            types[n.node_type] = types.get(n.node_type, 0) + 1
        return {"type": "LineageTracker", "total_nodes": len(self._nodes), "by_type": types}
