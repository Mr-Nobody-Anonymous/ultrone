# Copyright (c) Ultrone Contributors. All rights reserved.
"""Directed Acyclic Graph (TaskDAG) for F2T2EA Kill-Chain workflows."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class NodeStatus(str, Enum):
    """Execution status of a DAG task node."""

    PENDING = "PENDING"
    READY = "READY"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    SKIPPED = "SKIPPED"


@dataclass
class DAGNode:
    """A discrete task node in the execution DAG."""

    node_id: str
    phase: str  # FIND, FIX, TRACK, TARGET, ENGAGE, ASSESS
    description: str
    tool_name: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    prerequisites: List[str] = field(default_factory=list)  # Dependency node IDs
    acceptance_criteria: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    status: NodeStatus = NodeStatus.PENDING
    output: Optional[Any] = None
    evidence: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None

    @property
    def is_terminal(self) -> bool:
        return self.status in (NodeStatus.COMPLETED, NodeStatus.FAILED, NodeStatus.SKIPPED)


class TaskDAG:
    """Directed Acyclic Graph orchestrating multi-stage agent workflows."""

    def __init__(self, name: str = "f2t2ea-killchain-dag") -> None:
        self.name = name
        self.nodes: Dict[str, DAGNode] = {}
        self._execution_order: List[str] = []

    def add_node(self, node: DAGNode) -> None:
        """Add a task node and validate no circular dependencies are created."""
        if node.node_id in self.nodes:
            raise ValueError(f"Duplicate node_id '{node.node_id}' in DAG.")
        self.nodes[node.node_id] = node
        self._validate_acyclic()

    def get_node(self, node_id: str) -> Optional[DAGNode]:
        return self.nodes.get(node_id)

    def get_ready_nodes(self) -> List[DAGNode]:
        """Return nodes whose prerequisites are all COMPLETED and status is PENDING/READY."""
        ready: List[DAGNode] = []
        for node in self.nodes.values():
            if node.status in (NodeStatus.PENDING, NodeStatus.READY):
                prereqs_met = all(
                    self.nodes[prereq_id].status == NodeStatus.COMPLETED
                    for prereq_id in node.prerequisites
                    if prereq_id in self.nodes
                )
                if prereqs_met:
                    node.status = NodeStatus.READY
                    ready.append(node)
        return ready

    def mark_completed(self, node_id: str, output: Any, evidence: Optional[Dict[str, Any]] = None) -> None:
        node = self.nodes[node_id]
        node.status = NodeStatus.COMPLETED
        node.output = output
        node.evidence = evidence or {}
        node.completed_at = time.time()

    def mark_failed(self, node_id: str, error: str) -> None:
        node = self.nodes[node_id]
        node.status = NodeStatus.FAILED
        node.error = error
        node.completed_at = time.time()

        # Mark dependent downstream nodes as BLOCKED
        for other in self.nodes.values():
            if node_id in other.prerequisites and other.status == NodeStatus.PENDING:
                other.status = NodeStatus.BLOCKED

    def is_finished(self) -> bool:
        """True when all nodes are either COMPLETED, FAILED, or BLOCKED."""
        return all(node.is_terminal or node.status == NodeStatus.BLOCKED for node in self.nodes.values())

    def is_successful(self) -> bool:
        """True when all nodes reached COMPLETED status."""
        return len(self.nodes) > 0 and all(node.status == NodeStatus.COMPLETED for node in self.nodes.values())

    def _validate_acyclic(self) -> None:
        """Kahn's algorithm to detect cycles."""
        in_degree: Dict[str, int] = {nid: 0 for nid in self.nodes}
        for node in self.nodes.values():
            for p in node.prerequisites:
                if p in in_degree:
                    in_degree[node.node_id] += 1

        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        visited_count = 0

        while queue:
            curr = queue.pop(0)
            visited_count += 1
            for other in self.nodes.values():
                if curr in other.prerequisites:
                    in_degree[other.node_id] -= 1
                    if in_degree[other.node_id] == 0:
                        queue.append(other.node_id)

        if visited_count < len(self.nodes):
            raise ValueError("Cycle detected in TaskDAG specification.")
