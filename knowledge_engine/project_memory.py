# Copyright (c) Ultrone Contributors. All rights reserved.
"""Project memory - knowledge about the ULTRONE project itself."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .base import (
    KnowledgeEntry,
    KnowledgeMemoryBase,
    KnowledgeSource,
)


class ProjectMemory(KnowledgeMemoryBase):
    """Stores project-level knowledge: module inventory, status, and architecture decisions."""

    def __init__(self, capacity: int = 20000, name: str = "project_knowledge"):
        super().__init__(capacity=capacity, name=name)

    def record_module(
        self,
        module_path: str,
        status: str = "unknown",
        description: str = "",
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> KnowledgeEntry:
        """Record knowledge about a project module."""
        entry = KnowledgeEntry(
            content=description or f"Module {module_path} ({status})",
            source=KnowledgeSource.CODE,
            confidence_score=0.9,
            tags=["module", module_path, status] + (tags or []),
            entities=[module_path],
            metadata={
                **(metadata or {}),
                "module_path": module_path,
                "status": status,
            },
        )
        return self.store(entry)

    def find_module(self, module_path: str) -> Optional[KnowledgeEntry]:
        p = module_path.lower()
        for e in self._entries.values():
            meta = e.metadata or {}
            if p in (meta.get("module_path", "").lower() or e.content.lower()):
                return e
        return None

    def list_modules_by_status(self, status: str) -> List[KnowledgeEntry]:
        return [
            e for e in self._entries.values()
            if (e.metadata or {}).get("status") == status
        ]

