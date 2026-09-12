# Copyright (c) Ultrone Contributors. All rights reserved.
"""Reasoning graph for visualizing decision chains.

Builds a directed graph of the decision-making process, showing how
inputs flow through perception, reasoning, and action selection.
Nodes represent processing steps; edges represent information flow.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("Ultrone.Brain.XAI.ReasoningGraph")


@dataclass
class ReasoningNode:
    """A single node in the reasoning graph.

    Attributes
    ----------
    node_id:
        Unique identifier.
    label:
        Human-readable label (e.g. "Threat Assessment", "COA Selection").
    node_type:
        One of "perception", "reasoning", "decision", "action", "memory", "observation".
    confidence:
        Confidence score for this node's output (0-1).
    inputs:
        Input node IDs.
    outputs:
        Output node IDs.
    metadata:
        Arbitrary key-value pairs for additional context.
    """
    node_id: str
    label: str
    node_type: str = "reasoning"
    confidence: float = 1.0
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class ReasoningEdge:
    """A directed edge between reasoning nodes.

    Attributes
    ----------
    source:
        Source node ID.
    target:
        Target node ID.
    label:
        Edge label (e.g. "influences", "contradicts", "supports").
    weight:
        Edge weight / importance.
    """
    source: str
    target: str
    label: str = "influences"
    weight: float = 1.0


class ReasoningGraph:
    """Builds and manages a directed graph of the decision-making process.

    The graph can be exported to various formats for visualization
    (e.g., Graphviz DOT, networkx, JSON).

    Integration
    -----------
    Used by :class:`~brain.xai.decision_trace.DecisionTrace` to enrich
    step explanations with graph context. Exposed via the XAI API
    for human-in-the-loop analysis.
    """

    def __init__(self):
        self._nodes: Dict[str, ReasoningNode] = {}
        self._edges: List[ReasoningEdge] = []
        self._counter: int = 0

    def add_node(
        self,
        label: str,
        node_type: str = "reasoning",
        confidence: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Add a reasoning step node.

        Returns the auto-generated node ID.
        """
        node_id = f"node_{self._counter}"
        self._counter += 1
        self._nodes[node_id] = ReasoningNode(
            node_id=node_id,
            label=label,
            node_type=node_type,
            confidence=confidence,
            metadata=metadata or {},
        )
        return node_id

    def add_edge(
        self,
        source: str,
        target: str,
        label: str = "influences",
        weight: float = 1.0,
    ) -> None:
        """Add a directed edge between two nodes.."""
        if source not in self._nodes:
            logger.warning("add_edge: source '%s' not found", source)
            return
        if target not in self._nodes:
            logger.warning("add_edge: target '%s' not found", target)
            return
        self._edges.append(ReasoningEdge(source, target, label, weight))
        self._nodes[source].outputs.append(target)
        self._nodes[target].inputs.append(source)

    def build_from_trace(self, trace_data: List[Dict[str, Any]]) -> str:
        """Build a reasoning graph from a decision trace.

        Parameters
        ----------
        trace_data:
            List of trace steps from :class:`~brain.xai.decision_trace.DecisionTrace`.

        Returns
        -------
        str
            The root node ID.
        """
        root_id = None
        prev_id = None
        for step in trace_data:
            step_id = step.get("step_id", self._counter)
            label = step.get("action", "unknown")
            node_id = self.add_node(
                label=f"Step {step_id}: {label}",
                node_type="decision",
                confidence=step.get("confidence", 1.0),
                metadata={"reasoning": step.get("reasoning", "")},
            )
            if prev_id is not None:
                self.add_edge(prev_id, node_id, label="leads_to")
            if root_id is None:
                root_id = node_id
            prev_id = node_id
            # Add alternatives as sibling nodes
            for alt in step.get("alternatives", []):
                alt_id = self.add_node(
                    label=f"Alternative: {alt}",
                    node_type="decision",
                    confidence=0.0,
                )
                self.add_edge(node_id, alt_id, label="alternative_to", weight=0.3)
        return root_id or ""

    def to_dict(self) -> Dict[str, Any]:
        """Export the graph as a serializable dictionary."""
        return {
            "nodes": {nid: {
                "id": nid,
                "label": node.label,
                "type": node.node_type,
                "confidence": node.confidence,
                "inputs": node.inputs,
                "outputs": node.outputs,
                "metadata": node.metadata,
            } for nid, node in self._nodes.items()},
            "edges": [
                {"source": e.source, "target": e.target, "label": e.label, "weight": e.weight}
                for e in self._edges
            ],
        }

    def to_dot(self) -> str:
        """Export as Graphviz DOT format string."""
        lines = ["digraph ReasoningGraph {"]
        lines.append("  rankdir=LR;")
        lines.append('  node [shape=box, style="rounded,filled", fillcolor=lightyellow];')
        for nid, node in self._nodes.items():
            color = self._node_color(node.node_type)
            lines.append(f'  {nid} [label="{node.label}", fillcolor={color}];')
        for edge in self._edges:
            lines.append(f'  {edge.source} -> {edge.target} [label="{edge.label}"];')
        lines.append("}")
        return "\n".join(lines)

    def to_networkx(self) -> Any:
        """Export as a networkx graph (if networkx is available)."""
        try:
            import networkx as nx
            G = nx.DiGraph()
            for nid, node in self._nodes.items():
                G.add_node(nid, label=node.label, type=node.node_type, confidence=node.confidence)
            for edge in self._edges:
                G.add_edge(edge.source, edge.target, label=edge.label, weight=edge.weight)
            return G
        except ImportError:
            logger.warning("networkx not available — cannot export to networkx.")
            return None

    def get_stats(self) -> Dict[str, Any]:
        return {
            "type": "ReasoningGraph",
            "num_nodes": len(self._nodes),
            "num_edges": len(self._edges),
        }

    @staticmethod
    def _node_color(node_type: str) -> str:
        colors = {
            "perception": "lightskyblue",
            "reasoning": "lightyellow",
            "decision": "lightgreen",
            "action": "lightcoral",
            "memory": "plum",
            "observation": "wheat",
        }
        return colors.get(node_type, "lightgrey")

    def build(self, decision_data: Dict[str, Any]) -> str:
        """Build a reasoning graph from a decision dictionary.

        Args:
            decision_data: Dict with keys such as ``action``, ``reason``,
                ``step_id``, ``alternatives``, ``confidence``.

        Returns:
            Root node ID of the built graph.
        """
        self.clear()
        root_id = self.add_node(
            label="Decision: " + str(decision_data.get('action', 'unknown')),
            node_type="decision",
            confidence=decision_data.get("confidence", 1.0),
            metadata={"reason": decision_data.get("reason", "")},
        )
        step_id = decision_data.get("step_id", 0)
        perception_id = self.add_node(
            label="Observation " + str(step_id),
            node_type="observation",
            confidence=decision_data.get("confidence", 0.8),
        )
        self.add_edge(perception_id, root_id, label="informs")

        for alt in decision_data.get("alternatives", []):
            alt_id = self.add_node(
                label="Alternative: " + str(alt),
                node_type="decision",
                confidence=0.0,
            )
            self.add_edge(root_id, alt_id, label="alternative_to", weight=0.3)
        return root_id

    def clear(self) -> None:
        """Reset the graph."""
        self._nodes.clear()
        self._edges.clear()
        self._counter = 0

