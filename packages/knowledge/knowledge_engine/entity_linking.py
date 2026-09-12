# Copyright (c) Ultrone Contributors. All rights reserved.
"""Entity linking for the ULTRONE autonomous research platform.

Resolves mentions in text to ontology concepts and knowledge graph entities.
Supports alias-based matching, context scoring, and confidence estimation.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set, Tuple

from .base import KnowledgeEntry
from .ontology import OntologyEngine

logger = logging.getLogger("Ultrone.KnowledgeEngine.EntityLinking")


class EntityLinker:
    """Links text mentions to ontology concepts / knowledge graph entities.

    Features
    --------
    - Alias-based mention resolution
    - Context scoring
    - Confidence estimation
    - Batch linking
    """

    def __init__(self, ontology: Optional[OntologyEngine] = None):
        self.ontology = ontology or OntologyEngine()
        self._entity_aliases: Dict[str, Set[str]] = {}  # entity_id -> aliases

    # ------------------------------------------------------------------
    # Entity registration
    # ------------------------------------------------------------------
    def register_entity(
        self,
        entity_id: str,
        name: str,
        aliases: Optional[List[str]] = None,
    ) -> None:
        """Register a knowledge graph entity with aliases for linking."""
        self._entity_aliases.setdefault(entity_id, set()).add(name.lower())
        for alias in aliases or []:
            self._entity_aliases[entity_id].add(alias.lower())

    def register_entities_from_entries(self, entries: List[KnowledgeEntry]) -> None:
        """Register entities from knowledge entries."""
        for entry in entries:
            for entity in entry.entities:
                self._entity_aliases.setdefault(entity, set()).add(entity.lower())

    # ------------------------------------------------------------------
    # Linking
    # ------------------------------------------------------------------
    def link_text(self, text: str) -> List[Tuple[str, float, str]]:
        """Link mentions in text to entities.

        Returns list of (entity_id, confidence, matched_text) tuples.
        """
        text_lower = text.lower()
        results: List[Tuple[str, float, str]] = []
        seen: Set[str] = set()

        # Match ontology concepts
        for concept in self.ontology._concepts.values():
            for name in [concept.name] + concept.aliases:
                if name.lower() in text_lower and concept.concept_id not in seen:
                    seen.add(concept.concept_id)
                    confidence = min(1.0, len(name) / 15.0)
                    results.append((concept.concept_id, confidence, name))
                    break

        # Match registered entities
        for entity_id, aliases in self._entity_aliases.items():
            for alias in aliases:
                if alias and alias in text_lower and entity_id not in seen:
                    seen.add(entity_id)
                    confidence = min(1.0, len(alias) / 15.0)
                    results.append((entity_id, confidence, alias))
                    break

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:20]

    def link_entries(self, entries: List[KnowledgeEntry]) -> Dict[str, List[str]]:
        """Link all entities in knowledge entries.

        Returns dict: entry_id -> list of linked entity IDs.
        """
        result: Dict[str, List[str]] = {}
        for entry in entries:
            text = f"{entry.content} {' '.join(entry.tags)}"
            linked = self.link_text(text)
            result[entry.entry_id] = [eid for eid, _, _ in linked]
        return result

    def disambiguate(self, mention: str, context: str = "") -> Optional[Tuple[str, float]]:
        """Resolve a single mention with optional context to best entity."""
        candidates = self.link_text(mention + " " + context)
        if not candidates:
            return None
        best = candidates[0]
        return best[0], best[1]

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------
    def get_stats(self) -> Dict[str, Any]:
        return {
            "type": "EntityLinker",
            "ontology_concepts": len(self.ontology._concepts),
            "registered_entities": len(self._entity_aliases),
            "total_aliases": sum(len(a) for a in self._entity_aliases.values()),
        }
