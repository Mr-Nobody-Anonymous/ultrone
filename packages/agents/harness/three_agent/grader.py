# Copyright (c) Ultrone Contributors. All rights reserved.
"""ROEGrader: Independent Fresh-Context Evaluator and ROE Safety Gatekeeper."""

from __future__ import annotations

import logging
import math
import uuid
from typing import Any, Dict, List, Optional, Tuple

from packages.agents.harness.evaluator import IndependentEvaluator
from packages.agents.harness.schemas import EvaluationResult, EvaluationStatus, Goal
from .dag import DAGNode

logger = logging.getLogger("Ultrone.Harness.Grader")


class ROEGrader(IndependentEvaluator):
    """Independent Safety & Rules of Engagement Gatekeeper with default-fail semantics."""

    def __init__(
        self,
        min_pid_confidence: float = 0.85,
        no_strike_entities: Optional[List[Dict[str, Any]]] = None,
        max_cde_radius_m: float = 150.0,
    ) -> None:
        super().__init__()
        self.min_pid_confidence = min_pid_confidence
        self.no_strike_entities = no_strike_entities or []
        self.max_cde_radius_m = max_cde_radius_m

    def add_no_strike_entity(self, name: str, lat: float, lon: float, buffer_m: float = 300.0) -> None:
        """Register a protected hospital, school, cultural, or diplomatic site."""
        self.no_strike_entities.append({
            "name": name,
            "lat": lat,
            "lon": lon,
            "buffer_m": buffer_m,
        })

    def grade_node_execution(
        self,
        node: DAGNode,
        candidate_output: Any,
        evidence: Optional[Dict[str, Any]] = None,
    ) -> Tuple[EvaluationResult, Optional[str]]:
        """Evaluate a completed DAG node in an isolated fresh context.

        Returns (EvaluationResult, Optional[roe_clearance_token]).
        """
        evidence = evidence or {}

        # 1. Base Goal evaluation with default-fail semantics
        goal = Goal(
            description=node.description,
            acceptance_criteria=node.acceptance_criteria,
            constraints=node.constraints,
        )
        base_result = self.evaluate(goal, candidate_output, evidence)

        if not base_result.passed:
            logger.warning("Grader REJECTED node '%s': %s", node.node_id, base_result.reason)
            return base_result, None

        # 2. Stage-Specific Strict ROE Verification
        # Check Positive Identification (PID) confidence
        if node.phase in ("TRACK", "TARGET", "ENGAGE"):
            pid_score = evidence.get("pid_score", 0.0)
            if pid_score < self.min_pid_confidence:
                reason = f"PID confidence {pid_score:.2f} is below mandatory threshold {self.min_pid_confidence:.2f}"
                logger.error("ROE VIOLATION BLOCKED: %s", reason)
                return (
                    EvaluationResult(
                        status=EvaluationStatus.FAIL,
                        score=0.0,
                        reason=reason,
                        failed_criteria=[f"PID >= {self.min_pid_confidence}"],
                        evidence=evidence,
                    ),
                    None,
                )

        # Check No-Strike List (NSL) proximity for kinetic / target nodes
        target_lat = (
            evidence.get("lat")
            or evidence.get("target_lat")
            or node.parameters.get("lat")
            or node.parameters.get("target_lat")
        )
        target_lon = (
            evidence.get("lon")
            or evidence.get("target_lon")
            or node.parameters.get("lon")
            or node.parameters.get("target_lon")
        )
        if target_lat is not None and target_lon is not None and node.phase in ("TARGET", "ENGAGE"):
            t_lat = float(target_lat)
            t_lon = float(target_lon)
            for nse in self.no_strike_entities:
                dist_m = self._distance_m(t_lat, t_lon, nse["lat"], nse["lon"])
                if dist_m < nse["buffer_m"]:
                    reason = f"Target coordinates within buffer ({dist_m:.1f}m < {nse['buffer_m']}m) of protected No-Strike entity '{nse['name']}'"
                    logger.error("ROE VIOLATION BLOCKED: %s", reason)
                    return (
                        EvaluationResult(
                            status=EvaluationStatus.FAIL,
                            score=0.0,
                            reason=reason,
                            failed_criteria=["No-Strike List Compliance"],
                            evidence=evidence,
                        ),
                        None,
                    )


        # If ENGAGE phase successfully passes all checks, generate a one-time cryptographic ROE token
        clearance_token = None
        if node.phase in ("TARGET", "ENGAGE"):
            clearance_token = f"ROE-CLEARED-{uuid.uuid4().hex[:12].upper()}"
            evidence["roe_clearance_token"] = clearance_token
            logger.info("Grader issued valid ROE Clearance Token: %s", clearance_token)

        return base_result, clearance_token

    @staticmethod
    def _distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        r = 6371000.0
        p1 = math.radians(lat1)
        p2 = math.radians(lat2)
        dp = math.radians(lat2 - lat1)
        dl = math.radians(lon2 - lon1)
        a = math.sin(dp / 2.0) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2.0) ** 2
        return r * 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
