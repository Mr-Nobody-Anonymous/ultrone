# Copyright (c) Ultrone Contributors. All rights reserved.
"""Ontology engine for the ULTRONE autonomous research platform.

Provides a lightweight ontology with concept hierarchies, relationships,
synonyms, and inference for the knowledge graph. Supports semantic typing
of knowledge entries and cross-concept discovery.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("Ultrone.KnowledgeEngine.Ontology")


@dataclass
class OntologyConcept:
    """A concept in the ontology."""

    concept_id: str = field(default_factory=lambda: f"C-{uuid.uuid4().hex[:12]}")
    name: str = ""
    description: str = ""
    parent_id: Optional[str] = None
    aliases: List[str] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "concept_id": self.concept_id,
            "name": self.name,
            "description": self.description,
            "parent_id": self.parent_id,
            "aliases": self.aliases,
            "properties": self.properties,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OntologyConcept":
        return cls(
            concept_id=data.get("concept_id", f"C-{uuid.uuid4().hex[:12]}"),
            name=data.get("name", ""),
            description=data.get("description", ""),
            parent_id=data.get("parent_id"),
            aliases=data.get("aliases", []),
            properties=data.get("properties", {}),
            created_at=data.get("created_at", time.time()),
        )


class OntologyEngine:
    """Concept hierarchy with aliases, relationships, and inference.

    Features
    --------
    - Concept hierarchy (parent/child)
    - Alias resolution
    - Concept relationships
    - Subsumption / ancestor reasoning
    - Similarity computation between concepts
    """

    def __init__(self, name: str = "ultrone_ontology"):
        self.name = name
        self._concepts: Dict[str, OntologyConcept] = {}
        self._by_name: Dict[str, str] = {}  # name/alias -> concept_id
        self._relationships: Dict[Tuple[str, str], str] = {}  # (src, dst) -> rel_type

    # ------------------------------------------------------------------
    # Concept management
    # ------------------------------------------------------------------
    def add_concept(
        self,
        name: str,
        description: str = "",
        parent_id: Optional[str] = None,
        aliases: Optional[List[str]] = None,
        properties: Optional[Dict[str, Any]] = None,
        concept_id: Optional[str] = None,
    ) -> OntologyConcept:
        """Add a concept. If name exists, returns existing concept."""
        existing = self._by_name.get(name.lower())
        if existing:
            return self._concepts[existing]

        if parent_id and parent_id not in self._concepts:
            logger.warning("Parent concept %s not found; adding anyway", parent_id)

        concept = OntologyConcept(
            concept_id=concept_id or f"C-{uuid.uuid4().hex[:12]}",
            name=name,
            description=description,
            parent_id=parent_id,
            aliases=aliases or [],
            properties=properties or {},
        )
        self._concepts[concept.concept_id] = concept
        self._by_name[name.lower()] = concept.concept_id
        for alias in concept.aliases:
            self._by_name[alias.lower()] = concept.concept_id
        return concept

    def get_concept(self, concept_id: str) -> Optional[OntologyConcept]:
        return self._concepts.get(concept_id)

    def lookup(self, name: str) -> Optional[OntologyConcept]:
        """Find concept by name or alias (case-insensitive)."""
        # Normalize: underscores -> spaces, strip
        normalized = name.strip().lower().replace("_", " ")
        cid = self._by_name.get(normalized)
        if cid:
            return self._concepts.get(cid)
        # Also check the original (with underscores) key
        cid = self._by_name.get(name.lower())
        if cid:
            return self._concepts.get(cid)
        # Fuzzy: prefix match
        for key, cid in self._by_name.items():
            if normalized in key or key in normalized:
                return self._concepts.get(cid)
        return None

    def add_relationship(self, source_id: str, target_id: str, rel_type: str = "related") -> bool:
        """Add a relationship between two concepts."""
        if source_id not in self._concepts or target_id not in self._concepts:
            logger.warning("Cannot add relationship: missing concept(s)")
            return False
        self._relationships[(source_id, target_id)] = rel_type
        return True

    def get_relationships(self, concept_id: str) -> List[Dict[str, str]]:
        """Return relationships for a concept."""
        result = []
        for (src, dst), rel in self._relationships.items():
            if src == concept_id:
                result.append({"source": src, "target": dst, "type": rel})
            elif dst == concept_id:
                result.append({"source": src, "target": dst, "type": rel})
        return result

    # ------------------------------------------------------------------
    # Hierarchy & inference
    # ------------------------------------------------------------------
    def ancestors(self, concept_id: str) -> List[OntologyConcept]:
        """Return all ancestor concepts (parents, grandparents, ...)."""
        result = []
        visited: Set[str] = set()
        current = self._concepts.get(concept_id)
        while current is not None and current.parent_id and current.parent_id not in visited:
            visited.add(current.parent_id)
            parent = self._concepts.get(current.parent_id)
            if parent:
                result.append(parent)
                current = parent
            else:
                break
        return result

    def descendants(self, concept_id: str) -> List[OntologyConcept]:
        """Return all descendant concepts."""
        result = []
        for concept in self._concepts.values():
            if concept.parent_id == concept_id:
                result.append(concept)
                result.extend(self.descendants(concept.concept_id))
        return result

    def is_subconcept_of(self, child_id: str, ancestor_id: str) -> bool:
        """Check if child_id is a subconcept of ancestor_id."""
        return any(a.concept_id == ancestor_id for a in self.ancestors(child_id))

    def siblings(self, concept_id: str) -> List[OntologyConcept]:
        """Return sibling concepts (same parent)."""
        concept = self._concepts.get(concept_id)
        if concept is None or concept.parent_id is None:
            return []
        return [c for c in self._concepts.values() if c.parent_id == concept.parent_id and c.concept_id != concept_id]

    def most_specific_common_ancestor(self, id_a: str, id_b: str) -> Optional[OntologyConcept]:
        """Find the most specific common ancestor of two concepts."""
        anc_a = set(a.concept_id for a in self.ancestors(id_a))
        common = [a for a in self.ancestors(id_b) if a.concept_id in anc_a]
        if not common:
            return None
        # Most specific = deepest = farthest from root
        return common[-1]

    def similarity(self, id_a: str, id_b: str) -> float:
        """Compute concept similarity using path-based measure."""
        if id_a == id_b:
            return 1.0
        if id_a not in self._concepts or id_b not in self._concepts:
            return 0.0
        msca = self.most_specific_common_ancestor(id_a, id_b)
        if msca is None:
            return 0.0
        depth_a = len(self.ancestors(id_a))
        depth_b = len(self.ancestors(id_b))
        depth_msca = len(self.ancestors(msca.concept_id))
        # Path-based similarity: 2 * d(msca) / (d(a) + d(b))
        if depth_a + depth_b == 0:
            return 1.0
        return (2.0 * depth_msca) / (depth_a + depth_b)

    # ------------------------------------------------------------------
    # Classification
    # ------------------------------------------------------------------
    def classify_text(self, text: str) -> List[Tuple[OntologyConcept, float]]:
        """Classify text against ontology concepts using keyword overlap."""
        text_lower = text.lower()
        concepts_seen: Set[str] = set()
        scored: List[Tuple[OntologyConcept, float]] = []
        for key, cid in self._by_name.items():
            if key in text_lower and cid not in concepts_seen:
                concepts_seen.add(cid)
                concept = self._concepts[cid]
                # Score by length of matched key (longer = more specific)
                score = min(1.0, len(key) / 20.0)
                scored.append((concept, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:10]

    # ------------------------------------------------------------------
    # Serialization & stats
    # ------------------------------------------------------------------
    def get_stats(self) -> Dict[str, Any]:
        return {
            "type": "OntologyEngine",
            "name": self.name,
            "concepts": len(self._concepts),
            "relationships": len(self._relationships),
            "aliases": len(self._by_name) - len(self._concepts),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "concepts": [c.to_dict() for c in self._concepts.values()],
            "relationships": [
                {
                    "source": src,
                    "target": dst,
                    "type": rel,
                }
                for (src, dst), rel in self._relationships.items()
            ],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OntologyEngine":
        engine = cls(name=data.get("name", "ultrone_ontology"))
        for cd in data.get("concepts", []):
            concept = OntologyConcept.from_dict(cd)
            engine._concepts[concept.concept_id] = concept
            engine._by_name[concept.name.lower()] = concept.concept_id
            for alias in concept.aliases:
                engine._by_name[alias.lower()] = concept.concept_id
        for rel in data.get("relationships", []):
            engine._relationships[(rel["source"], rel["target"])] = rel["type"]
        return engine
