# Copyright (c) Ultrone Contributors. All rights reserved.
"""MLOps Model Registry — production model registry with stage management
(MLflow-style)."""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Ultrone.MLOps.ModelRegistry")


@dataclass
class MLOpsModel:
    """A model in the MLOps registry."""
    model_id: str = field(default_factory=lambda: f"m-{uuid.uuid4().hex[:8]}")
    name: str = ""
    version: str = "1.0.0"
    stage: str = "registered"     # registered, staging, production, archived
    run_id: str = ""
    metrics: Dict[str, float] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id, "name": self.name, "version": self.version,
            "stage": self.stage, "run_id": self.run_id, "metrics": self.metrics,
            "created_at": self.created_at,
        }


class MLOpsModelRegistry:
    """Registry for production models with stage lifecycle."""

    STAGES = ("registered", "staging", "production", "archived")

    def __init__(self):
        self._models: Dict[str, MLOpsModel] = {}

    def register(self, name: str, version: str = "1.0.0", run_id: str = "",
                 metrics: Optional[Dict[str, float]] = None) -> MLOpsModel:
        """Register a new model."""
        model = MLOpsModel(name=name, version=version, run_id=run_id, metrics=metrics or {})
        self._models[model.model_id] = model
        logger.info("Registered model %s v%s", name, version)
        return model

    def transition(self, model_id: str, stage: str) -> bool:
        """Move a model to a new stage."""
        if stage not in self.STAGES:
            raise ValueError(f"Invalid stage: {stage}")
        model = self._models.get(model_id)
        if model is None:
            return False
        model.stage = stage
        return True

    def get(self, model_id: str) -> Optional[MLOpsModel]:
        return self._models.get(model_id)

    def get_production(self, name: str) -> Optional[MLOpsModel]:
        """Get the production model for a name."""
        for m in self._models.values():
            if m.name == name and m.stage == "production":
                return m
        return None

    def list_models(self, stage: Optional[str] = None) -> List[MLOpsModel]:
        if stage:
            return [m for m in self._models.values() if m.stage == stage]
        return list(self._models.values())

    def get_stats(self) -> Dict[str, Any]:
        stages: Dict[str, int] = {}
        for m in self._models.values():
            stages[m.stage] = stages.get(m.stage, 0) + 1
        return {"type": "MLOpsModelRegistry", "total_models": len(self._models), "by_stage": stages}
