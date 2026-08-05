# Copyright (c) Ultrone Contributors. All rights reserved.
"""Planning Layer — multi-horizon planning subsystem.

Supports planning at multiple horizons: reactive, tactical, operational,
strategic, and long-term. Uses multiple planners including behavior trees,
HTN, GOAP, utility AI, MCTS, constraint optimization, model predictive
control, multi-agent planning, and hierarchical planning.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .base_layer import CognitiveLayer, LayerConfig
from .cycle_context import CycleContext, CyclePhase, PhaseResult
from .event_types import CognitiveEventType
from .types import (
    Action,
    Plan,
    PlanStep,
    PlannerType,
    PlanningHorizon,
    UncertaintyEstimate,
    UncertaintyType,
)

logger = logging.getLogger("Ultrone.Cognitive.Planning")


@dataclass
class PlanningLayerConfig(LayerConfig):
    """Configuration for the planning layer."""
    name: str = "planning"
    default_planner: PlannerType = PlannerType.GOAP
    enable_planner_selection: bool = True
    enable_hierarchical_planning: bool = True
    enable_multi_agent_planning: bool = True
    max_plan_steps: int = 20
    max_alternatives: int = 3
    planning_horizons: List[PlanningHorizon] = field(
        default_factory=lambda: [
            PlanningHorizon.REACTIVE,
            PlanningHorizon.TACTICAL,
            PlanningHorizon.OPERATIONAL,
            PlanningHorizon.STRATEGIC,
        ]
    )


class PlanningLayer(CognitiveLayer):
    """Multi-horizon planning subsystem.

    The planning layer:
    1. Selects the appropriate planner dynamically
    2. Generates plans at multiple time horizons
    3. Evaluates plan alternatives
    4. Produces executable actions
    5. Tracks planner performance
    """

    def __init__(self, config: Optional[PlanningLayerConfig] = None):
        super().__init__(config or PlanningLayerConfig())
        self._plan_history: List[Plan] = []
        self._planner_performance: Dict[PlannerType, List[float]] = {}

    def _layer_phase(self) -> CyclePhase:
        return CyclePhase.PLAN

    def process(self, ctx: CycleContext) -> PhaseResult:
        """Execute the planning phase.

        Parameters
        ----------
        ctx : CycleContext
            The shared cycle context.

        Returns
        -------
        PhaseResult
            Result with the generated plan and actions.
        """
        start = time.time()

        # 1. Select planner
        planner = self._select_planner(ctx)

        # 2. Generate plan
        plan = self._generate_plan(planner, ctx)

        # 3. Generate alternatives
        alternatives = self._generate_alternatives(planner, ctx)
        plan.alternatives = alternatives

        # 4. Derive actions from plan
        actions = self._derive_actions(plan, ctx)

        # 5. Store in context
        ctx.plan = plan
        ctx.actions = actions

        # 6. Publish event
        self._publish_event(
            CognitiveEventType.PLANNING,
            {
                "plan_id": plan.plan_id,
                "goal": plan.goal,
                "steps_count": len(plan.steps),
                "planner_type": plan.planner_type.value,
                "confidence": plan.confidence,
            },
        )

        # 7. Track planner performance
        self._track_planner_performance(planner, plan.confidence)

        # 8. Create decision trace
        trace = self._create_trace(
            decision=f"Plan for goal: {plan.goal}",
            confidence=plan.confidence,
            evidence=[
                {
                    "source": "planning",
                    "description": f"Generated plan with {len(plan.steps)} steps using {planner.value}",
                    "confidence": plan.confidence,
                }
            ],
        )
        trace.uncertainty = UncertaintyEstimate(
            epistemic=1.0 - plan.confidence,
            aleatoric=0.0,
            total=1.0 - plan.confidence,
            type=UncertaintyType.EPISTEMIC,
            contributing_factors=["planning_uncertainty"],
        )

        self._plan_history.append(plan)
        if len(self._plan_history) > 100:
            self._plan_history = self._plan_history[-100:]

        return PhaseResult(
            phase=self._phase,
            success=True,
            duration_seconds=time.time() - start,
            output={
                "plan": plan.to_dict(),
                "actions": [a.to_dict() for a in actions],
                "alternatives": len(alternatives),
                "planner_type": planner.value,
            },
            trace=trace,
        )

    def _select_planner(self, ctx: CycleContext) -> PlannerType:
        """Select the appropriate planner dynamically."""
        if not self.config.enable_planner_selection:
            return self.config.default_planner

        # Select based on context
        uncertainty = ctx.uncertainty if ctx.uncertainty > 0 else 0.5

        if uncertainty > 0.7:
            return PlannerType.MCTS
        elif ctx.context.time_horizon > 3600:
            return PlannerType.HIERARCHICAL
        elif len(ctx.context.goals) > 1:
            return PlannerType.GOAP
        elif ctx.context.constraints:
            return PlannerType.CONSTRAINT_OPTIMIZATION
        else:
            return PlannerType.UTILITY_AI

    def _generate_plan(self, planner: PlannerType, ctx: CycleContext) -> Plan:
        """Generate a plan using the selected planner."""
        goal = ctx.context.goals[0] if ctx.context.goals else "achieve_objective"
        horizon = self._select_horizon(ctx)

        if planner == PlannerType.BEHAVIOR_TREE:
            return self._behavior_tree_plan(goal, horizon, ctx)
        elif planner == PlannerType.HTN:
            return self._htn_plan(goal, horizon, ctx)
        elif planner == PlannerType.GOAP:
            return self._goap_plan(goal, horizon, ctx)
        elif planner == PlannerType.UTILITY_AI:
            return self._utility_plan(goal, horizon, ctx)
        elif planner == PlannerType.MCTS:
            return self._mcts_plan(goal, horizon, ctx)
        elif planner == PlannerType.CONSTRAINT_OPTIMIZATION:
            return self._constraint_plan(goal, horizon, ctx)
        elif planner == PlannerType.MODEL_PREDICTIVE_CONTROL:
            return self._mpc_plan(goal, horizon, ctx)
        elif planner == PlannerType.MULTI_AGENT_PLANNING:
            return self._multi_agent_plan(goal, horizon, ctx)
        elif planner == PlannerType.HIERARCHICAL:
            return self._hierarchical_plan(goal, horizon, ctx)
        else:
            return self._reactive_plan(goal, horizon, ctx)

    def _select_horizon(self, ctx: CycleContext) -> PlanningHorizon:
        """Select the planning horizon based on context."""
        time_horizon = ctx.context.time_horizon
        if time_horizon < 60:
            return PlanningHorizon.REACTIVE
        elif time_horizon < 3600:
            return PlanningHorizon.TACTICAL
        elif time_horizon < 86400:
            return PlanningHorizon.OPERATIONAL
        else:
            return PlanningHorizon.STRATEGIC

    def _behavior_tree_plan(self, goal: str, horizon: PlanningHorizon, ctx: CycleContext) -> Plan:
        """Generate a plan using behavior tree approach."""
        steps = [
            PlanStep(
                step_id="bt-1",
                action="evaluate_conditions",
                parameters={"goal": goal},
                preconditions=[],
                effects=["conditions_evaluated"],
                duration=1.0,
                horizon=horizon,
            ),
            PlanStep(
                step_id="bt-2",
                action="select_behavior",
                parameters={"goal": goal},
                preconditions=["conditions_evaluated"],
                effects=["behavior_selected"],
                duration=1.0,
                horizon=horizon,
            ),
            PlanStep(
                step_id="bt-3",
                action="execute_behavior",
                parameters={"goal": goal},
                preconditions=["behavior_selected"],
                effects=["behavior_executed"],
                duration=5.0,
                horizon=horizon,
            ),
        ]
        return Plan(
            goal=goal,
            steps=steps,
            planner_type=PlannerType.BEHAVIOR_TREE,
            confidence=0.7,
            expected_utility=0.6,
            horizon=horizon,
        )

    def _htn_plan(self, goal: str, horizon: PlanningHorizon, ctx: CycleContext) -> Plan:
        """Generate a plan using Hierarchical Task Network."""
        steps = [
            PlanStep(
                step_id="htn-1",
                action="decompose_task",
                parameters={"goal": goal},
                preconditions=[],
                effects=["task_decomposed"],
                duration=1.0,
                horizon=horizon,
            ),
            PlanStep(
                step_id="htn-2",
                action="execute_subtask_1",
                parameters={"goal": goal, "subtask": 1},
                preconditions=["task_decomposed"],
                effects=["subtask_1_complete"],
                duration=3.0,
                horizon=horizon,
            ),
            PlanStep(
                step_id="htn-3",
                action="execute_subtask_2",
                parameters={"goal": goal, "subtask": 2},
                preconditions=["subtask_1_complete"],
                effects=["subtask_2_complete"],
                duration=3.0,
                horizon=horizon,
            ),
            PlanStep(
                step_id="htn-4",
                action="compose_results",
                parameters={"goal": goal},
                preconditions=["subtask_2_complete"],
                effects=["goal_achieved"],
                duration=1.0,
                horizon=horizon,
            ),
        ]
        return Plan(
            goal=goal,
            steps=steps,
            planner_type=PlannerType.HTN,
            confidence=0.75,
            expected_utility=0.7,
            horizon=horizon,
        )

    def _goap_plan(self, goal: str, horizon: PlanningHorizon, ctx: CycleContext) -> Plan:
        """Generate a plan using Goal-Oriented Action Planning."""
        steps = [
            PlanStep(
                step_id="goap-1",
                action="assess_state",
                parameters={"goal": goal},
                preconditions=[],
                effects=["state_assessed"],
                duration=1.0,
                horizon=horizon,
            ),
            PlanStep(
                step_id="goap-2",
                action="select_action",
                parameters={"goal": goal},
                preconditions=["state_assessed"],
                effects=["action_selected"],
                duration=1.0,
                horizon=horizon,
            ),
            PlanStep(
                step_id="goap-3",
                action="execute_action",
                parameters={"goal": goal},
                preconditions=["action_selected"],
                effects=["action_executed"],
                duration=5.0,
                horizon=horizon,
            ),
            PlanStep(
                step_id="goap-4",
                action="verify_goal",
                parameters={"goal": goal},
                preconditions=["action_executed"],
                effects=["goal_verified"],
                duration=1.0,
                horizon=horizon,
            ),
        ]
        return Plan(
            goal=goal,
            steps=steps,
            planner_type=PlannerType.GOAP,
            confidence=0.8,
            expected_utility=0.75,
            horizon=horizon,
        )

    def _utility_plan(self, goal: str, horizon: PlanningHorizon, ctx: CycleContext) -> Plan:
        """Generate a plan using utility-based AI."""
        steps = [
            PlanStep(
                step_id="util-1",
                action="compute_utilities",
                parameters={"goal": goal},
                preconditions=[],
                effects=["utilities_computed"],
                duration=1.0,
                horizon=horizon,
            ),
            PlanStep(
                step_id="util-2",
                action="select_highest_utility",
                parameters={"goal": goal},
                preconditions=["utilities_computed"],
                effects=["action_selected"],
                duration=1.0,
                horizon=horizon,
            ),
            PlanStep(
                step_id="util-3",
                action="execute_utility_action",
                parameters={"goal": goal},
                preconditions=["action_selected"],
                effects=["action_executed"],
                duration=5.0,
                horizon=horizon,
            ),
        ]
        return Plan(
            goal=goal,
            steps=steps,
            planner_type=PlannerType.UTILITY_AI,
            confidence=0.7,
            expected_utility=0.8,
            horizon=horizon,
        )

    def _mcts_plan(self, goal: str, horizon: PlanningHorizon, ctx: CycleContext) -> Plan:
        """Generate a plan using Monte Carlo Tree Search."""
        steps = [
            PlanStep(
                step_id="mcts-1",
                action="simulate_rollouts",
                parameters={"goal": goal, "num_simulations": 100},
                preconditions=[],
                effects=["rollouts_complete"],
                duration=2.0,
                horizon=horizon,
            ),
            PlanStep(
                step_id="mcts-2",
                action="select_best_branch",
                parameters={"goal": goal},
                preconditions=["rollouts_complete"],
                effects=["branch_selected"],
                duration=1.0,
                horizon=horizon,
            ),
            PlanStep(
                step_id="mcts-3",
                action="execute_best_branch",
                parameters={"goal": goal},
                preconditions=["branch_selected"],
                effects=["branch_executed"],
                duration=5.0,
                horizon=horizon,
            ),
        ]
        return Plan(
            goal=goal,
            steps=steps,
            planner_type=PlannerType.MCTS,
            confidence=0.6,
            expected_utility=0.7,
            horizon=horizon,
        )

    def _constraint_plan(self, goal: str, horizon: PlanningHorizon, ctx: CycleContext) -> Plan:
        """Generate a plan using constraint optimization."""
        constraints = ctx.context.constraints
        steps = [
            PlanStep(
                step_id="const-1",
                action="formulate_constraints",
                parameters={"goal": goal, "constraints": constraints},
                preconditions=[],
                effects=["constraints_formulated"],
                duration=1.0,
                horizon=horizon,
            ),
            PlanStep(
                step_id="const-2",
                action="optimize_solution",
                parameters={"goal": goal},
                preconditions=["constraints_formulated"],
                effects=["solution_optimized"],
                duration=2.0,
                horizon=horizon,
            ),
            PlanStep(
                step_id="const-3",
                action="execute_optimized_solution",
                parameters={"goal": goal},
                preconditions=["solution_optimized"],
                effects=["solution_executed"],
                duration=5.0,
                horizon=horizon,
            ),
        ]
        return Plan(
            goal=goal,
            steps=steps,
            planner_type=PlannerType.CONSTRAINT_OPTIMIZATION,
            confidence=0.75,
            expected_utility=0.7,
            horizon=horizon,
        )

    def _mpc_plan(self, goal: str, horizon: PlanningHorizon, ctx: CycleContext) -> Plan:
        """Generate a plan using Model Predictive Control."""
        steps = [
            PlanStep(
                step_id="mpc-1",
                action="predict_trajectory",
                parameters={"goal": goal, "horizon": horizon.value},
                preconditions=[],
                effects=["trajectory_predicted"],
                duration=1.0,
                horizon=horizon,
            ),
            PlanStep(
                step_id="mpc-2",
                action="optimize_control",
                parameters={"goal": goal},
                preconditions=["trajectory_predicted"],
                effects=["control_optimized"],
                duration=1.0,
                horizon=horizon,
            ),
            PlanStep(
                step_id="mpc-3",
                action="apply_control",
                parameters={"goal": goal},
                preconditions=["control_optimized"],
                effects=["control_applied"],
                duration=5.0,
                horizon=horizon,
            ),
        ]
        return Plan(
            goal=goal,
            steps=steps,
            planner_type=PlannerType.MODEL_PREDICTIVE_CONTROL,
            confidence=0.7,
            expected_utility=0.75,
            horizon=horizon,
        )

    def _multi_agent_plan(self, goal: str, horizon: PlanningHorizon, ctx: CycleContext) -> Plan:
        """Generate a plan using multi-agent planning."""
        steps = [
            PlanStep(
                step_id="ma-1",
                action="allocate_tasks",
                parameters={"goal": goal, "agents": 3},
                preconditions=[],
                effects=["tasks_allocated"],
                duration=1.0,
                horizon=horizon,
            ),
            PlanStep(
                step_id="ma-2",
                action="coordinate_agents",
                parameters={"goal": goal},
                preconditions=["tasks_allocated"],
                effects=["agents_coordinated"],
                duration=2.0,
                horizon=horizon,
            ),
            PlanStep(
                step_id="ma-3",
                action="execute_agent_tasks",
                parameters={"goal": goal},
                preconditions=["agents_coordinated"],
                effects=["tasks_executed"],
                duration=5.0,
                horizon=horizon,
            ),
        ]
        return Plan(
            goal=goal,
            steps=steps,
            planner_type=PlannerType.MULTI_AGENT_PLANNING,
            confidence=0.7,
            expected_utility=0.8,
            horizon=horizon,
        )

    def _hierarchical_plan(self, goal: str, horizon: PlanningHorizon, ctx: CycleContext) -> Plan:
        """Generate a plan using hierarchical planning."""
        steps = [
            PlanStep(
                step_id="hier-1",
                action="strategic_planning",
                parameters={"goal": goal, "level": "strategic"},
                preconditions=[],
                effects=["strategic_plan"],
                duration=2.0,
                horizon=PlanningHorizon.STRATEGIC,
            ),
            PlanStep(
                step_id="hier-2",
                action="operational_planning",
                parameters={"goal": goal, "level": "operational"},
                preconditions=["strategic_plan"],
                effects=["operational_plan"],
                duration=2.0,
                horizon=PlanningHorizon.OPERATIONAL,
            ),
            PlanStep(
                step_id="hier-3",
                action="tactical_planning",
                parameters={"goal": goal, "level": "tactical"},
                preconditions=["operational_plan"],
                effects=["tactical_plan"],
                duration=2.0,
                horizon=PlanningHorizon.TACTICAL,
            ),
            PlanStep(
                step_id="hier-4",
                action="execute_tactical_plan",
                parameters={"goal": goal},
                preconditions=["tactical_plan"],
                effects=["plan_executed"],
                duration=5.0,
                horizon=horizon,
            ),
        ]
        return Plan(
            goal=goal,
            steps=steps,
            planner_type=PlannerType.HIERARCHICAL,
            confidence=0.8,
            expected_utility=0.8,
            horizon=horizon,
        )

    def _reactive_plan(self, goal: str, horizon: PlanningHorizon, ctx: CycleContext) -> Plan:
        """Generate a reactive plan."""
        steps = [
            PlanStep(
                step_id="react-1",
                action="react_to_stimulus",
                parameters={"goal": goal},
                preconditions=[],
                effects=["reaction_executed"],
                duration=1.0,
                horizon=PlanningHorizon.REACTIVE,
            ),
        ]
        return Plan(
            goal=goal,
            steps=steps,
            planner_type=PlannerType.REACTIVE,
            confidence=0.6,
            expected_utility=0.5,
            horizon=PlanningHorizon.REACTIVE,
        )

    def _generate_alternatives(self, planner: PlannerType, ctx: CycleContext) -> List[Plan]:
        """Generate alternative plans."""
        alternatives = []
        goal = ctx.context.goals[0] if ctx.context.goals else "achieve_objective"
        horizon = self._select_horizon(ctx)

        # Generate alternatives using different planners
        alt_planners = [
            PlannerType.GOAP,
            PlannerType.UTILITY_AI,
            PlannerType.HTN,
        ]
        for alt_planner in alt_planners:
            if alt_planner != planner and len(alternatives) < self.config.max_alternatives:
                alt = self._generate_plan(alt_planner, ctx)
                alternatives.append(alt)

        return alternatives

    def _derive_actions(self, plan: Plan, ctx: CycleContext) -> List[Action]:
        """Derive executable actions from the plan."""
        actions = []
        for step in plan.steps:
            action = Action(
                name=step.action,
                parameters=step.parameters,
                priority=1.0 / max(1, len(plan.steps)),
                confidence=step.confidence,
                urgency=0.5,
                horizon=step.horizon,
                expected_utility=plan.expected_utility / max(1, len(plan.steps)),
                risk=step.risk,
                source="planning_layer",
            )
            actions.append(action)
        return actions

    def _track_planner_performance(self, planner: PlannerType, confidence: float) -> None:
        """Track the performance of each planner."""
        if planner not in self._planner_performance:
            self._planner_performance[planner] = []
        self._planner_performance[planner].append(confidence)
        if len(self._planner_performance[planner]) > 100:
            self._planner_performance[planner] = self._planner_performance[planner][-100:]

    def get_plan_history(self) -> List[Plan]:
        """Return the history of plans."""
        return self._plan_history

    def get_planner_performance(self) -> Dict[str, float]:
        """Return the average performance of each planner."""
        return {
            planner.value: (
                sum(confidences) / len(confidences)
                if confidences else 0.0
            )
            for planner, confidences in self._planner_performance.items()
        }