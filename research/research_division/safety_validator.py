# Copyright (c) Ultrone Contributors. All rights reserved.
"""Safety Validator — validates research outputs for safety, ethical
considerations, and compliance with platform guidelines.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from comms.protocol import MessageType
from knowledge_engine.base import KnowledgeSource
from .base_agent import ResearchAgent, ResearchAgentRole

logger = logging.getLogger("Ultrone.ResearchDivision.Safety")


class SafetyValidator(ResearchAgent):
    """Validates research outputs for safety and compliance."""

    def __init__(self, **kwargs):
        super().__init__(
            agent_id=kwargs.pop("agent_id", "safety-validator-001"),
            role=ResearchAgentRole.SAFETY,
            **kwargs,
        )
        self.message_handlers[MessageType.RESEARCH_SAFETY_VALIDATION] = self._on_safety_request

    async def run(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Validate all experiments for safety."""
        experiments = self.research_db.list_experiments()
        validations = []
        for experiment in experiments:
            validation = self._validate_experiment(experiment)
            validations.append(validation)

        self._log_action("safety_cycle", {"validations": len(validations)}, None)
        return {"validations": len(validations), "results": validations}

    def _on_safety_request(self, message: Any) -> Any:
        experiment_id = message.content.get("experiment_id")
        experiment = self.research_db.get_experiment(experiment_id) if experiment_id else None
        if experiment:
            return self._validate_experiment(experiment)
        return None

    def _validate_experiment(self, experiment: Any) -> Dict[str, Any]:
        """Validate an experiment for safety and compliance."""
        warnings = []
        passed = True

        # Check for sensitive content
        text = f"{experiment.hypothesis} {experiment.implementation} {experiment.conclusion}".lower()
        sensitive_terms = ["weapon", "attack", "harm", "exploit", "bypass", "evade"]
        for term in sensitive_terms:
            if term in text:
                warnings.append(f"Contains potentially sensitive term: '{term}'")
                passed = False

        # Check for data privacy
        if not experiment.dataset:
            warnings.append("No dataset specified - data provenance unclear")
            passed = False

        # Check for resource safety
        if experiment.resource_usage:
            gpu_util = experiment.resource_usage.get("gpu_utilization", 0)
            if gpu_util > 0.95:
                warnings.append("GPU utilization exceeds safe threshold (95%)")

        validation = {
            "experiment_id": experiment.experiment_id,
            "passed": passed,
            "warnings": warnings,
        }

        self.knowledge.store_auto_categorized(
            content=f"Safety validation for experiment '{experiment.experiment_id}': passed={passed}, "
            f"warnings={warnings}",
            source=KnowledgeSource.ANALYSIS,
            tags=["safety", "validation"],
            entities=[experiment.experiment_id],
            confidence_score=0.9 if passed else 0.5,
            layer="experiment",
            metadata={"experiment_id": experiment.experiment_id, "validation": validation},
        )

        self._log_action("experiment_validated", {"experiment_id": experiment.experiment_id}, validation)
        return validation
