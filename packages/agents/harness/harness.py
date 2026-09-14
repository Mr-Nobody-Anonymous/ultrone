# Copyright (c) Ultrone Contributors. All rights reserved.
"""AgentHarness: The central long-running agent execution engine.

Coordinates Goal -> Plan -> Execute -> Observe -> Evaluate -> Checkpoint -> Recovery loop
with independent fresh-context evaluation, worker adapters, and persistent resume across restarts.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Union

from .checkpoint import CheckpointStore
from .evaluator import IndependentEvaluator
from .events import HarnessEvent, HarnessEventType
from .goal import GoalManager
from .lifecycle import LifecycleStateMachine
from .policies import ExecutionPolicy
from .recovery import RecoveryAction, RecoveryManager
from .schemas import (
    CheckpointData,
    EvaluationResult,
    ExecutionStep,
    Goal,
    HarnessConfig,
    LifecycleState,
)

logger = logging.getLogger("Ultrone.Harness")


class AgentHarness:
    """Universal execution harness for ULTRONE agents."""

    def __init__(
        self,
        config: Optional[HarnessConfig] = None,
        evaluator: Optional[IndependentEvaluator] = None,
        checkpoint_store: Optional[CheckpointStore] = None,
        policy: Optional[ExecutionPolicy] = None,
        context_manager: Optional[Any] = None,
        model_gateway: Optional[Any] = None,
        tool_runtime: Optional[Any] = None,
        liveness_watchdog: Optional[Any] = None,
        worker_selector: Optional[Any] = None,
        tracer: Optional[Any] = None,
    ) -> None:
        self.config = config or HarnessConfig()
        self.evaluator = evaluator or IndependentEvaluator()
        self.checkpoint_store = checkpoint_store or CheckpointStore(self.config.checkpoint_dir)
        self.policy = policy or ExecutionPolicy()
        self.recovery_manager = RecoveryManager(
            max_retries=self.config.max_retries_per_step,
            checkpoint_store=self.checkpoint_store,
        )

        # Core subsystem integrations
        self.context_manager = context_manager
        self.model_gateway = model_gateway
        self.tool_runtime = tool_runtime
        self.liveness_watchdog = liveness_watchdog
        self.worker_selector = worker_selector
        self.tracer = tracer

        self.state_machine = LifecycleStateMachine(LifecycleState.CREATED)
        self.events: List[HarnessEvent] = []
        self._step_handlers: Dict[str, Callable[[ExecutionStep, Dict[str, Any]], Dict[str, Any]]] = {}

    def register_action_handler(
        self, action: str, handler: Callable[[ExecutionStep, Dict[str, Any]], Dict[str, Any]]
    ) -> None:
        """Register a handler function for an execution action."""
        self._step_handlers[action] = handler

    def emit_event(self, event_type: HarnessEventType, task_id: str, payload: Optional[Dict[str, Any]] = None) -> None:
        """Record and log a harness lifecycle event."""
        event = HarnessEvent(
            event_type=event_type,
            task_id=task_id,
            payload=payload or {},
        )
        self.events.append(event)
        logger.debug("Harness event: %s for task %s", event_type.value, task_id)

    def run(
        self,
        goal: Goal | str,
        executor_fn: Optional[Callable[[Dict[str, Any]], Any]] = None,
        worker: Optional[Any] = None,
        task_id: Optional[str] = None,
        initial_state: Optional[Dict[str, Any]] = None,
        domain: Optional[str] = None,
        required_capabilities: Optional[List[str]] = None,
    ) -> EvaluationResult:
        """Execute task through full Goal -> Plan -> Execute -> Evaluate -> Checkpoint loop."""
        task_id = task_id or f"task-{uuid.uuid4().hex[:8]}"
        run_id = f"run-{uuid.uuid4().hex[:8]}"

        # Start OpenTelemetry distributed trace if tracer is provided
        span = None
        if self.tracer:
            span = self.tracer.start_span("AgentHarness.run")
            span.attributes.update({
                "task_id": task_id,
                "run_id": run_id,
                "model": self.config.model_name,
            })

        if isinstance(goal, str):
            parsed_goal = GoalManager.parse_from_prompt(goal)
        else:
            parsed_goal = goal
            parsed_goal.validate()

        self.emit_event(HarnessEventType.HARNESS_STARTED, task_id, {"goal": parsed_goal.description, "run_id": run_id})

        # Resolve worker if not provided directly
        active_worker = worker
        if not active_worker and self.worker_selector:
            active_worker = self.worker_selector.select_worker(
                domain=domain,
                required_capabilities=required_capabilities,
            )

        agent_id = getattr(active_worker, "worker_id", "harness-executor")
        if span:
            span.attributes["agent_id"] = agent_id

        # 1. State: CREATED -> PLANNING (reset state machine if previous run was terminal)
        if self.state_machine.current_state.is_terminal:
            self.state_machine = LifecycleStateMachine(LifecycleState.CREATED)

        self.state_machine.transition(LifecycleState.PLANNING, reason="Creating initial plan")
        self.emit_event(HarnessEventType.PLAN_CREATED, task_id, {"criteria": parsed_goal.acceptance_criteria})

        working_state = dict(initial_state or {})
        completed_steps: List[Dict[str, Any]] = []
        failed_steps: List[Dict[str, Any]] = []

        # 2. State: PLANNING -> READY -> EXECUTING
        self.state_machine.transition(LifecycleState.READY, reason="Plan ready")
        self.state_machine.transition(LifecycleState.EXECUTING, reason="Executing plan")

        candidate_output: Any = None
        evidence: Dict[str, Any] = {}
        retries_remaining = self.config.max_retries_per_step

        while retries_remaining >= 0:
            step_start = time.time()
            retry_count = self.config.max_retries_per_step - retries_remaining
            self.emit_event(HarnessEventType.STEP_STARTED, task_id, {"retry": retry_count})

            # Check liveness of active worker
            if self.liveness_watchdog:
                self.liveness_watchdog.check_and_recover()

            try:
                if active_worker and hasattr(active_worker, "execute"):
                    # Use WorkerInput contract
                    from .workers.base_worker import WorkerInput
                    w_input = WorkerInput(
                        task_id=task_id,
                        goal_description=parsed_goal.description,
                        parameters=working_state,
                    )
                    worker_out = active_worker.execute(w_input)
                    if not worker_out.success:
                        raise RuntimeError(worker_out.error or "Worker execution signaled failure")
                    candidate_output = worker_out.result
                    evidence.update(worker_out.evidence)

                elif executor_fn:
                    candidate_output = executor_fn(working_state)
                else:
                    candidate_output = working_state

                # Step completed
                duration = (time.time() - step_start) * 1000.0
                step_record = ExecutionStep(
                    action="execute_plan",
                    status="SUCCESS",
                    input_data=working_state,
                    output_data=candidate_output if isinstance(candidate_output, dict) else {"result": candidate_output},
                    duration_ms=duration,
                )
                completed_steps.append(step_record.__dict__)
                self.emit_event(HarnessEventType.STEP_COMPLETED, task_id, {"step": step_record.step_id})
                break

            except Exception as exc:
                duration = (time.time() - step_start) * 1000.0
                err_str = str(exc)
                logger.warning("Step failed during execution of %s: %s", task_id, err_str)
                step_record = ExecutionStep(
                    action="execute_plan",
                    status="FAILED",
                    input_data=working_state,
                    error=err_str,
                    duration_ms=duration,
                )
                failed_steps.append(step_record.__dict__)
                self.emit_event(HarnessEventType.STEP_FAILED, task_id, {"error": err_str})

                action = self.recovery_manager.decide_recovery(task_id, exc)
                if action == RecoveryAction.TERMINATE or retries_remaining == 0:
                    self.state_machine.transition(LifecycleState.FAILED, reason=f"Execution failed: {err_str}")
                    self.emit_event(HarnessEventType.HARNESS_FAILED, task_id, {"error": err_str})
                    if span:
                        span.status = "error"
                        span.end()
                    return EvaluationResult(
                        status=EvaluationResult().status,  # default FAIL
                        score=0.0,
                        reason=f"Execution error: {err_str}",
                    )

                retries_remaining -= 1

        # 3. State: EXECUTING -> OBSERVING
        self.state_machine.transition(LifecycleState.OBSERVING, reason="Collecting execution observations and evidence")
        evidence["completed_steps_count"] = len(completed_steps)
        if isinstance(candidate_output, dict):
            evidence.update({k: v for k, v in candidate_output.items() if k in parsed_goal.acceptance_criteria})
        self.emit_event(HarnessEventType.OBSERVATION_COLLECTED, task_id, {"evidence_keys": list(evidence.keys())})

        # 4. State: OBSERVING -> VERIFYING (Independent Evaluator)
        self.state_machine.transition(LifecycleState.VERIFYING, reason="Independent fresh-context evaluation")
        self.emit_event(HarnessEventType.EVALUATION_STARTED, task_id)

        eval_result = self.evaluator.evaluate(parsed_goal, candidate_output, evidence)

        # 5. Branch on evaluation outcome: PASS -> COMPLETED, FAIL -> RECOVERING / FAILED
        if eval_result.passed:
            self.state_machine.transition(LifecycleState.COMPLETED, reason="Evaluation passed successfully")
            self.emit_event(HarnessEventType.EVALUATION_PASSED, task_id, {"score": eval_result.score})
            self.emit_event(HarnessEventType.HARNESS_COMPLETED, task_id)
            self.recovery_manager.reset(task_id)
            if span:
                span.status = "ok"
        else:
            self.state_machine.transition(LifecycleState.RECOVERING, reason=f"Evaluation failed: {eval_result.reason}")
            self.emit_event(HarnessEventType.EVALUATION_FAILED, task_id, {"reason": eval_result.reason})

            # Check if recoverable
            rec_action = self.recovery_manager.decide_recovery(task_id, eval_result)
            if rec_action == RecoveryAction.TERMINATE or rec_action == RecoveryAction.ESCALATE_HUMAN:
                self.state_machine.transition(LifecycleState.FAILED, reason=f"Unrecoverable evaluation failure: {eval_result.reason}")
                self.emit_event(HarnessEventType.HARNESS_FAILED, task_id, {"reason": eval_result.reason})
            if span:
                span.status = "error"

        # 6. Save final checkpoint reflecting outcome state
        if self.config.auto_checkpoint:
            checkpoint = CheckpointData(
                task_id=task_id,
                goal=parsed_goal.__dict__,
                current_phase=self.state_machine.current_state.value,
                completed_steps=completed_steps,
                failed_steps=failed_steps,
                working_state=working_state,
                model=self.config.model_name,
            )
            self.checkpoint_store.save(checkpoint)
            self.emit_event(HarnessEventType.CHECKPOINT_SAVED, task_id)

        if span:
            span.end()

        return eval_result

    def resume_from_checkpoint(
        self,
        task_id: str,
        executor_fn: Optional[Callable[[Dict[str, Any]], Any]] = None,
        worker: Optional[Any] = None,
    ) -> EvaluationResult:
        """Resume execution of an interrupted task from its last checkpoint."""
        checkpoint = self.checkpoint_store.load_latest(task_id)
        if not checkpoint:
            raise ValueError(f"No checkpoint found for task {task_id}")

        self.emit_event(HarnessEventType.CHECKPOINT_RESTORED, task_id, {"phase": checkpoint.current_phase})
        goal = Goal(
            description=checkpoint.goal.get("description", "Resumed goal"),
            acceptance_criteria=checkpoint.goal.get("acceptance_criteria", []),
            constraints=checkpoint.goal.get("constraints", []),
            metadata=checkpoint.goal.get("metadata", {}),
        )

        return self.run(
            goal=goal,
            executor_fn=executor_fn,
            worker=worker,
            task_id=task_id,
            initial_state=checkpoint.working_state,
        )
