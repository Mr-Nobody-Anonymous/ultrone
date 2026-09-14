# Copyright (c) Ultrone Contributors. All rights reserved.
import tempfile

from packages.agents.harness.checkpoint import CheckpointStore
from packages.agents.harness.evaluator import IndependentEvaluator
from packages.agents.harness.harness import AgentHarness
from packages.agents.harness.schemas import EvaluationStatus, Goal, HarnessConfig, LifecycleState


def test_harness_successful_run():
    with tempfile.TemporaryDirectory() as tmpdir:
        config = HarnessConfig(checkpoint_dir=tmpdir, auto_checkpoint=True)
        harness = AgentHarness(config=config)

        goal = Goal(
            description="Process dataset batch",
            acceptance_criteria=["processed_count", "valid_checksum"],
        )

        def mock_executor(state):
            return {
                "processed_count": 100,
                "valid_checksum": True,
                "status": "done",
            }

        result = harness.run(goal=goal, executor_fn=mock_executor, task_id="task-success-1")

        assert result.status == EvaluationStatus.PASS
        assert result.passed
        assert harness.state_machine.current_state == LifecycleState.COMPLETED

        # Verify checkpoint was written
        latest_cp = harness.checkpoint_store.load_latest("task-success-1")
        assert latest_cp is not None
        assert latest_cp.task_id == "task-success-1"


def test_harness_failed_evaluation_triggers_recovery_and_failure():
    harness = AgentHarness(config=HarnessConfig(max_retries_per_step=1))
    goal = Goal(
        description="Strict compliance task",
        acceptance_criteria=["mandatory_signed_cert"],
    )

    def failing_executor(state):
        # Missing mandatory_signed_cert
        return {"unsigned_data": "raw"}

    result = harness.run(goal=goal, executor_fn=failing_executor, task_id="task-fail-1")

    assert result.status == EvaluationStatus.FAIL
    assert not result.passed
    assert "mandatory_signed_cert" in result.failed_criteria


def test_harness_resume_from_checkpoint():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = CheckpointStore(storage_dir=tmpdir)
        config = HarnessConfig(checkpoint_dir=tmpdir)
        harness = AgentHarness(config=config, checkpoint_store=store)

        # 1. Run step 1 and stop
        goal = Goal(
            description="Multi-stage task",
            acceptance_criteria=["stage_1_done", "stage_2_done"],
        )

        def partial_executor(state):
            return {"stage_1_done": True}

        harness.run(goal=goal, executor_fn=partial_executor, task_id="task-resume-test")

        # 2. Resume with updated executor that completes stage 2
        def complete_executor(state):
            return {"stage_1_done": True, "stage_2_done": True}

        resumed_harness = AgentHarness(config=config, checkpoint_store=store)
        resumed_result = resumed_harness.resume_from_checkpoint(
            task_id="task-resume-test",
            executor_fn=complete_executor,
        )

        assert resumed_result.status == EvaluationStatus.PASS
        assert resumed_harness.state_machine.current_state == LifecycleState.COMPLETED
