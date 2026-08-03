# Copyright (c) Ultrone Contributors. All rights reserved.
"""Knowledge graph for the ULTRONE autonomous research platform.

Provides typed nodes and edges with versioning, timestamps, source
attribution, confidence scoring, graph traversal, and cross-reference
discovery. Extends (never replaces) the existing knowledge memory layers.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

logger = logging.getLogger("Ultrone.KnowledgeEngine.KnowledgeGraph")


class NodeType(Enum):
    """Typed nodes in the knowledge graph."""

    PAPER = "paper"
    AUTHOR = "author"
    ALGORITHM = "algorithm"
    ARCHITECTURE = "architecture"
    DATASET = "dataset"
    METRIC = "metric"
    METHOD = "method"
    CONCEPT = "concept"
    ENTITY = "entity"
    EXPERIMENT = "experiment"
    BENCHMARK = "benchmark"
    REPOSITORY = "repository"
    CONFERENCE = "conference"
    IMPLEMENTATION = "implementation"
    HYPOTHESIS = "hypothesis"


class EdgeType(Enum):
    """Typed edges between knowledge graph nodes."""

    CITES = "cites"
    AUTHORS = "authors"
    USES = "uses"
    EVALUATES = "evaluates"
    IMPLEMENTS = "implements"
    EXTENDS = "extends"
    RELATES_TO = "relates_to"
    IMPROVES = "improves"
    OUTPERFORMS = "outperforms"
    DEPENDS_ON = "depends_on"
    DERIVED_FROM = "derived_from"


@dataclass
class KnowledgeNode:
    """A node in the knowledge graph."""

    node_id: str = field(default_factory=lambda: f"N-{uuid.uuid4().hex[:12]}")
    label: str = ""
    node_type: NodeType = NodeType.CONCEPT
    properties: Dict[str, Any] = field(default_factory=dict)
    source: str = "unknown"
    confidence_score: float = 0.5
    version: int = 1
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "label": self.label,
            "node_type": self.node_type.value,
            "properties": self.properties,
            "source": self.source,
            "confidence_score": self.confidence_score,
            "version": self.version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KnowledgeNode":
        return cls(
            node_id=data.get("node_id", f"N-{uuid.uuid4().hex[:12]}"),
            label=data.get("label", ""),
            node_type=NodeType(data.get("node_type", "concept")),
            properties=data.get("properties", {}),
            source=data.get("source", "unknown"),
            confidence_score=data.get("confidence_score", 0.5),
            version=data.get("version", 1),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
        )


@dataclass
class KnowledgeEdge:
    """A directed edge between two knowledge graph nodes."""

    edge_id: str = field(default_factory=lambda: f"E-{uuid.uuid4().hex[:12]}")
    source_id: str = ""
    target_id: str = ""
    edge_type: EdgeType = EdgeType.RELATES_TO
    properties: Dict[str, Any] = field(default_factory=dict)
    confidence_score: float = 0.5
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "edge_id": self.edge_id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "edge_type": self.edge_type.value,
            "properties": self.properties,
            "confidence_score": self.confidence_score,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KnowledgeEdge":
        return cls(
            edge_id=data.get("edge_id", f"E-{uuid.uuid4().hex[:12]}"),
            source_id=data.get("source_id", ""),
            target_id=data.get("target_id", ""),
            edge_type=EdgeType(data.get("edge_type", "relates_to")),
            properties=data.get("properties", {}),
            confidence_score=data.get("confidence_score", 0.5),
            created_at=data.get("created_at", time.time()),
        )


class KnowledgeGraph:
    """Typed, versioned, confidence-scored knowledge graph.

    Features
    --------
    - Typed nodes and edges
    - Version history per node
    - Source attribution
    - Confidence scoring
    - Graph traversal (BFS/DFS, neighbors, paths)
    - Cross-reference discovery
    - Serialization to dict / JSON
    """

    def __init__(self, name: str = "ultrone_knowledge_graph"):
        self.name = name
        self._nodes: Dict[str, KnowledgeNode] = {}
        self._edges: Dict[str, KnowledgeEdge] = {}
        self._adjacency: Dict[str, Set[str]] = {}
        self._node_history: Dict[str, List[KnowledgeNode]] = {}

    # ------------------------------------------------------------------
    # Node operations
    # ------------------------------------------------------------------
    def add_node(
        self,
        label: str,
        node_type: NodeType = NodeType.CONCEPT,
        properties: Optional[Dict[str, Any]] = None,
        source: str = "unknown",
        confidence_score: float = 0.5,
        node_id: Optional[str] = None,
    ) -> KnowledgeNode:
        """Add or update a node in the graph."""
        if node_id and node_id in self._nodes:
            existing = self._nodes[node_id]
            # Append to history before update
            self._node_history.setdefault(node_id, []).append(existing)
            existing.label = label
            existing.node_type = node_type
            existing.properties = properties or {}
            existing.source = source
            existing.confidence_score = confidence_score
            existing.version += 1
            existing.updated_at = time.time()
            return existing

        node = KnowledgeNode(
            label=label,
            node_type=node_type,
            properties=properties or {},
            source=source,
            confidence_score=confidence_score,
            node_id=node_id or f"N-{uuid.uuid4().hex[:12]}",
        )
        self._nodes[node.node_id] = node
        self._adjacency.setdefault(node.node_id, set())
        return node

    def get_node(self, node_id: str) -> Optional[KnowledgeNode]:
        return self._nodes.get(node_id)

    def lookup_node(self, label: str, node_type: Optional[NodeType] = None) -> Optional[KnowledgeNode]:
        """Find a node by exact label match (optionally filtered by type)."""
        for node in self._nodes.values():
            if node.label == label:
                if node_type is None or node.node_type == node_type:
                    return node
        return None

    def update_node(self, node_id: str, **kwargs: Any) -> Optional[KnowledgeNode]:
        """Update node properties. Returns None if node not found."""
        node = self._nodes.get(node_id)
        if node is None:
            return None
        self._node_history.setdefault(node_id, []).append(node)
        for key, value in kwargs.items():
            if hasattr(node, key):
                setattr(node, key, value)
        node.version += 1
        node.updated_at = time.time()
        return node

    def delete_node(self, node_id: str) -> bool:
        """Delete a node and its incident edges."""
        if node_id not in self._nodes:
            return False
        del self._nodes[node_id]
        # Remove edges connected to this node
        edge_ids = [eid for eid, e in self._edges.items() if e.source_id == node_id or e.target_id == node_id]
        for eid in edge_ids:
            del self._edges[eid]
        self._adjacency.pop(node_id, None)
        return True

    def get_node_history(self, node_id: str) -> List[KnowledgeNode]:
        """Return version history for a node."""
        return list(self._node_history.get(node_id, []))

    # ------------------------------------------------------------------
    # Edge operations
    # ------------------------------------------------------------------
    def add_edge(
        self,
        source_id: str,
        target_id: str,
        edge_type: EdgeType = EdgeType.RELATES_TO,
        properties: Optional[Dict[str, Any]] = None,
        confidence_score: float = 0.5,
    ) -> Optional[KnowledgeEdge]:
        """Add an edge between two existing nodes. Returns None if either node missing."""
        if source_id not in self._nodes or target_id not in self._nodes:
            logger.warning(
                "Cannot add edge: missing node source=%s target=%s",
                source_id,
                target_id,
            )
            return None
        edge = KnowledgeEdge(
            source_id=source_id,
            target_id=target_id,
            edge_type=edge_type,
            properties=properties or {},
            confidence_score=confidence_score,
        )
        self._edges[edge.edge_id] = edge
        self._adjacency.setdefault(source_id, set()).add(target_id)
        return edge

    def get_edge(self, edge_id: str) -> Optional[KnowledgeEdge]:
        return self._edges.get(edge_id)

    def remove_edge(self, edge_id: str) -> bool:
        """Remove an edge. Returns True if removed."""
        edge = self._edges.pop(edge_id, None)
        if edge is None:
            return False
        self._adjacency.get(edge.source_id, set()).discard(edge.target_id)
        return True

    def get_edges(self, node_id: Optional[str] = None) -> List[KnowledgeEdge]:
        """Return edges optionally filtered by incident node."""
        if node_id is None:
            return list(self._edges.values())
        return [e for e in self._edges.values() if e.source_id == node_id or e.target_id == node_id]

    # ------------------------------------------------------------------
    # Traversal
    # ------------------------------------------------------------------
    def neighbors(self, node_id: str, edge_type: Optional[EdgeType] = None) -> List[str]:
        """Return neighbor node IDs (optionally filtered by edge type)."""
        result = []
        for e in self._edges.values():
            if e.source_id != node_id and e.target_id != node_id:
                continue
            if edge_type is not None and e.edge_type != edge_type:
                continue
            other = e.target_id if e.source_id == node_id else e.source_id
            result.append(other)
        return result

    def bfs(self, start_id: str, max_depth: int = 3) -> List[Tuple[str, int]]:
        """Breadth-first search from a node. Returns (node_id, depth) tuples."""
        if start_id not in self._nodes:
            return []
        visited: Set[str] = {start_id}
        queue: List[Tuple[str, int]] = [(start_id, 0)]
        results: List[Tuple[str, int]] = [(start_id, 0)]
        while queue:
            current, depth = queue.pop(0)
            if depth >= max_depth:
                continue
            for nbr in self.neighbors(current):
                if nbr not in visited:
                    visited.add(nbr)
                    queue.append((nbr, depth + 1))
                    results.append((nbr, depth + 1))
        return results

    def dfs(self, start_id: str, max_depth: int = 5) -> List[str]:
        """Depth-first search from a node. Returns visited node IDs."""
        if start_id not in self._nodes:
            return []
        visited: Set[str] = set()

        def _dfs(cur: str, depth: int) -> None:
            if depth > max_depth or cur in visited:
                return
            visited.add(cur)
            for nbr in self.neighbors(cur):
                _dfs(nbr, depth + 1)

        _dfs(start_id, 0)
        return list(visited)

    def find_path(self, start_id: str, end_id: str) -> Optional[List[str]]:
        """BFS-based shortest path. Returns list of node IDs or None."""
        if start_id not in self._nodes or end_id not in self._nodes:
            return None
        if start_id == end_id:
            return [start_id]
        queue: List[str] = [start_id]
        parent: Dict[str, Optional[str]] = {start_id: None}
        visited: Set[str] = {start_id}
        while queue:
            cur = queue.pop(0)
            for nbr in self.neighbors(cur):
                if nbr not in visited:
                    visited.add(nbr)
                    parent[nbr] = cur
                    if nbr == end_id:
                        # Reconstruct path
                        path = [nbr]
                        while parent[path[-1]] is not None:
                            path.append(parent[path[-1]])
                        path.reverse()
                        return path
                    queue.append(nbr)
        return None

    def subgraph(self, node_ids: Iterable[str]) -> "KnowledgeGraph":
        """Extract a subgraph containing only the specified nodes and edges between them."""
        ids = set(node_ids)
        sub = KnowledgeGraph(name=f"{self.name}_subgraph")
        for nid in ids:
            node = self._nodes.get(nid)
            if node:
                sub._nodes[nid] = node
        for e in self._edges.values():
            if e.source_id in ids and e.target_id in ids:
                sub._edges[e.edge_id] = e
        return sub

    # ------------------------------------------------------------------
    # Cross-reference discovery
    # ------------------------------------------------------------------
    def find_related(self, node_id: str, min_confidence: float = 0.0) -> List[KnowledgeNode]:
        """Find related nodes through shared neighbors (2-hop)."""
        if node_id not in self._nodes:
            return []
        direct = set(self.neighbors(node_id))
        related: Dict[str, float] = {}
        for nbr in direct:
            for nbr2 in self.neighbors(nbr):
                if nbr2 == node_id or nbr2 in direct:
                    continue
                # Score based on shared neighbors
                related[nbr2] = related.get(nbr2, 0.0) + 1.0
        # Normalize and filter by confidence
        result = []
        for nid, score in related.items():
            node = self._nodes.get(nid)
            if node and node.confidence_score >= min_confidence:
                # Normalize score to 0..1
                result.append(node)
        result.sort(key=lambda n: n.confidence_score, reverse=True)
        return result

    # ------------------------------------------------------------------
    # Statistics & serialization
    # ------------------------------------------------------------------
    def count_nodes(self) -> int:
        return len(self._nodes)

    def count_edges(self) -> int:
        return len(self._edges)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "type": "KnowledgeGraph",
            "name": self.name,
            "nodes": len(self._nodes),
            "edges": len(self._edges),
            "node_types": self._count_node_types(),
            "edge_types": self._count_edge_types(),
        }

    def _count_node_types(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for node in self._nodes.values():
            counts[node.node_type.value] = counts.get(node.node_type.value, 0) + 1
        return counts

    def _count_edge_types(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for e in self._edges.values():
            counts[e.edge_type.value] = counts.get(e.edge_type.value, 0) + 1
        return counts

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "nodes": [n.to_dict() for n in self._nodes.values()],
            "edges": [e.to_dict() for e in self._edges.values()],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KnowledgeGraph":
        graph = cls(name=data.get("name", "ultrone_knowledge_graph"))
        for nd in data.get("nodes", []):
            node = KnowledgeNode.from_dict(nd)
            graph._nodes[node.node_id] = node
            graph._adjacency.setdefault(node.node_id, set())
        for ed in data.get("edges", []):
            edge = KnowledgeEdge.from_dict(ed)
            graph._edges[edge.edge_id] = edge
            graph._adjacency.setdefault(edge.source_id, set()).add(edge.target_id)
        return graph
