# Copyright (c) Ultrone Contributors. All rights reserved.
"""Experiment memory - knowledge from experiment runs, results, and configurations."""

from __future__ import annotations

from typing import Any, Dict, Optional

from .base import (
    ConfidenceLevel,
    KnowledgeCategory,
    KnowledgeEntry,
    KnowledgeMemoryBase,
    KnowledgeSource,
)


class ExperimentMemory(KnowledgeMemoryBase):
    """Stores experiment knowledge: runs, configs, metrics, and outcomes."""

    def __init__(self, capacity: int = 50000, name: str = "experiment_knowledge"):
        super().__init__(capacity=capacity, name=name)

    def record_experiment(
        self,
        experiment_id: str,
        description: str,
        config: Optional[Dict[str, Any]] = None,
        metrics: Optional[Dict[str, float]] = None,
        status: str = "completed",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> KnowledgeEntry:
        """Record an experiment run."""
        summary = ", ".join(f"{k}={v:.4f}" for k, v in (metrics or {}).items())
        entry = KnowledgeEntry(
            content=f"{description} | metrics: {summary}" if summary else description,
            category=KnowledgeCategory.RESULT,
            source=KnowledgeSource.EXPERIMENT,
            confidence=self._confidence_from_status(status),
            confidence_score=0.8 if status == "completed" else 0.5,
            tags=["experiment", experiment_id, status],
            entities=[f"experiment:{experiment_id}"],
            metadata={
                **(metadata or {}),
                "experiment_id": experiment_id,
                "config": config or {},
                "metrics": metrics or {},
                "status": status,
            },
        )
        return self.store(entry)

    def find_experiment(self, experiment_id: str) -> Optional[KnowledgeEntry]:
        eid = f"experiment:{experiment_id}"
        for e in self._entries.values():
            if eid in e.entities:
                return e
        return None

    def get_metrics(self, experiment_id: str) -> Dict[str, float]:
        entry = self.find_experiment(experiment_id)
        if entry:
            return dict((entry.metadata or {}).get("metrics", {}))
        return {}

    @staticmethod
    def _confidence_from_status(status: str) -> ConfidenceLevel:
        if status == "completed":
            return ConfidenceLevel.VERIFIED
        if status == "failed":
            return ConfidenceLevel.LOW
        return ConfidenceLevel.MEDIUM
