# Copyright (c) Ultrone Contributors. All rights reserved.
import pytest

from packages.agents.harness.evaluator import IndependentEvaluator
from packages.agents.harness.schemas import EvaluationStatus, Goal


def test_evaluator_default_fail_on_empty_output():
    evaluator = IndependentEvaluator()
    goal = Goal(description="Produce report", acceptance_criteria=["Report summary"])

    res_none = evaluator.evaluate(goal, None)
    assert res_none.status == EvaluationStatus.FAIL
    assert not res_none.passed

    res_empty = evaluator.evaluate(goal, "")
    assert res_empty.status == EvaluationStatus.FAIL
    assert not res_empty.passed


def test_evaluator_passes_when_criteria_met():
    evaluator = IndependentEvaluator()
    goal = Goal(
        description="Run security scan",
        acceptance_criteria=["Zero critical vulnerabilities", "Audit logged"],
    )

    output = "Security scan complete. Audit logged. Zero critical vulnerabilities found."
    result = evaluator.evaluate(goal, output)

    assert result.status == EvaluationStatus.PASS
    assert result.passed
    assert result.score == 1.0
    assert len(result.failed_criteria) == 0


def test_evaluator_fails_when_criterion_missing():
    evaluator = IndependentEvaluator()
    goal = Goal(
        description="Run benchmark",
        acceptance_criteria=["Latency < 5ms", "Throughput > 1000"],
    )

    output = {"Latency < 5ms": True, "Throughput": 500}
    evidence = {"Latency < 5ms": True}
    result = evaluator.evaluate(goal, output, evidence)

    assert result.status == EvaluationStatus.FAIL
    assert not result.passed
    assert "Throughput > 1000" in result.failed_criteria


def test_evaluator_custom_verifier():
    evaluator = IndependentEvaluator()

    def must_have_valid_checksum(output, evidence):
        return evidence.get("checksum_valid", False) is True

    evaluator.register_verifier("checksum_verifier", must_have_valid_checksum)

    goal = Goal(description="Download payload", acceptance_criteria=["payload"])
    output = "Downloaded payload"

    # Fails without valid checksum in evidence
    res_fail = evaluator.evaluate(goal, output, evidence={"checksum_valid": False})
    assert not res_fail.passed

    # Passes with valid checksum in evidence
    res_pass = evaluator.evaluate(goal, output, evidence={"checksum_valid": True})
    assert res_pass.passed
