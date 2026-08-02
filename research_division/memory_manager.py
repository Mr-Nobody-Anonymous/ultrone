# Copyright (c) Ultrone Contributors. All rights reserved.
"""Research Memory Manager — manages knowledge consolidation, deduplication,
and cross-layer memory integration for the research platform.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from comms.protocol import MessageType, Priority
from knowledge_engine.base import KnowledgeSource, KnowledgeCategory, ConfidenceLevel
from .base_agent import ResearchAgent, ResearchAgentRole

logger = logging.getLogger("Ultrone.ResearchDivision.MemoryManager")


class ResearchMemoryManagerAgent(ResearchAgent):
    """Manages knowledge memory consolidation and integration."""

    def __init__(self, **kwargs):
        super().__init__(
            agent_id=kwargs.pop("agent_id", "memory-manager-001"),
            role=ResearchAgentRole.MEMORY_MANAGER,
            **kwargs,
        )

    async def run(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Run memory consolidation and report statistics."""
        # Consolidate knowledge
        consolidation_report = self.knowledge.consolidate_all()

        # Build cross-references
        all_entries = list(self.knowledge._all_entries.values())
        references = self.knowledge.cross_reference.create_references(all_entries)

        # Update related_entry_ids
        for entry_id, related_ids in references.items():
            entry = self.knowledge._all_entries.get(entry_id)
            if entry:
                entry.related_entry_ids = related_ids

        stats = self.knowledge.get_stats()
        self._log_action("memory_consolidation", {
            "consolidation": consolidation_report,
            "cross_references": len(references),
        }, stats)
        return {
            "consolidation": consolidation_report,
            "cross_references_created": len(references),
            "stats": stats,
        }

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get current memory statistics."""
        return self.knowledge.get_stats()