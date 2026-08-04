# Copyright (c) Ultrone Contributors. All rights reserved.
"""Dataset Registry — central registry for all datasets.

Tracks dataset metadata, versions, and access statistics.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Ultrone.Datasets.Registry")


@dataclass
class DatasetEntry:
    """A registered dataset."""
    dataset_id: str = field(default_factory=lambda: f"D-{uuid.uuid4().hex[:12]}")
    name: str = ""
    source: str = "custom"        # huggingface, custom, synthetic
    num_samples: int = 0
    num_features: int = 0
    version: str = "1.0.0"
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dataset_id": self.dataset_id, "name": self.name, "source": self.source,
            "num_samples": self.num_samples, "num_features": self.num_features,
            "version": self.version, "tags": self.tags, "metadata": self.metadata,
            "created_at": self.created_at, "updated_at": self.updated_at,
        }


class DatasetRegistry:
    """Central registry of datasets."""

    def __init__(self):
        self._datasets: Dict[str, DatasetEntry] = {}
        self._by_name: Dict[str, List[str]] = {}

    def register(self, entry: DatasetEntry) -> DatasetEntry:
        """Register a dataset."""
        self._datasets[entry.dataset_id] = entry
        self._by_name.setdefault(entry.name, []).append(entry.dataset_id)
        logger.info("Dataset registered: %s (%s)", entry.name, entry.source)
        return entry

    def get(self, dataset_id: str) -> Optional[DatasetEntry]:
        return self._datasets.get(dataset_id)

    def get_by_name(self, name: str) -> List[DatasetEntry]:
        ids = self._by_name.get(name, [])
        return [self._datasets[i] for i in ids if i in self._datasets]

    def search(self, query: str, limit: int = 20) -> List[DatasetEntry]:
        q = query.lower()
        results = [d for d in self._datasets.values()
                   if q in d.name.lower() or any(q in t.lower() for t in d.tags) or q in d.source]
        return results[:limit]

    def list_all(self, source: Optional[str] = None) -> List[DatasetEntry]:
        if source:
            return [d for d in self._datasets.values() if d.source == source]
        return list(self._datasets.values())

    def get_stats(self) -> Dict[str, Any]:
        sources: Dict[str, int] = {}
        for d in self._datasets.values():
            sources[d.source] = sources.get(d.source, 0) + 1
        return {
            "type": "DatasetRegistry",
            "total_datasets": len(self._datasets),
            "by_source": sources,
        }

