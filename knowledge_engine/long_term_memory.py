# Copyright (c) Ultrone Contributors. All rights reserved.
"""Long-term memory - persistent, high-capacity knowledge store with serialization."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from .base import KnowledgeEntry, KnowledgeMemoryBase


class LongTermMemory(KnowledgeMemoryBase):
    """Persistent long-term knowledge memory.

    Supports:
    - JSON serialization to/from disk
    - High capacity
    - Import/export of full knowledge base
    """

    def __init__(self, capacity: int = 1000000, name: str = "long_term_knowledge"):
        super().__init__(capacity=capacity, name=name)

    def save_to_file(self, path: str) -> None:
        """Persist all entries to a JSON file."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "name": self.name,
            "capacity": self.capacity,
            "entries": [e.to_dict() for e in self._entries.values()],
        }
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load_from_file(self, path: str) -> int:
        """Load entries from a JSON file. Returns number of entries loaded."""
        p = Path(path)
        if not p.exists():
            return 0
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        entries = data.get("entries", [])
        for e_data in entries:
            entry = KnowledgeEntry.from_dict(e_data)
            self._entries[entry.entry_id] = entry
        self.name = data.get("name", self.name)
        return len(entries)

    def export_all(self) -> List[Dict[str, Any]]:
        """Export all entries as dicts."""
        return [e.to_dict() for e in self._entries.values()]

    def import_all(self, entries: List[Dict[str, Any]]) -> int:
        """Import entries from dicts. Returns number imported."""
        count = 0
        for e_data in entries:
            entry = KnowledgeEntry.from_dict(e_data)
            self._entries[entry.entry_id] = entry
            count += 1
        return count
