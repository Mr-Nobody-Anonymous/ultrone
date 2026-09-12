"""ULTRONE Core Provenance - Derivation traces for fused tracks and analytical assessments."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class DerivationStep:
    """A step in an algorithmic or neural derivation process."""
    step_id: str
    algorithm_or_model: str
    input_ids: List[str]
    output_id: str
    confidence_delta: float = 0.0
    computation_time_ms: float = 0.0
    parameters: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "algorithm_or_model": self.algorithm_or_model,
            "input_ids": self.input_ids,
            "output_id": self.output_id,
            "confidence_delta": self.confidence_delta,
            "computation_time_ms": self.computation_time_ms,
            "parameters": self.parameters,
            "timestamp": self.timestamp,
        }


@dataclass
class DerivationTrace:
    """Complete chain of steps that produced an entity attribute or tactical assessment."""
    target_entity_id: str
    attribute_name: str
    steps: List[DerivationStep] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def add_step(self, step: DerivationStep) -> None:
        self.steps.append(step)

    def summary(self) -> str:
        models = " -> ".join(s.algorithm_or_model for s in self.steps)
        return f"Derivation for {self.target_entity_id}.{self.attribute_name} via [{models}]"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_entity_id": self.target_entity_id,
            "attribute_name": self.attribute_name,
            "steps": [s.to_dict() for s in self.steps],
            "created_at": self.created_at,
        }
