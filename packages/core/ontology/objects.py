# Copyright (c) Ultrone Contributors. All rights reserved.
"""Palantir-inspired Ontology primitives for ULTRONE.

Structures operational applications around:
- Objects: Structured real-world or synthetic entities
- Links: Relationships connecting objects
- Actions: Parameterized workflows and operations
- Functions: Derived calculations and analytic evaluations
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class OntologyLink:
    """Directed, typed relationship connecting two ontology objects."""
    source_id: str
    target_id: str
    relation_type: str       # e.g., 'observes', 'communicates_with', 'located_in', 'protects'
    confidence: float = 1.0
    properties: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


@dataclass
class OntologyAction:
    """Action workflow that can be executed against one or more objects."""
    action_id: str
    name: str
    description: str
    target_object_types: List[str]
    handler: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the action with parameters."""
        if self.handler:
            return self.handler(params)
        return {
            "status": "executed",
            "action_id": self.action_id,
            "timestamp": time.time(),
            "params": params,
        }


@dataclass
class OntologyObject:
    """First-class semantic object in the ULTRONE platform."""
    object_id: str
    object_type: str
    properties: Dict[str, Any] = field(default_factory=dict)
    links: List[OntologyLink] = field(default_factory=list)
    available_actions: List[str] = field(default_factory=list)
    confidence: float = 1.0
    last_updated: float = field(default_factory=time.time)

    def add_link(self, target_id: str, relation_type: str, confidence: float = 1.0) -> None:
        """Add a typed link to another object."""
        self.links.append(OntologyLink(
            source_id=self.object_id,
            target_id=target_id,
            relation_type=relation_type,
            confidence=confidence,
        ))
        self.last_updated = time.time()
