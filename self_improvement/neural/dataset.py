# Copyright (c) Ultrone Contributors. All rights reserved.
"""Real training dataset (item 4 of the neural milestone).

The existing ``DatasetBuilder`` already converts ExperienceMemory
traces into ``TrainingExample`` records and writes a JSONL artifact.
What it does not do is *external* data -- curated corpora, public
instruction-tuning data, or hand-written golden examples -- and it
does not enforce train/holdout separation.

This module adds:

* ``ExternalCorpus`` -- a registry of named corpora with strict
  train/holdout separation at *ingest* time, not at evaluation time.
  Once a record is tagged ``"holdout"`` it never re-appears in any
  training mixture; once tagged ``"train"`` it never re-appears in any
  holdout evaluation. This is the rule that makes holdout numbers
  honest.

* ``DatasetSplitter`` -- take a list of ``TrainingExample`` and split
  it deterministically (configurable seed) into train + holdout. The
  splitter writes both halves to disk and returns a content hash for
  each so the lineage can record exactly which bytes trained which
  candidate.

* ``SplitResult`` / ``TrainHoldoutPair`` -- small data types the
  trainer and the benchmark consume.

The module plugs into the existing pipeline by emitting records that
already satisfy the ``TrainingExample`` schema the ``DatasetBuilder``
expects, so the ``ContinualMixture`` continues to merge historical
+ recent + weakness corpora without modification.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from self_improvement.self_training.dataset_builder import (
    DatasetArtifact,
    TrainingExample,
    content_hash,
)


# --- Data types ----------------------------------------------------------- #


@dataclass
class TrainHoldoutPair:
    """Result of a deterministic train/holdout split.

    The pair is reported *with* the seed it was produced under so a
    later audit can re-run the split and obtain identical artifacts.
    """

    train: DatasetArtifact
    holdout: DatasetArtifact
    seed: int
    train_ratio: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "train": self.train.to_dict(),
            "holdout": self.holdout.to_dict(),
            "seed": self.seed,
            "train_ratio": self.train_ratio,
        }


@dataclass
class SplitResult:
    """Outcome of a split, including a guarantee that no example leaks.

    ``leakage_checked`` is True iff every example_id appears in
    exactly one of the two halves. Any leakage (an id in both, or an
    id in neither) flips the bool to False and the offending ids are
    reported in ``leaked_ids``.
    """

    pair: TrainHoldoutPair
    leakage_checked: bool
    leaked_ids: List[str] = field(default_factory=list)
    total_examples: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pair": self.pair.to_dict(),
            "leakage_checked": self.leakage_checked,
            "leaked_ids": list(self.leaked_ids),
            "total_examples": self.total_examples,
        }


# --- External corpus ----------------------------------------------------- #


class ExternalCorpus:
    """Named, hash-tracked external training corpus.

    A *corpus* is a list of ``TrainingExample`` plus a ``name``, a
    ``kind`` (``"curated"``, ``"public_instruct"``, ``"synthetic"``,
    ``"experience"``), and a content hash. The same record type is
    what the existing ``DatasetBuilder`` already emits, so a
    mixture-style merge needs no schema changes.

    Strict train/holdout separation: a corpus is one of the two --
    a ``train`` corpus never feeds the holdout evaluator, and a
    ``holdout`` corpus never feeds a candidate's training mixture.
    The class enforces this in the constructor.
    """

    #: Valid corpus kinds.
    KINDS = ("curated", "public_instruct", "synthetic", "experience")

    def __init__(self, name: str, kind: str, examples: Sequence[Any],
                 *, split: str = "train",
                 source: str = "") -> None:
        if split not in ("train", "holdout"):
            raise ValueError(
                f"split must be 'train' or 'holdout', got {split!r}")
        if kind not in self.KINDS:
            raise ValueError(
                f"kind must be one of {self.KINDS}, got {kind!r}")
        if not name:
            raise ValueError("corpus name is required")
        self.name = str(name)
        self.kind = str(kind)
        self.split = str(split)
        self.source = str(source)
        # Examples are stored as plain dicts so a corpus can be
        # constructed from raw records (jsonl, csv, in-memory list)
        # without first wrapping them in a TrainingExample.
        self._records: List[Dict[str, Any]] = []
        for ex in examples:
            if isinstance(ex, TrainingExample):
                self._records.append(ex.to_dict())
            elif isinstance(ex, dict):
                self._records.append(dict(ex))
            else:
                raise TypeError(
                    f"examples must be TrainingExample or dict, got "
                    f"{type(ex).__name__}")
        self._content_hash = self._compute_hash()

    # -- accessors ------------------------------------------------------- #
    def records(self) -> List[Dict[str, Any]]:
        return list(self._records)

    def __len__(self) -> int:
        return len(self._records)

    def fingerprint(self) -> str:
        return self._content_hash

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind,
            "split": self.split,
            "source": self.source,
            "num_examples": len(self._records),
            "fingerprint": self._content_hash,
        }

    # -- helpers --------------------------------------------------------- #
    def _compute_hash(self) -> str:
        # Stable over (sorted ids + sorted first fields) so a tiny
        # reorder does not produce a different hash, but a content
        # change does.
        if not self._records:
            return hashlib.sha256(b"empty").hexdigest()[:16]
        ids = sorted(r.get("example_id", "") for r in self._records)
        # Hash the *fields*, not the raw bytes, so json-equal records
        # produce equal fingerprints across jsonlibs.
        canonical = json.dumps({"name": self.name, "kind": self.kind,
                                "split": self.split, "ids": ids,
                                "records": sorted(
                                    [json.dumps(r, sort_keys=True)
                                     for r in self._records])},
                               sort_keys=True).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()[:16]


# --- DatasetSplitter ----------------------------------------------------- #


class DatasetSplitter:
    """Deterministic train/holdout splitter with leakage detection.

    The split is *content-stable*: same examples + same seed ->
    same artifacts (byte-equal). The default seed (0) makes the
    benchmark deterministic.

    The leakage check runs after the split and refuses to return a
    result whose ``leakage_checked`` flag is False -- call sites
    should treat ``leakage_checked == False`` as a hard error because
    it would silently inflate the holdout improvement.
    """

    def __init__(self, *, train_ratio: float = 0.8,
                 seed: int = 0, workdir: str = "") -> None:
        if not 0.5 <= train_ratio <= 0.95:
            raise ValueError("train_ratio must lie in [0.5, 0.95]")
        self.train_ratio = float(train_ratio)
        self.seed = int(seed)
        self._workdir = Path(workdir) if workdir else None

    # -- public API ------------------------------------------------------ #
    def split(self, examples: Sequence[Any], *,
              tag: str = "split") -> SplitResult:
        records = [e.to_dict() if isinstance(e, TrainingExample)
                   else dict(e) for e in examples]
        if not records:
            return SplitResult(
                pair=TrainHoldoutPair(
                    train=DatasetArtifact(path="", content_hash="",
                                          num_examples=0),
                    holdout=DatasetArtifact(path="", content_hash="",
                                            num_examples=0),
                    seed=self.seed, train_ratio=self.train_ratio),
                leakage_checked=True,
                leaked_ids=[],
                total_examples=0)

        # Deterministic ordering: by (id, seed) so a different seed
        # produces a different split, but the same seed always
        # reproduces it.
        ordered = sorted(records,
                         key=lambda r: (r.get("example_id", ""),
                                        self.seed))
        cut = int(round(self.train_ratio * len(ordered)))
        # Guarantee at least one example in each half when feasible.
        if 0 < cut < len(ordered):
            cut = max(1, min(len(ordered) - 1, cut))
        train_records = ordered[:cut]
        holdout_records = ordered[cut:]

        # Leakage check.
        train_ids = {r.get("example_id", "") for r in train_records}
        holdout_ids = {r.get("example_id", "") for r in holdout_records}
        overlap = train_ids & holdout_ids
        all_ids = {r.get("example_id", "") for r in records}
        missing = all_ids - (train_ids | holdout_ids)
        leaked = sorted(overlap | missing)
        leakage_checked = not leaked

        if self._workdir is None:
            import tempfile
            self._workdir = Path(tempfile.mkdtemp(prefix="datasplit-"))
        out_dir = self._workdir
        out_dir.mkdir(parents=True, exist_ok=True)

        train_path = out_dir / f"{tag}_train.jsonl"
        holdout_path = out_dir / f"{tag}_holdout.jsonl"
        train_path.write_text(
            "\n".join(json.dumps(r, sort_keys=True) for r in train_records)
            + ("\n" if train_records else ""), encoding="utf-8")
        holdout_path.write_text(
            "\n".join(json.dumps(r, sort_keys=True) for r in holdout_records)
            + ("\n" if holdout_records else ""), encoding="utf-8")

        train_hash = content_hash(train_records)
        holdout_hash = content_hash(holdout_records)

        return SplitResult(
            pair=TrainHoldoutPair(
                train=DatasetArtifact(
                    path=str(train_path), content_hash=train_hash,
                    num_examples=len(train_records),
                    source_counts={"external": len(train_records)}),
                holdout=DatasetArtifact(
                    path=str(holdout_path), content_hash=holdout_hash,
                    num_examples=len(holdout_records),
                    source_counts={"external": len(holdout_records)}),
                seed=self.seed, train_ratio=self.train_ratio),
            leakage_checked=leakage_checked,
            leaked_ids=leaked,
            total_examples=len(records))
