# Copyright (c) Ultrone Contributors. All rights reserved.
"""Knowledge consolidation for the ULTRONE autonomous research platform.

Merges duplicate entries, resolves conflicts, calculates combined
confidence, and links related knowledge across memory layers.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from .base import KnowledgeEntry, ConfidenceLevel
from .cross_reference import CrossReferenceEngine

logger = logging.getLogger("Ultrone.KnowledgeEngine.Consolidation")


class KnowledgeConsolidation:
    """Consolidates and deduplicates knowledge entries.

    Features
    --------
    - Deduplication via cross-reference engine
    - Conflict resolution (highest confidence wins)
    - Confidence recalculation
    - Provenance preservation
    """

    def __init__(
        self,
        cross_reference: Optional[CrossReferenceEngine] = None,
        max_merge_similarity: float = 0.85,
    ):
        self.cross_reference = cross_reference or CrossReferenceEngine()
        self.max_merge_similarity = max_merge_similarity

    def consolidate(
        self,
        entries: List[KnowledgeEntry],
    ) -> Tuple[List[KnowledgeEntry], Dict[str, Any]]:
        """Consolidate entries.

        Returns (kept_entries, report).
        """
        duplicates = self.cross_reference.find_duplicates(entries, threshold=self.max_merge_similarity)
        merged_ids = set()
        merged_entries: Dict[str, List[KnowledgeEntry]] = defaultdict(list)

        # Group duplicate pairs
        for entry_a, entry_b, score in duplicates:
            # Keep the higher-confidence one as "primary"
            primary = entry_a if entry_a.confidence_score >= entry_b.confidence_score else entry_b
            secondary = entry_b if primary == entry_a else entry_a
            merged_ids.add(secondary.entry_id)
            merged_entries[primary.entry_id].append(secondary)

        # Build result: non-duplicates + merged primaries
        kept: List[KnowledgeEntry] = []
        for entry in entries:
            if entry.entry_id in merged_ids:
                continue  # Duplicate, skip
            if entry.entry_id in merged_entries:
                merged = self._merge(entry, merged_entries[entry.entry_id])
                kept.append(merged)
            else:
                kept.append(entry)

        report = {
            "original_count": len(entries),
            "kept_count": len(kept),
            "deduplicated_count": len(merged_ids),
            "merge_groups": len(merged_entries),
        }
        return kept, report

    def _merge(self, primary: KnowledgeEntry, secondaries: List[KnowledgeEntry]) -> KnowledgeEntry:
        """Merge secondary entries into primary."""
        # Combine tags and entities
        all_tags = list(dict.fromkeys(primary.tags))
        all_entities = list(dict.fromkeys(primary.entities))
        all_related = list(dict.fromkeys(primary.related_entry_ids))
        sources = [primary.source.value]

        for sec in secondaries:
            for tag in sec.tags:
                if tag not in all_tags:
                    all_tags.append(tag)
            for ent in sec.entities:
                if ent not in all_entities:
                    all_entities.append(ent)
            for rid in sec.related_entry_ids:
                if rid not in all_related:
                    all_related.append(rid)
            sources.append(sec.source.value)

        # Recalculate confidence: new = 1 - prod(1 - conf_i)
        combined_conf = primary.confidence_score
        for sec in secondaries:
            combined_conf = 1.0 - (1.0 - combined_conf) * (1.0 - sec.confidence_score)

        # Determine confidence level
        if combined_conf >= 0.9:
            level = ConfidenceLevel.VERIFIED
        elif combined_conf >= 0.75:
            level = ConfidenceLevel.HIGH
        elif combined_conf >= 0.5:
            level = ConfidenceLevel.MEDIUM
        elif combined_conf >= 0.25:
            level = ConfidenceLevel.LOW
        else:
            level = ConfidenceLevel.HYPOTHETICAL

        primary.tags = all_tags
        primary.entities = all_entities
        primary.related_entry_ids = all_related
        primary.confidence_score = round(combined_conf, 4)
        primary.confidence = level
        primary.metadata["merged_sources"] = sources
        primary.metadata["merged_from"] = [s.entry_id for s in secondaries]
        primary.metadata["consolidated_at"] = time.time()
        primary.version += 1
        primary.updated_at = time.time()
        return primary

    def resolve_conflicts(
        self,
        entries: List[KnowledgeEntry],
    ) -> List[KnowledgeEntry]:
        """Resolve conflicting entries by keeping highest-confidence, merging metadata."""
        by_content: Dict[str, List[KnowledgeEntry]] = defaultdict(list)
        for entry in entries:
            by_content[entry.content.strip().lower()].append(entry)

        resolved = []
        for content, group in by_content.items():
            if len(group) == 1:
                resolved.append(group[0])
            else:
                # Sort by confidence, keep best
                best = max(group, key=lambda e: e.confidence_score)
                others = [e for e in group if e.entry_id != best.entry_id]
                resolved.append(self._merge(best, others))
        return resolved

    def get_stats(self) -> Dict[str, Any]:
        return {
            "type": "KnowledgeConsolidation",
            "max_merge_similarity": self.max_merge_similarity,
            "cross_reference": self.cross_reference.get_stats(),
        }
