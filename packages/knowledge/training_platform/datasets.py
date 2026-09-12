# Copyright (c) Ultrone Contributors. All rights reserved.
"""Dataset registry for the training platform.

Provides dataset registration, validation, versioning, hashing, and
metadata tracking. Every dataset gets a version, hash, license, source,
schema, quality score, safety classification, and creation date.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Ultrone.TrainingPlatform.Datasets")


@dataclass
class DatasetRecord:
    """A registered dataset."""

    name: str
    version: str = "1.0.0"
    hash: str = ""
    license: str = ""
    source: str = ""
    schema: Dict[str, Any] = field(default_factory=dict)
    quality_score: float = 0.0
    safety_classification: str = "research"
    creation_date: float = field(default_factory=time.time)
    num_examples: int = 0
    path: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "hash": self.hash,
            "license": self.license,
            "source": self.source,
            "schema": self.schema,
            "quality_score": self.quality_score,
            "safety_classification": self.safety_classification,
            "creation_date": self.creation_date,
            "num_examples": self.num_examples,
            "path": self.path,
            "metadata": self.metadata,
        }


class DatasetRegistry:
    """Registry for training datasets.

    Supports registration, validation, hashing, and listing of datasets.
    """

    def __init__(self, storage_dir: str = "training_platform/datasets"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._datasets: Dict[str, DatasetRecord] = {}

    def register(
        self,
        name: str,
        path: str,
        license: str = "",
        source: str = "",
        version: str = "1.0.0",
        schema: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DatasetRecord:
        """Register a dataset.

        Parameters
        ----------
        name : str
            Dataset name.
        path : str
            Path to the dataset file/directory.
        license : str
            Dataset license.
        source : str
            Dataset source.
        version : str
            Dataset version.
        schema : Optional[Dict]
            Dataset schema.
        metadata : Optional[Dict]
            Additional metadata.

        Returns
        -------
        DatasetRecord
            The registered dataset record.
        """
        record = DatasetRecord(
            name=name,
            version=version,
            license=license,
            source=source,
            schema=schema or {},
            path=path,
            metadata=metadata or {},
        )
        # Compute hash
        record.hash = self._compute_hash(path)
        # Count examples
        record.num_examples = self._count_examples(path)
        # Compute quality score
        record.quality_score = self._compute_quality(path)

        self._datasets[name] = record
        logger.info("Registered dataset '%s' (version=%s, examples=%d)", name, version, record.num_examples)
        return record

    def _compute_hash(self, path: str) -> str:
        """Compute a SHA-256 hash of the dataset file."""
        p = Path(path)
        if not p.exists():
            return ""
        h = hashlib.sha256()
        if p.is_file():
            with open(p, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    h.update(chunk)
        else:
            # Hash directory listing
            for f in sorted(p.rglob("*")):
                if f.is_file():
                    h.update(str(f).encode())
        return h.hexdigest()[:16]

    def _count_examples(self, path: str) -> int:
        """Count examples in a dataset file."""
        p = Path(path)
        if not p.exists():
            return 0
        if p.is_file():
            suffix = p.suffix.lower()
            try:
                if suffix == ".jsonl":
                    return sum(1 for _ in open(p, "r", encoding="utf-8"))
                if suffix == ".json":
                    data = json.loads(p.read_text(encoding="utf-8"))
                    if isinstance(data, list):
                        return len(data)
                    if isinstance(data, dict):
                        return len(data.get("examples", data.get("data", [])))
                if suffix == ".csv":
                    import csv

                    with open(p, "r", encoding="utf-8") as f:
                        return sum(1 for _ in csv.reader(f)) - 1
                if suffix == ".txt":
                    return sum(1 for _ in open(p, "r", encoding="utf-8"))
            except Exception:
                return 0
        return 0

    def _compute_quality(self, path: str) -> float:
        """Compute a basic quality score based on file size and format."""
        p = Path(path)
        if not p.exists():
            return 0.0
        size = p.stat().st_size if p.is_file() else sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
        if size == 0:
            return 0.0
        # Score based on size (larger = more data = higher base score)
        score = min(1.0, size / (10 * 1024 * 1024))  # 10MB = full score
        return round(score, 3)

    def validate(self, name: str) -> Dict[str, Any]:
        """Validate a registered dataset.

        Returns
        -------
        Dict[str, Any]
            Validation report.
        """
        record = self._datasets.get(name)
        if record is None:
            return {"valid": False, "error": f"Dataset '{name}' not found"}

        issues = []
        if not record.path:
            issues.append("No path specified")
        elif not Path(record.path).exists():
            issues.append(f"Path does not exist: {record.path}")
        if not record.hash:
            issues.append("No hash computed")
        if record.num_examples == 0:
            issues.append("No examples found")

        return {
            "valid": len(issues) == 0,
            "name": name,
            "issues": issues,
            "num_examples": record.num_examples,
            "hash": record.hash,
        }

    def get(self, name: str) -> Optional[DatasetRecord]:
        """Get a dataset by name."""
        return self._datasets.get(name)

    def list_datasets(self) -> List[Dict[str, Any]]:
        """List all registered datasets."""
        return [d.to_dict() for d in self._datasets.values()]

    def remove(self, name: str) -> bool:
        """Remove a dataset."""
        return self._datasets.pop(name, None) is not None

    def get_stats(self) -> Dict[str, Any]:
        """Return registry statistics."""
        return {
            "type": "DatasetRegistry",
            "datasets": len(self._datasets),
            "total_examples": sum(d.num_examples for d in self._datasets.values()),
        }