# Copyright (c) Ultrone Contributors. All rights reserved.
"""Model lineage and checkpoint promotion.

Every produced model is stamped with the exact ingredients that made
it -- model/dataset/configuration hashes, training seed, duration, and
parent -- so ``what changed between v1 and v2`` is always answerable
from a record, never from memory.

Layout::

    models/
      baseline/     current baseline weights
      candidate/    training candidates (candidate-<id>)
      evaluated/    candidates that cleared the regression suite
      production/   winner only -- written by promote(), never by hand

``CheckpointManager`` only *moves* a candidate into production after a
governed promotion; it never invents a promotion of its own. Write
paths are separate so an experimental model can never silently become
the live one.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from self_improvement.self_training.trainer import LearnedWeights

#: Channels a model may occupy.
STATUSES = ("candidate", "evaluated", "production")


@dataclass
class ModelRecord:
    model_id: str
    model_hash: str
    dataset_hash: str
    configuration_hash: str
    training_seed: str
    parent_model: str
    duration_seconds: float
    evaluation_scores: Dict[str, float] = field(default_factory=dict)
    status: str = "candidate"
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return dict(self.__dict__)


class CheckpointManager:
    """Persistent, lineage-stamped model store.

    All four channels live under one root; the registry is an
    append-only JSONL so history is never overwritten, only extended.
    """

    def __init__(self, root: str) -> None:
        self._root = Path(root)
        self._channels = {
            status: self._root / status for status in STATUSES}
        for directory in self._channels.values():
            directory.mkdir(parents=True, exist_ok=True)
        self._registry_path = self._root / "registry.jsonl"
        self._records: List[ModelRecord] = self._load()

    # -- persistence ----------------------------------------------------- #
    def _load(self) -> List[ModelRecord]:
        if not self._registry_path.exists():
            return []
        records: List[ModelRecord] = []
        for line in self._registry_path.read_text(
                encoding="utf-8").splitlines():
            if line.strip():
                records.append(ModelRecord(**json.loads(line)))
        return records

    def _flush(self) -> None:
        lines = "\n".join(json.dumps(r.to_dict(), sort_keys=True)
                          for r in self._records)
        self._registry_path.write_text(lines + "\n", encoding="utf-8")

    # -- write paths ----------------------------------------------------- #
    def register_candidate(
            self, weights: LearnedWeights, *,
            dataset_hash: str, configuration_hash: str,
            training_seed: str, parent_model: str,
            duration_seconds: float) -> ModelRecord:
        record = ModelRecord(
            model_id=f"m{len(self._records) + 1:04d}",
            model_hash=weights.model_hash,
            dataset_hash=dataset_hash,
            configuration_hash=configuration_hash,
            training_seed=str(training_seed),
            parent_model=parent_model,
            duration_seconds=float(duration_seconds),
            status="candidate")
        self._write_weights(record.model_id, weights, "candidate")
        self._records.append(record)
        self._flush()
        return record

    def evaluate(self, model_id: str,
                 scores: Dict[str, float]) -> ModelRecord:
        record = self._get(model_id)
        record.evaluation_scores = dict(scores)
        record.status = "evaluated"
        self._write_weights(model_id, self._read_weights(
            model_id, "candidate"), "evaluated")
        self._flush()
        return record

    def promote(self, model_id: str) -> ModelRecord:
        """Relocate an evaluated candidate into production."""
        record = self._get(model_id)
        if record.status != "evaluated":
            raise ValueError(
                f"cannot promote '{model_id}' (status {record.status!r}) "
                f"-- only evaluated candidates enter production")
        record.status = "production"
        self._write_weights(model_id, self._read_weights(
            model_id, "evaluated"), "production")
        if record.parent_model:
            parent = self._get(record.parent_model)
            self._write_weights(parent.model_id, self._read_weights(
                parent.model_id, "candidate"), "baseline")
        self._flush()
        return record

    # -- read paths ------------------------------------------------------ #
    def get(self, model_id: str) -> ModelRecord:
        return self._get(model_id)

    def production(self) -> Optional[ModelRecord]:
        return next((r for r in reversed(self._records)
                     if r.status == "production"), None)

    def production_weights(self) -> Optional[LearnedWeights]:
        record = self.production()
        if record is None:
            return None
        return self._read_weights(record.model_id, "production")

    def records(self) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in self._records]

    # -- io helpers ------------------------------------------------------ #
    def _get(self, model_id: str) -> ModelRecord:
        for record in self._records:
            if record.model_id == model_id:
                return record
        raise KeyError(f"no model '{model_id}'")

    def _write_weights(self, model_id: str, weights: LearnedWeights,
                       channel: str) -> None:
        path = self._channels[channel] / model_id
        path.write_text(json.dumps(weights.to_config(), sort_keys=True),
                        encoding="utf-8")

    def _read_weights(self, model_id: str, channel: str) -> LearnedWeights:
        path = self._channels[channel] / model_id
        payload = path.read_text(encoding="utf-8")
        return LearnedWeights.from_config(json.loads(payload))