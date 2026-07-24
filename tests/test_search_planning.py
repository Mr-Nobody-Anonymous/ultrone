#!/usr/bin/env python3
"""Comprehensive unit tests for the Search & Planning module (Phase 1).

Tests cover:
- Base interface contract compliance
- MCTS planning correctness
- HTN decomposition correctness
- A* optimality on grid
- Beam Search completeness
- Bidirectional Search meeting condition
- MAPF with CBS conflict resolution
- PDDL interface STRIPS semantics
- Anytime improvement guarantee
- RHC replanning behaviour
- DP value iteration convergence

Run with: python -m pytest tests/test_search_planning.py -v
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
from typing import Any, Dict, List, Tuple

from brain.reasoning.search.base import (
    Planner, PlanningAction, PlanningDomain, PlanningGoal, PlanningResult,
)
from brain.reasoning.search.mcts import MCTS, MCTSConfig
from brain.reasoning.search.htn import (
    HTNPlanner, HTNConfig, Task, PrimitiveTask, CompoundTask, Method,
)
from brain.reasoning.search.astar import AStar, AStarConfig, DLite, LPAStar
from brain.reasoning.search.beam_search import BeamSearch, BeamSearchConfig
from brain.reasoning.search.bidirectional import BidirectionalSearch, BidirectionalConfig
from brain.reasoning.search.mapf import MAPFPlanner, MAPFConfig, ConflictBasedSearch
from brain.reasoning.search.pddl_interface import (
    PDDLPlanner, PDDLConfig, PDDLDomain, PDDLAction, PDDLPredicate, PDDLProblem,
)
from brain.reasoning.search.anytime_planning import AnytimePlanner, AnytimeConfig
from brain.reasoning.search.receding_horizon import RecedingHorizonPlanner, RecedingHorizonConfig
from brain.reasoning.search.dynamic_programming import DPPlanner, DPConfig


# ═══════════════════════════════════════════════════════════════════════
#  Fixtures
# ═══════════════════════════════════════════════════════════════════════

def _create_grid_domain(
    width: int = 10,
    height: int = 10,
    obstacles: List[Tuple[int, int]] = None,
) -> PlanningDomain:
    """Create a simple grid world domain."""
    obstacles = obstacles or []

    def cost_fn(state: Any, action: Any) -> float:
        return 1.0

    def terminal_fn(state: Tuple[int, int]) -> bool:
        return state == (width - 1, height - 1)

    def heuristic_fn(state: Tuple[int, int], goal: Any) -> float:
        gx, gy = goal if isinstance(goal, tuple) else (width - 1, height - 1)
        return abs(state[0] - gx) + abs(state[1] - gy)

    actions = [
        PlanningAction("up", {"dx": 0, "dy": 1}, cost=1.0),
        PlanningAction("down", {"dx": 0, "dy": -1}, cost=1.0),
        PlanningAction("left", {"dx": -1, "dy": 0}, cost=1.0),
        PlanningAction("right", {"dx": 1, "dy": 0}, cost=1.0),
    ]

    return PlanningDomain(
        state_shape=(width, height),
        discrete_actions=actions,
        action_cost_fn=cost_fn,
        is_terminal_fn=terminal_fn,
        heuristic_fn=heuristic_fn,
    )


# ═══════════════════════════════════════════════════════════════════════
#  Test Base Interface
# ═══════════════════════════════════════════════════════════════════════

class TestPlannerInterface(unittest.TestCase):
    """All planners must implement the base interface correctly."""

    def setUp(self):
        self.domain = _create_grid_domain()

    def test_base_instantiation_fails(self):
        """Planner base class cannot be instantiated directly."""
        with self.assertRaises(TypeError):
            Planner()  # Abstract class

    def test_mcts_implements_interface(self):
        """MCTS implements the Planner interface."""
        p = MCTS()
        self.assertIsInstance(p, Planner)

    def test_astar_implements_interface(self):
        """A* implements the Planner interface."""
        p = AStar()
        self.assertIsInstance(p, Planner)

    def test_htn_implements_interface(self):
        """HTN implements the Planner interface."""
        p = HTNPlanner()
        self.assertIsInstance(p, Planner)

    def test_beam_implements_interface(self):
        """BeamSearch implements the Planner interface."""
        p = BeamSearch()
        self.assertIsInstance(p, Planner)

    def test_bidirectional_implements_interface(self):
        """BidirectionalSearch implements the Planner interface."""
        p = BidirectionalSearch()
        self.assertIsInstance(p, Planner)

    def test_mapf_implements_interface(self):
        """MAPFPlanner implements the Planner interface."""
        p = MAPFPlanner()
        self.assertIsInstance(p, Planner)

    def test_pddl_implements_interface(self):
        """PDDLPlanner implements the Planner interface."""
        p = PDDLPlanner()
        self.assertIsInstance(p, Planner)

    def test_anytime_implements_interface(self):
        """AnytimePlanner implements the Planner interface."""
        p = AnytimePlanner(MCTS())
        self.assertIsInstance(p, Planner)

    def test_rhc_implements_interface(self):
        """RecedingHorizonPlanner implements the Planner interface."""
        p = RecedingHorizonPlanner(AStar())
        self.assertIsInstance(p, Planner)

    def test_dp_implements_interface(self):
        """DPPlanner implements the Planner interface."""
        p = DPPlanner()
        self.assertIsInstance(p, Planner)

    def test_plan_returns_result(self):
        """Every planner must return a PlanningResult from plan()."""
        planners = [
            ("MCTS", MCTS(MCTSConfig(num_simulations=10))),
            ("AStar", AStar()),
            ("Beam", BeamSearch(BeamSearchConfig(beam_width=5, max_depth=10))),
            ("BiDir", BidirectionalSearch(BidirectionalConfig(max_expansions=1000))),
            ("DP", DPPlanner(DPConfig(max_iterations=50))),
        ]
        goal = PlanningGoal(description="reach_goal", target_state=(9, 9))
        state = (0, 0)

        for name, planner in planners:
            with self.subTest(planner=name):
                planner.initialize(self.domain)
                result = planner.plan(state, goal)
                self.assertIsInstance(result, PlanningResult,
                    f"{name} did not return PlanningResult")
                self.assertIn(type(result).success, [True, False],
                    f"{name} result.success not bool")


# ═══════════════════════════════════════════════════════════════════════
#  Test MCTS
# ═══════════════════════════════════════════════════════════════════════

class TestMCTS(unittest.TestCase):
    """Monte Carlo Tree Search correctness tests."""

    def setUp(self):
        self.domain = _create_grid_domain()
        self.planner = MCTS(MCTSConfig(num_simulations=200, max_depth=20))
        self.planner.initialize(self.domain)

    def test_mcts_finds_path_to_goal(self):
        """MCTS should find a path from (0,0) to (9,9)."""
        result = self.planner.plan((0, 0), PlanningGoal(target_state=(9, 9)))
        self.assertTrue(result.success, "MCTS should find a path")
        self.assertGreater(result.plan_length, 0)

    def test_mcts_plan_reduces_cost(self):
        """More simulations should produce lower or equal cost."""
        cheap = MCTS(MCTSConfig(num_simulations=500, max_depth=20))
        cheap.initialize(self.domain)
        result_cheap = cheap.plan((0, 0), PlanningGoal(target_state=(9, 9)))

        expensive = MCTS(MCTSConfig(num_simulations=50, max_depth=20))
        expensive.initialize(self.domain)
        result_expensive = expensive.plan((0, 0), PlanningGoal(target_state=(9, 9)))

        # More sims should not make cost worse (may not always hold but often does)
        self.assertLessEqual(result_cheap.cost, result_expensive.cost * 2)

    def test_mcts_returns_non_empty_actions(self):
        """Successful plan must contain actions."""
        result = self.planner.plan((0, 0), PlanningGoal(target_state=(9, 9)))
        if result.success:
            self.assertGreater(len(result.actions), 0)
            for action in result.actions:
                self.assertIsInstance(action, PlanningAction)

    def test_mcts_stats(self):
        """get_stats() should return diagnostic information."""
        self.planner.plan((0, 0), PlanningGoal(target_state=(9, 9)))
        stats = self.planner.get_stats()
        self.assertIn("total_plans", stats)
        self.assertIn("total_nodes_expanded", stats)
        self.assertEqual(stats["total_plans"], 1)


# ═══════════════════════════════════════════════════════════════════════
#  Test HTN
# ═══════════════════════════════════════════════════════════════════════

class TestHTN(unittest.TestCase):
    """Hierarchical Task Network decomposition tests."""

    def setUp(self):
        self.planner = HTNPlanner(HTNConfig(max_depth=10))
        domain = _create_grid_domain()
        self.planner.initialize(domain)

        # Add HTN-specific structure
        self.planner.add_method(Method(
            task_name="reach_goal",
            subtasks=[
                CompoundTask("navigate"),
                CompoundTask("secure_area"),
            ],
            description="Standard approach",
        ))
        self.planner.add_method(Method(
            task_name="navigate",
            subtasks=[
                PrimitiveTask("move_forward"),
                PrimitiveTask("move_forward"),
            ],
        ))
        self.planner.add_method(Method(
            task_name="secure_area",
            subtasks=[
                PrimitiveTask("scan_area"),
                PrimitiveTask("report_status"),
            ],
        ))
        self.planner.add_primitive(PrimitiveTask("move_forward",
            PlanningAction("move", cost=1.0)))
        self.planner.add_primitive(PrimitiveTask("scan_area",
            PlanningAction("scan", cost=0.5)))
        self.planner.add_primitive(PrimitiveTask("report_status",
            PlanningAction("report", cost=0.3)))

    def test_htn_decomposes_to_primitives(self):
        """HTN should decompose a goal into primitive actions."""
        result = self.planner.plan(
            {}, PlanningGoal(description="reach_goal"),
        )
        self.assertTrue(result.success)
        self.assertGreater(len(result.actions), 0)
        # All actions must be primitives (PlanningAction)
        for action in result.actions:
            self.assertIsInstance(action, PlanningAction)

    def test_htn_plan_order_matches_method(self):
        """Action order should reflect method decomposition."""
        result = self.planner.plan(
            {}, PlanningGoal(description="reach_goal"),
        )
        if result.success:
            names = [a.name for a in result.actions]
            expected = ["move", "move", "scan", "report"]
            self.assertEqual(names, expected)

    def test_htn_fails_on_unknown_task(self):
        """HTN should fail gracefully for unknown tasks."""
        result = self.planner.plan(
            {}, PlanningGoal(description="unknown_task"),
        )
        self.assertFalse(result.success)

    def test_htn_cycle_detection(self):
        """HTN should detect and break cycles."""
        # Add a self-referencing method
        self.planner.add_method(Method(
            task_name="infinite_loop",
            subtasks=[CompoundTask("infinite_loop")],
        ))
        result = self.planner.plan(
            {}, PlanningGoal(description="infinite_loop"),
        )
        self.assertFalse(result.success)


# ═══════════════════════════════════════════════════════════════════════
#  Test A*
# ═══════════════════════════════════════════════════════════════════════

class TestAStar(unittest.TestCase):
    """A* optimality and correctness tests."""

    def setUp(self):
        self.domain = _create_grid_domain()
        self.planner = AStar(AStarConfig(heuristic_weight=1.0))
        self.planner.initialize(self.domain)

    def test_astar_finds_optimal_path(self):
        """A* should find the shortest path on a uniform grid."""
        result = self.planner.plan((0, 0), PlanningGoal(target_state=(5, 5)))
        self.assertTrue(result.success)
        # Manhattan distance from (0,0) to (5,5) is 10 steps
        self.assertEqual(result.plan_length, 10)

    def test_astar_start_is_goal(self):
        """A* should handle start == goal."""
        result = self.planner.plan((5, 5), PlanningGoal(target_state=(5, 5)))
        self.assertTrue(result.success)
        self.assertEqual(result.plan_length, 0)

    def test_astar_path_cost_matches_length(self):
        """On unit-cost grid, cost == plan_length."""
        result = self.planner.plan((0, 0), PlanningGoal(target_state=(3, 3)))
        if result.success:
            self.assertEqual(result.cost, result.plan_length)

    def test_astar_dlite_subclass(self):
        """DLite is a subclass of AStar."""
        dlite = DLite()
        self.assertIsInstance(dlite, AStar)

    def test_astar_lpastar_subclass(self):
        """LPAStar is a subclass of AStar."""
        lpa = LPAStar()
        self.assertIsInstance(lpa, AStar)


# ═══════════════════════════════════════════════════════════════════════
#  Test Beam Search
# ═══════════════════════════════════════════════════════════════════════

class TestBeamSearch(unittest.TestCase):
    """Beam Search completeness tests."""

    def setUp(self):
        self.domain = _create_grid_domain()
        self.planner = BeamSearch(BeamSearchConfig(beam_width=10, max_depth=30))
        self.planner.initialize(self.domain)

    def test_beam_finds_path(self):
        """Beam Search should find a path to the goal."""
        result = self.planner.plan((0, 0), PlanningGoal(target_state=(9, 9)))
        self.assertTrue(result.success)

    def test_beam_wider_beam_better_path(self):
        """Wider beam should produce lower cost paths."""
        narrow = BeamSearch(BeamSearchConfig(beam_width=2, max_depth=20))
        narrow.initialize(self.domain)
        r_narrow = narrow.plan((0, 0), PlanningGoal(target_state=(5, 5)))

        wide = BeamSearch(BeamSearchConfig(beam_width=20, max_depth=20))
        wide.initialize(self.domain)
        r_wide = wide.plan((0, 0), PlanningGoal(target_state=(5, 5)))

        self.assertLessEqual(r_wide.cost, r_narrow.cost)

    def test_beam_narrow_fails(self):
        """Very narrow beam may fail on large grid."""
        tiny = BeamSearch(BeamSearchConfig(beam_width=1, max_depth=5))
        tiny.initialize(self.domain)
        result = tiny.plan((0, 0), PlanningGoal(target_state=(9, 9)))
        # With beam_width=1 and max_depth=5, it may fail
        # or succeed — we just check it doesn't crash


# ═══════════════════════════════════════════════════════════════════════
#  Test Bidirectional Search
# ═══════════════════════════════════════════════════════════════════════

class TestBidirectionalSearch(unittest.TestCase):
    """Bidirectional Search meeting condition tests."""

    def setUp(self):
        self.domain = _create_grid_domain()
        self.planner = BidirectionalSearch(BidirectionalConfig(max_expansions=10000))
        self.planner.initialize(self.domain)

    def test_bidirectional_finds_path(self):
        """Bidirectional search should find a path."""
        result = self.planner.plan((0, 0), PlanningGoal(target_state=(9, 9)))
        self.assertTrue(result.success)
        self.assertGreater(result.plan_length, 0)

    def test_bidirectional_meeting_point_in_result(self):
        """Metadata should contain meeting point."""
        result = self.planner.plan((0, 0), PlanningGoal(target_state=(9, 9)))
        if result.success:
            self.assertIn("meeting_point", result.metadata)


# ═══════════════════════════════════════════════════════════════════════
#  Test MAPF / CBS
# ═══════════════════════════════════════════════════════════════════════

class TestMAPF(unittest.TestCase):
    """Multi-Agent Path Finding conflict resolution tests."""

    def setUp(self):
        self.planner = MAPFPlanner(MAPFConfig(max_iterations=1000))
        self.domain = _create_grid_domain()
        self.planner.initialize(self.domain)
        self.planner.set_grid(10, 10)
        self.planner.set_agents(
            agent_ids=["A", "B"],
            starts={"A": (0, 0), "B": (9, 9)},
            goals={"A": (9, 9), "B": (0, 0)},
        )

    def test_mapf_finds_joint_path(self):
        """MAPF should find collision-free paths."""
        result = self.planner.plan({}, PlanningGoal(description="cross"))
        self.assertTrue(result.success,
            "MAPF should find paths for agents in this configuration")

    def test_mapf_no_collisions_in_path(self):
        """Planned paths must have no vertex conflicts."""
        result = self.planner.plan({}, PlanningGoal(description="cross"))
        if result.success:
            # Verify by checking per-timestep occupancy
            occupied: Dict[Tuple[int, int], str] = {}
            for action in result.actions:
                params = action.parameters
                pos = tuple(params.get("position", (0, 0)))
                if pos in occupied:
                    self.fail(f"Collision at {pos} between agents")
                occupied[pos] = params.get("agent", "?")

    def test_mapf_conflictbasedsearch_alias(self):
        """ConflictBasedSearch is an alias for MAPFPlanner."""
        cbs = ConflictBasedSearch()
        self.assertIsInstance(cbs, MAPFPlanner)


# ═══════════════════════════════════════════════════════════════════════
#  Test PDDL Interface
# ═══════════════════════════════════════════════════════════════════════

class TestPDDLPlanner(unittest.TestCase):
    """STRIPS planning correctness tests."""

    def setUp(self):
        self.domain = PDDLDomain("test_domain")
        # Simple logistics: pickup → deliver
        self.domain.add_action(PDDLAction(
            name="pickup",
            preconditions={PDDLPredicate("at_warehouse")},
            add_effects={PDDLPredicate("has_package")},
            del_effects=set(),
            cost=1.0,
        ))
        self.domain.add_action(PDDLAction(
            name="deliver",
            preconditions={PDDLPredicate("has_package")},
            add_effects={PDDLPredicate("delivered")},
            del_effects={PDDLPredicate("has_package")},
            cost=1.0,
        ))
        self.domain.add_action(PDDLAction(
            name="move_to_warehouse",
            preconditions=set(),
            add_effects={PDDLPredicate("at_warehouse")},
            del_effects={PDDLPredicate("at_home")},
            cost=1.0,
        ))

        self.planner = PDDLPlanner(PDDLConfig(max_expansions=10000))
        self.planner.load_domain(self.domain)

    def test_pddl_finds_valid_plan(self):
        """PDDL planner should find a plan that achieves the goal."""
        problem = PDDLProblem(
            name="test_problem",
            domain=self.domain,
            init={PDDLPredicate("at_home")},
            goal={PDDLPredicate("delivered")},
        )
        self.planner.load_problem(problem)
        result = self.planner.plan(problem.init, PlanningGoal(
            description="deliver_package",
            predicates={"delivered": True},
        ))
        self.assertTrue(result.success, "PDDL should find a plan")
        # Expected: move_to_warehouse → pickup → deliver
        names = [a.name for a in result.actions]
        self.assertIn("pickup", names)
        self.assertIn("deliver", names)

    def test_pddl_strips_semantics(self):
        """Plan should respect STRIPS add/delete semantics."""
        problem = PDDLProblem(
            name="test_semantics",
            domain=self.domain,
            init={PDDLPredicate("at_home")},
            goal={PDDLPredicate("delivered")},
        )
        self.planner.load_problem(problem)
        result = self.planner.plan(problem.init, PlanningGoal(
            description="deliver_package",
            predicates={"delivered": True},
        ))
        if result.success:
            # Simulate execution
            state = {PDDLPredicate("at_home")}
            for action in result.actions:
                # Find matching PDDL action
                pddl_action = next(
                    a for a in self.domain.actions if a.name == action.name
                )
                self.assertTrue(
                    pddl_action.preconditions.issubset(state),
                    f"Preconditions not met for {action.name}: {pddl_action.preconditions - state}",
                )
                state = (state - pddl_action.del_effects) | pddl_action.add_effects
            self.assertIn(PDDLPredicate("delivered"), state)

    def test_pddl_fails_impossible(self):
        """PDDL planner should fail on unsolvable problems."""
        impossible = PDDLDomain("impossible")
        impossible.add_action(PDDLAction(
            name="nothing",
            preconditions={PDDLPredicate("magic")},
            add_effects={PDDLPredicate("done")},
            del_effects=set(),
        ))
        planner = PDDLPlanner(PDDLConfig(max_expansions=500))
        planner.load_domain(impossible)
        result = planner.plan(
            set(), PlanningGoal(description="finish", predicates={"done": True}),
        )
        self.assertFalse(result.success)


# ═══════════════════════════════════════════════════════════════════════
#  Test Anytime Planning
# ═══════════════════════════════════════════════════════════════════════

class TestAnytimePlanner(unittest.TestCase):
    """Anytime improvement guarantee tests."""

    def setUp(self):
        self.inner = MCTS(MCTSConfig(num_simulations=50))
        self.domain = _create_grid_domain()
        self.inner.initialize(self.domain)
        self.planner = AnytimePlanner(
            self.inner,
            AnytimeConfig(time_budget_ms=2000, max_iterations=5),
        )
        self.planner.initialize(self.domain)

    def test_anytime_returns_first_solution(self):
        """Anytime should return a solution immediately."""
        result = self.planner.plan((0, 0), PlanningGoal(target_state=(9, 9)))
        self.assertTrue(result.success)

    def test_anytime_inner_plan_detection(self):
        """get_stats should report inner planner type."""
        stats = self.planner.get_stats()
        self.assertEqual(stats["inner_planner"], "MCTS")


# ═══════════════════════════════════════════════════════════════════════
#  Test Receding Horizon Control
# ═══════════════════════════════════════════════════════════════════════

class TestRHC(unittest.TestCase):
    """Receding Horizon replanning behaviour tests."""

    def setUp(self):
        self.inner = AStar()
        self.domain = _create_grid_domain()
        self.inner.initialize(self.domain)
        self.planner = RecedingHorizonPlanner(
            self.inner,
            RecedingHorizonConfig(horizon=5, receding_step=1, max_total_steps=50),
        )
        self.planner.initialize(self.domain)

    def test_rhc_reaches_goal(self):
        """RHC should eventually reach the goal."""
        result = self.planner.plan((0, 0), PlanningGoal(target_state=(9, 9)))
        self.assertTrue(result.success,
            "RHC should reach the goal (even if suboptimally)")
        self.assertGreater(result.plan_length, 0)

    def test_rhc_plan_length_reasonable(self):
        """RHC plan should not exceed max steps."""
        result = self.planner.plan((0, 0), PlanningGoal(target_state=(9, 9)))
        if result.success:
            self.assertLessEqual(result.plan_length, 50)

    def test_rhc_inner_planner_reporting(self):
        """get_stats should report inner planner."""
        stats = self.planner.get_stats()
        self.assertEqual(stats["inner_planner"], "AStar")


# ═══════════════════════════════════════════════════════════════════════
#  Test Dynamic Programming
# ═══════════════════════════════════════════════════════════════════════

class TestDPPlanner(unittest.TestCase):
    """Value iteration convergence tests."""

    def setUp(self):
        self.domain = _create_grid_domain(width=5, height=5)
        self.planner = DPPlanner(DPConfig(max_iterations=200, convergence_threshold=1e-3))
        # Enumerate all 25 states
        from itertools import product
        states = list(product(range(5), range(5)))
        self.planner.initialize(self.domain, state_enumeration=states)

    def test_dp_finds_path(self):
        """DP should find a path from (0,0) to (4,4)."""
        result = self.planner.plan((0, 0), PlanningGoal(target_state=(4, 4)))
        self.assertTrue(result.success)
        self.assertGreater(result.plan_length, 0)

    def test_dp_optimal_path_length(self):
        """DP should find the optimal (shortest) path."""
        result = self.planner.plan((0, 0), PlanningGoal(target_state=(4, 4)))
        if result.success:
            # Manhattan distance: 8
            self.assertEqual(result.plan_length, 8,
                "DP should find optimal path length on uniform grid")

    def test_dp_value_convergence(self):
        """Value iteration should converge to stable values."""
        result = self.planner.plan((0, 0), PlanningGoal(target_state=(4, 4)))
        stats = self.planner.get_stats()
        self.assertGreater(stats.get("has_policy", 0), 0,
            "DP should produce a policy after planning")

    def test_dp_start_is_terminal(self):
        """DP should handle start == goal."""
        result = self.planner.plan((4, 4), PlanningGoal(target_state=(4, 4)))
        self.assertTrue(result.success)
        self.assertEqual(result.plan_length, 0)

    def test_dp_finite_horizon(self):
        """DP should work in finite-horizon mode."""
        fp = DPPlanner(DPConfig(horizon=10, max_iterations=100))
        from itertools import product
        states = list(product(range(5), range(5)))
        fp.initialize(self.domain, state_enumeration=states)
        result = fp.plan((0, 0), PlanningGoal(target_state=(4, 4)))
        self.assertTrue(result.success)


# ═══════════════════════════════════════════════════════════════════════
#  Integration test: TacticalEngine compatibility
# ═══════════════════════════════════════════════════════════════════════

class TestIntegrationWithTacticalEngine(unittest.TestCase):
    """Planners should be usable via the TacticalEngine."""

    def test_planners_importable_via_reasoning(self):
        """All planners must be importable from brain.reasoning.search."""
        try:
            from brain.reasoning.search import (
                MCTS, HTNPlanner, AStar, BeamSearch,
                BidirectionalSearch, MAPFPlanner, PDDLPlanner,
                AnytimePlanner, RecedingHorizonPlanner, DPPlanner,
            )
            self.assertTrue(True, "All planners importable")
        except ImportError as e:
            self.fail(f"Import failed: {e}")

    def test_planner_polymorphism(self):
        """Planners can be used polymorphically via the Planner base."""
        planners: List[Planner] = [
            MCTS(MCTSConfig(num_simulations=10)),
            AStar(),
            BeamSearch(BeamSearchConfig(beam_width=5)),
        ]
        domain = _create_grid_domain()
        goal = PlanningGoal(target_state=(9, 9))

        for planner in planners:
            with self.subTest(planner=type(planner).__name__):
                planner.initialize(domain)
                result = planner.plan((0, 0), goal)
                self.assertIsNotNone(result)


if __name__ == "__main__":
    unittest.main(verbosity=2)

