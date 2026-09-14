# Copyright (c) Ultrone Contributors. All rights reserved.
from packages.agents.harness.recovery import RecoveryAction, RecoveryManager
from packages.agents.harness.schemas import EvaluationResult, EvaluationStatus


def test_recovery_retry_then_escalate():
    rm = RecoveryManager(max_retries=2)
    task_id = "test-task-rec"

    action1 = rm.decide_recovery(task_id, "Temporary network timeout")
    assert action1 == RecoveryAction.RETRY_STEP

    action2 = rm.decide_recovery(task_id, "Temporary network timeout")
    assert action2 == RecoveryAction.RETRY_STEP

    # 3rd attempt exceeds max_retries=2 -> ESCALATE_HUMAN
    action3 = rm.decide_recovery(task_id, "Temporary network timeout")
    assert action3 == RecoveryAction.ESCALATE_HUMAN


def test_recovery_context_compaction_trigger():
    rm = RecoveryManager(max_retries=3)
    task_id = "test-ctx"

    eval_result = EvaluationResult(
        status=EvaluationStatus.FAIL,
        reason="Context length exceeded model window limit",
    )
    action = rm.decide_recovery(task_id, eval_result)
    assert action == RecoveryAction.COMPACT_CONTEXT
