# Copyright (c) Ultrone Contributors. All rights reserved.
"""Promotion gate and versioned brains.

Nothing reaches production because it *claims* to be better -- the
evaluation result decides. Every promotion/rejection produces a
reproducible record (config hash, scores, reason) appended to an
immutable history, and channel state lives in a BrainStore with
``baseline / candidate / experimental / production`` slots.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from adaptive.evaluator import EvaluationResult

CHANNELS = ("baseline", "candidate", "experimental", "production")


@dataclass(frozen=True)
class PromotionRecord:
    record_id: int
    decision: str                       # promote | reject | non_reproducible
    config_hash: str
    candidate_config: Dict[str, Any]
    candidate_score: float
    baseline_score: float
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return dict(self.__dict__)


class PromotionGate:
    """Turns EvaluationResults into audited promotion decisions."""

    _SCHEMA_VERSION = 1

    def __init__(self) -> None:
        self._history: List[PromotionRecord] = []

    def review(self, result: EvaluationResult,
               candidate_config: Dict[str, Any],
               config_hash: str) -> PromotionRecord:
        record = PromotionRecord(
            record_id=len(self._history) + 1,
            decision=result.decision,
            config_hash=config_hash,
            candidate_config=dict(candidate_config),
            candidate_score=result.candidate_score,
            baseline_score=result.baseline_score,
            reason=result.reason,
        )
        self._history.append(record)
        return record

    @property
    def history(self) -> List[PromotionRecord]:
        return list(self._history)

    def promotions(self) -> List[PromotionRecord]:
        return [r for r in self._history if r.decision == "promote"]

    # -- durable audit trail ---------------------------------------------------
    # The BrainStore already persists channel configs; without persisting
    # the gate's history, a restart keeps the promoted config but loses the
    # proof that it was ever reviewed. The closed-loop test exercises a
    # cross-process reload and must see both halves.

    def save(self, path) -> None:
        from pathlib import Path
        import json as _json
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": self._SCHEMA_VERSION,
            "history": [r.to_dict() for r in self._history],
        }
        target.write_text(
            _json.dumps(payload, sort_keys=True, indent=2),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path) -> "PromotionGate":
        from pathlib import Path
        import json as _json
        source = Path(path)
        payload = _json.loads(source.read_text(encoding="utf-8"))
        if payload.get("schema_version") != cls._SCHEMA_VERSION:
            raise ValueError(
                f"unsupported promotion schema "
                f"{payload.get('schema_version')!r}; expected "
                f"{cls._SCHEMA_VERSION}"
            )
        gate = cls()
        for raw in payload.get("history", []):
            gate._history.append(PromotionRecord(**raw))
        return gate


class BrainStore:
    """Versioned brain channels: baseline/candidate/experimental/production."""

    def __init__(self, storage_dir: Optional[str] = None) -> None:
        self._channels: Dict[str, Dict[str, Any]] = {
            channel: {} for channel in CHANNELS}
        self._storage_dir = Path(storage_dir) if storage_dir else None

    def set_config(self, channel: str, config: Dict[str, Any]) -> str:
        from adaptive.optimizer import config_hash

        if channel not in CHANNELS:
            raise ValueError(
                f"unknown channel '{channel}' -- choose from {CHANNELS}")
        self._channels[channel] = dict(config)
        if channel == "production":
            # Production is only ever written through promote(); direct
            # writes are rejected to keep the gate meaningful.
            raise ValueError("use promote() to change production")
        self._persist()
        return config_hash(config)

    def get_config(self, channel: str) -> Dict[str, Any]:
        if channel not in CHANNELS:
            raise ValueError(f"unknown channel '{channel}'")
        return dict(self._channels[channel])

    def promote(self, config: Dict[str, Any], record: PromotionRecord,
                gate: PromotionGate) -> PromotionRecord:
        """Move a reviewed configuration into production.

        Requires the gate's own record for this exact config hash with
        decision == ``promote`` -- the caller cannot bypass evaluation.
        """
        from adaptive.optimizer import config_hash

        target_hash = config_hash(config)
        verified = any(
            r.decision == "promote"
            and r.config_hash == target_hash
            and r.record_id == record.record_id
            for r in gate.history)
        if not verified:
            raise PermissionError(
                "promotion refused: no matching promotable gate record "
                f"for config {target_hash}")
        self._channels["production"] = dict(config)
        self._persist()
        return record

    def summary(self) -> Dict[str, Any]:
        from adaptive.optimizer import config_hash

        return {channel: {"config_hash": config_hash(config) if config
                          else None}
                for channel, config in self._channels.items()}

    # -- persistence ------------------------------------------------------------ #
    def _persist(self) -> None:
        if self._storage_dir is None:
            return
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        for channel, config in self._channels.items():
            path = self._storage_dir / f"{channel}.json"
            path.write_text(
                json.dumps(config, sort_keys=True, indent=2),
                encoding="utf-8")

    def load(self) -> None:
        """Reload channel configs previously persisted by ``_persist``."""
        if self._storage_dir is None or not self._storage_dir.exists():
            return
        for channel in CHANNELS:
            path = self._storage_dir / f"{channel}.json"
            if path.exists():
                self._channels[channel] = json.loads(
                    path.read_text(encoding="utf-8"))