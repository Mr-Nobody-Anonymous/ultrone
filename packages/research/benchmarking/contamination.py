"""Benchmark contamination protection and holdout leakage prevention."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class DatasetSplit(str, Enum):
    """Cryptographically separated dataset tiers for model evaluation."""
    TRAIN = "TRAIN"
    VALIDATION = "VALIDATION"
    HOLDOUT = "HOLDOUT"
    RED_TEAM_HOLDOUT = "RED_TEAM_HOLDOUT"


class ContaminationError(Exception):
    """Raised when candidate model or artifacts exhibit leakage of holdout data."""
    pass


@dataclass(frozen=True)
class DatasetManifest:
    """Immutable, cryptographically signed dataset manifest."""
    split: DatasetSplit
    manifest_id: str
    dataset_hash: str
    sample_hashes: List[str]
    n_samples: int
    version: str = "2026.01"

    @classmethod
    def create(cls, split: DatasetSplit, items: List[str], manifest_id: str = "") -> DatasetManifest:
        """Create an immutable manifest from a collection of serialized dataset items."""
        sample_hashes = [hashlib.sha256(item.encode("utf-8")).hexdigest() for item in items]
        combined = ":".join(sorted(sample_hashes))
        overall_hash = hashlib.sha256(combined.encode("utf-8")).hexdigest()
        mid = manifest_id or f"manifest-{split.value.lower()}-{overall_hash[:8]}"
        return cls(
            split=split,
            manifest_id=mid,
            dataset_hash=overall_hash,
            sample_hashes=sample_hashes,
            n_samples=len(items),
        )


class ContaminationGuard:
    """Verifies that candidates and training pipelines have zero leakage into holdouts."""

    def __init__(self, holdout_manifests: Optional[List[DatasetManifest]] = None):
        self.holdouts = holdout_manifests or []
        self._holdout_hashes: Set[str] = set()
        for manifest in self.holdouts:
            if manifest.split in (DatasetSplit.HOLDOUT, DatasetSplit.RED_TEAM_HOLDOUT):
                self._holdout_hashes.update(manifest.sample_hashes)

    def register_holdout(self, manifest: DatasetManifest) -> None:
        self.holdouts.append(manifest)
        if manifest.split in (DatasetSplit.HOLDOUT, DatasetSplit.RED_TEAM_HOLDOUT):
            self._holdout_hashes.update(manifest.sample_hashes)

    def inspect_training_data(self, training_items: List[str]) -> Tuple[bool, Optional[str]]:
        """Inspect proposed training data against holdout hashes. Rejects any exact duplicates."""
        for idx, item in enumerate(training_items):
            h = hashlib.sha256(item.encode("utf-8")).hexdigest()
            if h in self._holdout_hashes:
                return False, f"Benchmark contamination detected at training item {idx} (hash {h[:8]} in holdout)"
        return True, None

    def inspect_candidate_artifacts(
        self,
        candidate_strings: List[str],
        ngram_size: int = 5,
    ) -> Tuple[bool, Optional[str]]:
        """Check candidate outputs or memory for direct verbatim holdout contamination."""
        for c_str in candidate_strings:
            h = hashlib.sha256(c_str.encode("utf-8")).hexdigest()
            if h in self._holdout_hashes:
                return False, f"Candidate artifact contains verbatim holdout sample (hash {h[:8]})"
        return True, None
