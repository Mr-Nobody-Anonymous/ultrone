# Copyright (c) Ultrone Contributors. All rights reserved.
"""Experiment Designer — designs rigorous experiments for hypotheses."""
from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Ultrone.Science.ExperimentDesigner")


@dataclass
class ExperimentDesign:
    """A designed experiment for a hypothesis."""
    design_id: str = field(default_factory=lambda: f"ED-{uuid.uuid4().hex[:10]}")
    hypothesis_id: str = ""
    title: str = ""
    independent_variables: List[str] = field(default_factory=list)
    dependent_variables: List[str] = field(default_factory=list)
    control_conditions: List[str] = field(default_factory=list)
    treatment_conditions: List[str] = field(default_factory=list)
    num_trials: int = 1
    metrics: List[str] = field(default_factory=list)
    statistical_tests: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "design_id": self.design_id,
            "hypothesis_id": self.hypothesis_id,
            "title": self.title,
            "independent_variables": self.independent_variables,
            "dependent_variables": self.dependent_variables,
            "control_conditions": self.control_conditions,
            "treatment_conditions": self.treatment_conditions,
            "num_trials": self.num_trials,
            "metrics": self.metrics,
            "statistical_tests": self.statistical_tests,
            "created_at": self.created_at,
        }


class ExperimentDesigner:
    """Designs Controlled experiments for research hypotheses."""

    def __init__(self):
        self._designs: List[ExperimentDesign] = []

    def design(
        self,
        hypothesis_id: str,
        title: str,
        independent_variables: Optional[List[str]] = None,
        num_trials: int = 5,
    ) -> ExperimentDesign:
        """Create an experiment design for a hypothesis."""
        design = ExperimentDesign(
            hypothesis_id=hypothesis_id,
            title=title,
            independent_variables=independent_variables or ["model_config"],
            dependent_variables=["accuracy", "f1_score"],
            control_conditions=["baseline"],
            treatment_conditions=["adaptive"],
            num_trials=num_trials,
            metrics=["accuracy", "f1_score", "loss"],
            statistical_tests=["paired_t_test", "wilcoxon"],
        )
        self._designs.append(design)
        logger.info("Designed experiment for hypothesis %s: %s", hypothesis_id, title)
        return design

    def get_designs(self) -> List[ExperimentDesign]:
        """Return all designs."""
        return list(self._designs)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "type": "ExperimentDesigner",
            "designs_created": len(self._designs),
        }
