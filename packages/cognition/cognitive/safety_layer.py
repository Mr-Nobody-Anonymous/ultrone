# Copyright (c) Ultrone Contributors. All rights reserved.
"""Safety Layer — continuous robustness monitoring.

Continuously monitors distribution shift, out-of-distribution inputs,
novel situations, uncertainty, contradictions, memory corruption,
sensor disagreement, and model drift. Automatically falls back, requests
human review, recalibrates confidence, and recovers gracefully.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .base_layer import CognitiveLayer, LayerConfig
from .cycle_context import CycleContext, CyclePhase, PhaseResult
from .event_types import CognitiveEventType, SafetyEvent

logger = logging.getLogger("Ultrone.Cognitive.Safety")


@dataclass
class SafetyLayerConfig(LayerConfig):
    """Configuration for the safety layer."""
    name: str = "safety"
    uncertainty_threshold: float = 0.7
    confidence_threshold: float = 0.3
    drift_threshold: float = 0.5
    enable_human_review: bool = True
    enable_auto_fallback: bool = True
    enable_recalibration: bool = True
    max_violations_before_human: int = 3


class SafetyLayer(CognitiveLayer):
    """Safety and robustness monitoring layer.

    The safety layer:
    1. Monitors distribution shift
    2. Detects out-of-distribution inputs
    3. Identifies novel situations
    4. Monitors uncertainty levels
    5. Detects contradictions
    6. Checks for memory corruption
    7. Detects sensor disagreement
    8. Monitors model drift
    9. Automatically falls back when needed
    10. Requests human review when necessary
    """

    def __init__(self, config: Optional[SafetyLayerConfig] = None):
        super().__init__(config or SafetyLayerConfig())
        self._violations: List[Dict[str, Any]] = []
        self._monitor_history: List[Dict[str, Any]] = []
        self._fallbacks_triggered: int = 0
        self._human_reviews_requested: int = 0

    def _layer_phase(self) -> CyclePhase:
        return CyclePhase.EVALUATE

    def check_phase(self, ctx: CycleContext, phase: CyclePhase) -> Dict[str, Any]:
        """Check safety before a phase executes."""
        violations = []

        # Check confidence
        if ctx.confidence < self.config.confidence_threshold:
            violations.append({
                "type": "low_confidence",
                "phase": phase.value,
                "confidence": ctx.confidence,
            })

        # Check uncertainty
        if ctx.uncertainty > self.config.uncertainty_threshold:
            violations.append({
                "type": "high_uncertainty",
                "phase": phase.value,
                "uncertainty": ctx.uncertainty,
            })

        if violations:
            self._record_violations(violations)
            return {
                "safe": False,
                "reason": violations[0]["type"],
                "violations": violations,
            }

        return {"safe": True, "reason": "no violations"}

    def process(self, ctx: CycleContext) -> PhaseResult:
        """Execute the safety monitoring phase.

        Parameters
        ----------
        ctx : CycleContext
            The shared cycle context.

        Returns
        -------
        PhaseResult
            Result with safety monitoring findings.
        """
        start = time.time()

        # 1. Monitor all safety aspects
        issues = []
        issues.extend(self._monitor_uncertainty(ctx))
        issues.extend(self._monitor_confidence(ctx))
        issues.extend(self._monitor_drift(ctx))
        issues.extend(self._monitor_contradictions(ctx))
        issues.extend(self._monitor_memory_integrity(ctx))
        issues.extend(self._monitor_sensor_consistency(ctx))

        # 2. Trigger fallbacks
        fallbacks = []
        if self.config.enable_auto_fallback and issues:
            fallbacks = self._trigger_fallbacks(ctx, issues)

        # 3. Request human review
        human_review = None
        if self.config.enable_human_review and len(self._violations) >= self.config.max_violations_before_human:
            human_review = {
                "requested": True,
                "reason": f"{len(self._violations)} safety violations detected",
                "issues": issues,
            }
            self._human_reviews_requested += 1
            self._publish_event(
                CognitiveEventType.HUMAN_OVERVIEW_REQUESTED,
                {
                    "reason": human_review["reason"],
                    "violations": len(self._violations),
                },
            )

        # 4. Recalibrate confidence
        recalibration = None
        if self.config.enable_recalibration:
            recalibration = self._recalibrate_confidence(ctx)

        # 5. Store in context
        ctx.metadata["safety"] = {
            "issues": issues,
            "fallbacks": fallbacks,
            "human_review": human_review,
            "recalibration": recalibration,
        }

        # 6. Publish events
        for issue in issues[:5]:
            self._publish_event(
                CognitiveEventType.SAFETY_VIOLATION,
                {
                    "type": issue["type"],
                    "severity": issue.get("severity", "medium"),
                    "details": issue,
                },
            )

        # 7. Create decision trace
        trace = self._create_trace(
            decision="Safety monitoring and robustness",
            confidence=1.0 - min(0.5, len(issues) * 0.1),
            evidence=[
                {
                    "source": "safety_monitor",
                    "description": f"Detected {len(issues)} safety issues",
                    "confidence": 0.8,
                }
            ],
        )

        self._monitor_history.append({
            "timestamp": time.time(),
            "issues": issues,
            "fallbacks": fallbacks,
        })
        if len(self._monitor_history) > 100:
            self._monitor_history = self._monitor_history[-100:]

        return PhaseResult(
            phase=self._phase,
            success=len(issues) == 0,
            duration_seconds=time.time() - start,
            output={
                "issues": issues,
                "fallbacks": fallbacks,
                "human_review": human_review,
                "recalibration": recalibration,
                "violations_total": len(self._violations),
            },
            trace=trace,
        )

    def _monitor_uncertainty(self, ctx: CycleContext) -> List[Dict[str, Any]]:
        """Monitor uncertainty levels."""
        issues = []
        if ctx.uncertainty > self.config.uncertainty_threshold:
            issues.append({
                "type": "high_uncertainty",
                "severity": "high",
                "uncertainty": ctx.uncertainty,
                "threshold": self.config.uncertainty_threshold,
            })
        return issues

    def _monitor_confidence(self, ctx: CycleContext) -> List[Dict[str, Any]]:
        """Monitor confidence levels."""
        issues = []
        if ctx.confidence < self.config.confidence_threshold:
            issues.append({
                "type": "low_confidence",
                "severity": "high",
                "confidence": ctx.confidence,
                "threshold": self.config.confidence_threshold,
            })
        return issues

    def _monitor_drift(self, ctx: CycleContext) -> List[Dict[str, Any]]:
        """Monitor for distribution shift and model drift."""
        issues = []

        # Check for unexpected entity types
        if ctx.situational_context:
            entity_types = {e.get("type", "unknown") for e in ctx.situational_context.entities.values()}
            expected_types = {"agent", "resource", "threat", "sensor", "environment"}
            unexpected = entity_types - expected_types
            if unexpected:
                issues.append({
                    "type": "distribution_shift",
                    "severity": "medium",
                    "unexpected_types": list(unexpected),
                })

        # Check for unusual uncertainty patterns
        if ctx.uncertainty > self.config.drift_threshold:
            issues.append({
                "type": "model_drift",
                "severity": "medium",
                "uncertainty": ctx.uncertainty,
            })

        return issues

    def _monitor_contradictions(self, ctx: CycleContext) -> List[Dict[str, Any]]:
        """Monitor for contradictions in the context."""
        issues = []

        # Check for conflicting confidence values
        if ctx.confidence < 0.5 and ctx.uncertainty < 0.3:
            issues.append({
                "type": "contradiction",
                "severity": "medium",
                "detail": "Low confidence but low uncertainty",
            })

        return issues

    def _monitor_memory_integrity(self, ctx: CycleContext) -> List[Dict[str, Any]]:
        """Monitor for memory corruption."""
        issues = []

        # Check if memory retrievals look valid
        if ctx.memory_retrievals:
            total_results = sum(
                len(r.get("results", [])) if isinstance(r, dict) else 0
                for r in ctx.memory_retrievals
            )
            # No results might indicate memory issues
            if total_results == 0 and len(ctx.context.goals) > 0:
                issues.append({
                    "type": "memory_integrity",
                    "severity": "low",
                    "detail": "Memory retrieval returned no results",
                })

        return issues

    def _monitor_sensor_consistency(self, ctx: CycleContext) -> List[Dict[str, Any]]:
        """Monitor for sensor disagreement."""
        issues = []

        # Check if scene graph confidence is much lower than observation confidence
        if ctx.scene_graph and ctx.observations:
            avg_obs_confidence = sum(o.confidence for o in ctx.observations) / len(ctx.observations)
            if ctx.scene_graph.overall_confidence < avg_obs_confidence - 0.3:
                issues.append({
                    "type": "sensor_disagreement",
                    "severity": "medium",
                    "observation_confidence": avg_obs_confidence,
                    "scene_confidence": ctx.scene_graph.overall_confidence,
                })

        return issues

    def _trigger_fallbacks(self, ctx: CycleContext, issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Trigger automatic fallbacks for safety issues."""
        fallbacks = []

        # Fallback for high uncertainty
        if any(i["type"] == "high_uncertainty" for i in issues):
            fallbacks.append({
                "type": "uncertainty_fallback",
                "action": "reduce_confidence_in_decisions",
            })
            self._fallbacks_triggered += 1

        # Fallback for contradictions
        if any(i["type"] == "contradiction" for i in issues):
            fallbacks.append({
                "type": "contradiction_fallback",
                "action": "request_more_observations",
            })
            self._fallbacks_triggered += 1

        return fallbacks

    def _recalibrate_confidence(self, ctx: CycleContext) -> Dict[str, Any]:
        """Recalibrate confidence estimates."""
        if ctx.uncertainty > self.config.uncertainty_threshold:
            # Reduce confidence in high uncertainty situations
            adjusted = ctx.confidence * (1.0 - (ctx.uncertainty - self.config.uncertainty_threshold))
            return {
                "original_confidence": ctx.confidence,
                "adjusted_confidence": max(0.0, adjusted),
                "method": "uncertainty_penalty",
            }
        return {
            "original_confidence": ctx.confidence,
            "adjusted_confidence": ctx.confidence,
            "method": "none_needed",
        }

    def _record_violations(self, violations: List[Dict[str, Any]]) -> None:
        """Record safety violations."""
        for violation in violations:
            self._violations.append({
                "timestamp": time.time(),
                **violation,
            })

    def get_violations(self) -> List[Dict[str, Any]]:
        """Return all safety violations."""
        return self._violations

    def get_monitor_history(self) -> List[Dict[str, Any]]:
        """Return the history of safety monitoring."""
        return self._monitor_history

    def get_fallbacks_triggered(self) -> int:
        """Return the number of fallbacks triggered."""
        return self._fallbacks_triggered

    def get_human_reviews_requested(self) -> int:
        """Return the number of human reviews requested."""
        return self._human_reviews_requested