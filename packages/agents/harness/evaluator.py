# Copyright (c) Ultrone Contributors. All rights reserved.
"""Independent Fresh-Context Evaluator.

Enforces default-fail criteria: an executor cannot declare success by itself.
The evaluator evaluates strictly against the defined Goal and verifiable evidence
in an isolated, fresh context without reliance on the executor's internal scratchpad.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

from .schemas import EvaluationResult, EvaluationStatus, Goal

logger = logging.getLogger("Ultrone.Harness.Evaluator")


class IndependentEvaluator:
    """Read-only evaluator operating in a clean context."""

    def __init__(self, verifiers: Optional[Dict[str, Callable[[Any, Dict[str, Any]], bool]]] = None) -> None:
        self._custom_verifiers: Dict[str, Callable[[Any, Dict[str, Any]], bool]] = verifiers or {}

    def register_verifier(self, name: str, func: Callable[[Any, Dict[str, Any]], bool]) -> None:
        """Register a domain-specific assertion verifier."""
        self._custom_verifiers[name] = func

    def evaluate(
        self,
        goal: Goal,
        candidate_output: Any,
        evidence: Optional[Dict[str, Any]] = None,
    ) -> EvaluationResult:
        """Evaluate candidate output against goal criteria with default-fail semantics.

        Parameters
        ----------
        goal: Goal
            The original goal specification including acceptance criteria.
        candidate_output: Any
            The final result or artifact produced by the executor.
        evidence: Optional[Dict[str, Any]]
            Verifiable evidence (test outputs, execution logs, file checks, hashes).

        Returns
        -------
        EvaluationResult
            PASS or FAIL with detailed rubric scores and failed criteria list.
        """
        evidence = evidence or {}

        # Default-fail: if output is None or empty string/dict, fail immediately
        if candidate_output is None or (isinstance(candidate_output, (str, list, dict)) and len(candidate_output) == 0):
            return EvaluationResult(
                status=EvaluationStatus.FAIL,
                score=0.0,
                reason="Default-fail: Candidate output is empty or None.",
                failed_criteria=list(goal.acceptance_criteria) or ["Non-empty output"],
                evidence=evidence,
            )

        passed_criteria: List[str] = []
        failed_criteria: List[str] = []

        # 1. If explicit acceptance criteria exist, check each
        if goal.acceptance_criteria:
            for crit in goal.acceptance_criteria:
                crit_passed = self._check_criterion(crit, candidate_output, evidence)
                if crit_passed:
                    passed_criteria.append(crit)
                else:
                    failed_criteria.append(crit)

            total = len(goal.acceptance_criteria)
            score = len(passed_criteria) / total if total > 0 else 0.0

            if failed_criteria:
                return EvaluationResult(
                    status=EvaluationStatus.FAIL,
                    score=score,
                    reason=f"Failed {len(failed_criteria)} of {total} criteria: {failed_criteria}",
                    passed_criteria=passed_criteria,
                    failed_criteria=failed_criteria,
                    evidence=evidence,
                )
        else:
            # If no explicit criteria provided, apply default baseline check
            score = 1.0
            passed_criteria.append("Output generated")

        # 2. Check negative constraints
        for constraint in goal.constraints:
            constraint_violated = self._check_constraint_violation(constraint, candidate_output, evidence)
            if constraint_violated:
                return EvaluationResult(
                    status=EvaluationStatus.FAIL,
                    score=0.0,
                    reason=f"Constraint violation: {constraint}",
                    passed_criteria=passed_criteria,
                    failed_criteria=[f"CONSTRAINT: {constraint}"],
                    evidence=evidence,
                )

        # 3. Check custom verifiers if specified in evidence
        for verifier_name, func in self._custom_verifiers.items():
            try:
                if not func(candidate_output, evidence):
                    return EvaluationResult(
                        status=EvaluationStatus.FAIL,
                        score=score * 0.5,
                        reason=f"Verifier {verifier_name} rejected candidate output.",
                        passed_criteria=passed_criteria,
                        failed_criteria=[f"VERIFIER: {verifier_name}"],
                        evidence=evidence,
                    )
            except Exception as e:
                logger.error("Verifier error in %s: %s", verifier_name, e)
                return EvaluationResult(
                    status=EvaluationStatus.FAIL,
                    score=0.0,
                    reason=f"Verifier {verifier_name} threw an exception: {e}",
                    failed_criteria=[f"VERIFIER_ERROR: {verifier_name}"],
                    evidence=evidence,
                )

        return EvaluationResult(
            status=EvaluationStatus.PASS,
            score=score,
            reason="All acceptance criteria and constraints satisfied.",
            passed_criteria=passed_criteria,
            failed_criteria=[],
            evidence=evidence,
        )

    def _check_criterion(self, criterion: str, output: Any, evidence: Dict[str, Any]) -> bool:
        """Check whether a single criterion is verified by the candidate or evidence."""
        # 1. Direct evidence match
        if criterion in evidence:
            val = evidence[criterion]
            return bool(val and val is not False and val != 0 and val != "FAIL")

        # 2. String search in text output
        if isinstance(output, str):
            return criterion.lower() in output.lower()

        # 3. Dict key check
        if isinstance(output, dict):
            if criterion in output:
                return bool(output[criterion])
            for k, v in output.items():
                if criterion.lower() in str(k).lower() or criterion.lower() in str(v).lower():
                    return True

        return False

    def _check_constraint_violation(self, constraint: str, output: Any, evidence: Dict[str, Any]) -> bool:
        """Return True if a negative constraint is violated."""
        # Check if forbidden terms appear in output
        if isinstance(output, str) and constraint.lower() in output.lower():
            return True
        return False
