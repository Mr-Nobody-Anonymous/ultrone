# Copyright (c) Ultrone Contributors. All rights reserved.
"""Scene graph construction and querying.

Builds and maintains a spatial-semantic graph of the observed world:

* nodes = tracked entities
* edges = typed relationships (spatial, semantic, causal)
* supports graph queries, subgraph extraction, and graph statistics
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Set

from .types import (
    EntityID,
    Relationship,
    TrackedEntity,
    Vector3,
)

__all__ = [
    "SceneGraph",
    "SceneGraphNode",
    "SceneGraphEdge",
    "SceneGraphStats",
]


@dataclass
class SceneGraphNode:
    """A node in the scene graph wrapping a tracked entity."""

    entity: TrackedEntity
    degree: int = 0
    centrality: float = 0.0


@dataclass
class SceneGraphEdge:
    """An edge in the scene graph wrapping a relationship."""

    relationship: Relationship
    weight: float = 1.0


@dataclass
class SceneGraphStats:
    """Statistics about the scene graph."""

    node_count: int = 0
    edge_count: int = 0
    connected_components: int = 0
    average_degree: float = 0.0
    density: float = 0.0


class SceneGraph:
    """Spatial-semantic graph over tracked entities and relationships."""

    def __init__(self) -> None:
        self._nodes: Dict[str, SceneGraphNode] = {}
        self._edges: Dict[str, SceneGraphEdge] = {}
        self._adjacency: Dict[str, Set[str]] = {}

    def add_entity(self, entity: TrackedEntity) -> SceneGraphNode:
        """Add or update an entity node."""
        key = str(entity.entity_id)
        node = self._nodes.get(key)
        if node is None:
            node = SceneGraphNode(entity=entity)
            self._nodes[key] = node
            self._adjacency.setdefault(key, set())
        else:
            node.entity = entity
        return node

    def add_relationship(self, relationship: Relationship) -> SceneGraphEdge:
        """Add or update a relationship edge."""
        key = relationship.relationship_id
        edge = self._edges.get(key)
        if edge is None:
            edge = SceneGraphEdge(relationship=relationship)
            self._edges[key] = edge
            src = str(relationship.source_id)
            tgt = str(relationship.target_id)
            self._adjacency.setdefault(src, set()).add(tgt)
            self._adjacency.setdefault(tgt, set()).add(src)
        else:
            edge.relationship = relationship
        return edge

    def remove_entity(self, entity_id: EntityID) -> bool:
        """Remove an entity node and its incident edges."""
        key = str(entity_id)
        if key not in self._nodes:
            return False
        self._nodes.pop(key)
        # Remove incident edges.
        to_remove = [
            eid
            for eid, edge in self._edges.items()
            if str(edge.relationship.source_id) == key
            or str(edge.relationship.target_id) == key
        ]
        for eid in to_remove:
            self._edges.pop(eid, None)
        self._adjacency.pop(key, None)
        for neighbors in self._adjacency.values():
            neighbors.discard(key)
        return True

    def remove_relationship(self, relationship_id: str) -> bool:
        """Remove a relationship edge."""
        edge = self._edges.pop(relationship_id, None)
        if edge is None:
            return False
        src = str(edge.relationship.source_id)
        tgt = str(edge.relationship.target_id)
        self._adjacency.get(src, set()).discard(tgt)
        self._adjacency.get(tgt, set()).discard(src)
        return True

    def get_entity(self, entity_id: EntityID) -> Optional[TrackedEntity]:
        node = self._nodes.get(str(entity_id))
        return node.entity if node else None

    def get_relationship(self, relationship_id: str) -> Optional[Relationship]:
        edge = self._edges.get(relationship_id)
        return edge.relationship if edge else None

    def neighbors(self, entity_id: EntityID) -> List[TrackedEntity]:
        """Return entities directly connected to the given entity."""
        key = str(entity_id)
        neighbor_ids = self._adjacency.get(key, set())
        result: List[TrackedEntity] = []
        for nid in neighbor_ids:
            node = self._nodes.get(nid)
            if node is not None:
                result.append(node.entity)
        return result

    def relationships_for(self, entity_id: EntityID) -> List[Relationship]:
        """Return all relationships incident to the given entity."""
        key = str(entity_id)
        return [
            edge.relationship
            for edge in self._edges.values()
            if str(edge.relationship.source_id) == key
            or str(edge.relationship.target_id) == key
        ]

    def subgraph(
        self, entity_ids: Sequence[EntityID]
    ) -> "SceneGraph":
        """Extract a subgraph containing only the given entities."""
        sub = SceneGraph()
        id_set = {str(eid) for eid in entity_ids}
        for key, node in self._nodes.items():
            if key in id_set:
                sub.add_entity(node.entity)
        for edge in self._edges.values():
            src = str(edge.relationship.source_id)
            tgt = str(edge.relationship.target_id)
            if src in id_set and tgt in id_set:
                sub.add_relationship(edge.relationship)
        return sub

    def entities_by_type(self, entity_type: Any) -> List[TrackedEntity]:
        return [
            node.entity
            for node in self._nodes.values()
            if node.entity.entity_type == entity_type
        ]

    def entities_by_category(self, category: Any) -> List[TrackedEntity]:
        return [
            node.entity
            for node in self._nodes.values()
            if node.entity.category == category
        ]

    def entities_in_radius(self, center: Vector3, radius: float) -> List[TrackedEntity]:
        return [
            node.entity
            for node in self._nodes.values()
            if node.entity.state.position.distance_to(center) <= radius
        ]

    def stats(self) -> SceneGraphStats:
        """Compute graph statistics."""
        n = len(self._nodes)
        m = len(self._edges)
        if n == 0:
            return SceneGraphStats()
        total_degree = sum(len(neighbors) for neighbors in self._adjacency.values())
        density = (2.0 * m) / (n * (n - 1)) if n > 1 else 0.0
        components = self._count_components()
        return SceneGraphStats(
            node_count=n,
            edge_count=m,
            connected_components=components,
            average_degree=total_degree / n,
            density=density,
        )

    def _count_components(self) -> int:
        """Count connected components via BFS."""
        visited: Set[str] = set()
        components = 0
        for key in self._nodes:
            if key in visited:
                continue
            components += 1
            stack = [key]
            while stack:
                current = stack.pop()
                if current in visited:
                    continue
                visited.add(current)
                stack.extend(self._adjacency.get(current, set()))
        return components

    def node_count(self) -> int:
        return len(self._nodes)

    def edge_count(self) -> int:
        return len(self._edges)

    def clear(self) -> None:
        self._nodes.clear()
        self._edges.clear()
        self._adjacency.clear()