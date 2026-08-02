# Copyright (c) Ultrone Contributors. All rights reserved.
"""Procedural memory — how-to knowledge, recipes, and workflows."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .base import (
    KnowledgeCategory,
    KnowledgeEntry,
    KnowledgeMemoryBase,
    KnowledgeSource,
)


class ProceduralMemory(KnowledgeMemoryBase):
    """Stores procedural knowledge: step-by-step procedures and workflows."""

    def __init__(self, capacity: int = 20_000, name: str = "procedural_knowledge"):
        super().__init__(capacity=capacity, name=name)

    def store_procedure(
        self,
        name: str,
        steps: List[str],
        prerequisites: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> KnowledgeEntry:
        """Store a named procedure with ordered steps."""
        content = f"Procedure: {name}\n" + "\n".join(f"{i+1}. {s}" for i, s in enumerate(steps))
        entry = KnowledgeEntry(
            content=content,
            category=KnowledgeCategory.METHOD,
            source=KnowledgeSource.CODE,
            confidence_score=0.8,
            tags=["procedure", name] + (tags or []),
            entities=[name],
            metadata={
                **(metadata or {}),
                "steps": steps,
                "prerequisites": prerequisites or [],
            },
        )
        return self.store(entry)

    def find_procedure(self, name: str) -> Optional[KnowledgeEntry]:
        n = name.lower()
        for e in self._entries.values():
            if any(n == ent.lower() for ent in e.entities):
                return e
            if f"procedure: {name}".lower() in e.content.lower():
                return e
        return None

    def extract_steps(self, entry_id: str) -> List[str]:
        """Return the ordered steps of a stored procedure."""
        entry = self.get(entry_id)
        if entry:
            steps = entry.metadata.get("steps")
            if steps:
                return list(steps)
            # Fall back to parsing content lines.
            lines = entry.content.splitlines()
            parsed = []
            for line in lines:
                stripped = line.strip()
                if stripped and stripped[0].isdigit() and ". " in stripped:
                    parsed.append(stripped.split(". ", 1)[1])
            return parsed
        return []
