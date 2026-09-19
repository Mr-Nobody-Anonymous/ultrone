# Copyright (c) Ultrone Contributors. All rights reserved.
"""ThreeAgentHarness: Orchestrates Planner, Worker, and Grader in an integrated F2T2EA loop."""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from packages.agents.harness.checkpoint import CheckpointStore
from packages.agents.harness.recovery import RecoveryAction, RecoveryManager
from packages.agents.harness.schemas import CheckpointData, EvaluationStatus
from .dag import DAGNode, NodeStatus, TaskDAG
from .grader import ROEGrader
from .planner import F2T2EAPlanner, MissionDirective
from .worker import SwarmExecutionWorker

logger = logging.getLogger("Ultrone.Harness.ThreeAgent")


@dataclass
class MissionExecutionReport:
    """Consolidated report for a Three-Agent operational mission."""

    mission_id: str
    success: bool
    nodes_total: int
    nodes_completed: int
    nodes_failed: int
    roe_clearance_issued: bool
    violations: List[str] = field(default_factory=list)
    checkpoints: List[str] = field(default_factory=list)
    duration_ms: float = 0.0


class ThreeAgentHarness:
    """The central Three-Agent harness executing decoupled Planner -> Worker -> Grader workflows."""

    def __init__(
        self,
        planner: Optional[F2T2EAPlanner] = None,
        worker: Optional[SwarmExecutionWorker] = None,
        grader: Optional[ROEGrader] = None,
        checkpoint_store: Optional[CheckpointStore] = None,
        recovery_manager: Optional[RecoveryManager] = None,
    ) -> None:
        self.planner = planner or F2T2EAPlanner()
        self.worker = worker or SwarmExecutionWorker()
        self.grader = grader or ROEGrader()
        self.checkpoint_store = checkpoint_store or CheckpointStore()
        self.recovery_manager = recovery_manager or RecoveryManager(max_retries=2)

    def execute_mission(self, directive: MissionDirective) -> MissionExecutionReport:
        """Run the full Three-Agent operational kill-chain from directive to post-strike assessment."""
        start_time = time.time()
        logger.info("Initializing Three-Agent mission '%s'...", directive.mission_id)

        # 1. PLANNER: Compile Directive into immutable TaskDAG
        dag = self.planner.plan_mission(directive)

        shared_context: Dict[str, Any] = {
            "mission_id": directive.mission_id,
            "target_description": directive.target_description,
        }
        checkpoints_saved: List[str] = []
        violations: List[str] = []
        roe_issued = False

        # 2. WORKER & GRADER Loop across DAG stages
        while not dag.is_finished():
            ready_nodes = dag.get_ready_nodes()
            if not ready_nodes:
                logger.warning("No nodes ready to execute in DAG. Breaking loop.")
                break

            for node in ready_nodes:
                logger.info("Executing phase [%s] node '%s'", node.phase, node.node_id)

                # WORKER: executes the node
                worker_res = self.worker.execute_node(node, dag, shared_context)

                # If worker failed at tool level, attempt recovery
                if not worker_res["success"]:
                    action = self.recovery_manager.record_failure(node.node_id, worker_res["error"] or "Unknown tool error")
                    if action == RecoveryAction.RETRY:
                        logger.info("Retrying node '%s'...", node.node_id)
                        worker_res = self.worker.execute_node(node, dag, shared_context)
                    elif action == RecoveryAction.ABORT:
                        dag.mark_failed(node.node_id, worker_res["error"] or "Aborted")
                        violations.append(f"Worker execution failure on node '{node.node_id}'")
                        break

                # GRADER: Evaluate candidate output in independent fresh context
                eval_res, token = self.grader.grade_node_execution(
                    node=node,
                    candidate_output=worker_res["output"],
                    evidence=worker_res["evidence"],
                )

                if eval_res.passed:
                    dag.mark_completed(node.node_id, worker_res["output"], worker_res["evidence"])
                    if worker_res.get("evidence"):
                        for k in ("pid_score", "classification", "target_id", "lat", "lon", "target_lat", "target_lon"):
                            if k in worker_res["evidence"]:
                                shared_context[k] = worker_res["evidence"][k]
                    if token:
                        shared_context["roe_clearance_token"] = token
                        roe_issued = True


                    # CHECKPOINT STORE: Persist state after successful grading
                    ckpt_data = CheckpointData(
                        task_id=f"{directive.mission_id}-{node.node_id}",
                        goal={"phase": node.phase, "description": node.description},
                        current_phase=node.phase,
                        completed_steps=[{"node_id": node.node_id, "output": worker_res["output"]}],
                        working_state=shared_context,
                    )
                    cp_id = self.checkpoint_store.save(ckpt_data)
                    checkpoints_saved.append(cp_id)
                else:
                    dag.mark_failed(node.node_id, eval_res.reason)
                    violations.append(f"Grader rejected node '{node.node_id}': {eval_res.reason}")
                    logger.error("Grader halted execution of '%s'. Reason: %s", node.node_id, eval_res.reason)
                    break

        duration_ms = (time.time() - start_time) * 1000.0
        completed_count = sum(1 for n in dag.nodes.values() if n.status == NodeStatus.COMPLETED)
        failed_count = sum(1 for n in dag.nodes.values() if n.status == NodeStatus.FAILED)
        is_success = dag.is_successful()

        report = MissionExecutionReport(
            mission_id=directive.mission_id,
            success=is_success,
            nodes_total=len(dag.nodes),
            nodes_completed=completed_count,
            nodes_failed=failed_count,
            roe_clearance_issued=roe_issued,
            violations=violations,
            checkpoints=checkpoints_saved,
            duration_ms=duration_ms,
        )
        logger.info(
            "Mission '%s' finished with success=%s in %.1fms (Completed %d/%d nodes)",
            directive.mission_id,
            is_success,
            duration_ms,
            completed_count,
            len(dag.nodes),
        )
        return report
