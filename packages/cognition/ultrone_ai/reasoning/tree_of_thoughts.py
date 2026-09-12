# Copyright (c) Ultrone Contributors. All rights reserved.
"""Tree of Thoughts (ToT) reasoning engine.

Implements the Tree of Thoughts framework from "Tree of Thoughts: Deliberate
Problem Solving with Large Language Models" (Yao et al., 2023).

ToT explores multiple reasoning paths by:
1. Decomposing the problem into intermediate "thought" steps
2. Generating multiple candidate thoughts at each step
3. Evaluating each thought's promise (state evaluation)
4. Using BFS/DFS search to explore the most promising paths
5. Selecting the best solution from explored paths

This is particularly effective for:
- Mathematical reasoning (GSM8K, MATH, AIME)
- Logical reasoning (MMLU, GPQA)
- Code generation (HumanEval, MBPP)
- Planning tasks (AgentBench, GAIA)
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("Ultrone.AI.Reasoning.ToT")


@dataclass
class ToTConfig:
    """Configuration for Tree of Thoughts reasoning.

    Parameters
    ----------
    max_depth : int
        Maximum depth of the thought tree.
    branching_factor : int
        Number of candidate thoughts to generate at each node.
    beam_width : int
        Number of top thoughts to keep at each level (for BFS).
    search_strategy : str
        Search strategy: "bfs" or "dfs".
    evaluation_method : str
        How to evaluate thoughts: "value" (score 0-1) or "vote" (pick best).
    max_iterations : int
        Maximum search iterations.
    pruning_threshold : float
        Minimum value score to keep a thought (0-1).
    enable_backtracking : bool
        Whether to allow backtracking in DFS.
    """
    max_depth: int = 5
    branching_factor: int = 3
    beam_width: int = 3
    search_strategy: str = "bfs"  # bfs or dfs
    evaluation_method: str = "value"  # value or vote
    max_iterations: int = 20
    pruning_threshold: float = 0.1
    enable_backtracking: bool = True


@dataclass
class ThoughtNode:
    """A node in the thought tree.

    Attributes
    ----------
    thought : str
        The reasoning step / thought content.
    depth : int
        Depth in the tree (0 = root).
    value : float
        Evaluated promise score (0-1).
    children : list of ThoughtNode
        Child thoughts.
    parent : optional ThoughtNode
        Parent thought.
    is_solution : bool
        Whether this node represents a complete solution.
    metadata : dict
        Additional metadata.
    """
    thought: str = ""
    depth: int = 0
    value: float = 0.0
    children: List["ThoughtNode"] = field(default_factory=list)
    parent: Optional["ThoughtNode"] = None
    is_solution: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def path(self) -> List[str]:
        """Return the path of thoughts from root to this node."""
        path = []
        node: Optional[ThoughtNode] = self
        while node is not None:
            path.append(node.thought)
            node = node.parent
        return list(reversed(path))

    @property
    def path_str(self) -> str:
        """Return the path as a joined string."""
        return " → ".join(self.path)

    def add_child(self, thought: str, value: float = 0.0) -> "ThoughtNode":
        """Add a child thought node."""
        child = ThoughtNode(
            thought=thought,
            depth=self.depth + 1,
            value=value,
            parent=self,
        )
        self.children.append(child)
        return child


class TreeOfThoughts:
    """Tree of Thoughts reasoning engine.

    Parameters
    ----------
    config : ToTConfig
        Configuration for the reasoning engine.
    thought_generator : callable, optional
        Function that generates candidate thoughts given a state.
        Signature: (state: str, n: int) -> List[str]
    state_evaluator : callable, optional
        Function that evaluates the promise of a state.
        Signature: (state: str) -> float  (0-1)
    solution_checker : callable, optional
        Function that checks if a state is a solution.
        Signature: (state: str) -> bool
    """

    def __init__(
        self,
        config: Optional[ToTConfig] = None,
        thought_generator: Optional[Callable[[str, int], List[str]]] = None,
        state_evaluator: Optional[Callable[[str], float]] = None,
        solution_checker: Optional[Callable[[str], bool]] = None,
    ):
        self.config = config or ToTConfig()
        self._thought_generator = thought_generator or self._default_thought_generator
        self._state_evaluator = state_evaluator or self._default_state_evaluator
        self._solution_checker = solution_checker or self._default_solution_checker
        self._root: Optional[ThoughtNode] = None
        self._all_nodes: List[ThoughtNode] = []
        self._best_solution: Optional[ThoughtNode] = None
        self._iterations: int = 0

    def solve(self, problem: str) -> Dict[str, Any]:
        """Solve a problem using Tree of Thoughts.

        Parameters
        ----------
        problem : str
            The problem to solve.

        Returns
        -------
        dict
            Solution with the reasoning path, confidence, and metadata.
        """
        self._iterations = 0
        self._all_nodes = []
        self._best_solution = None

        # Create root node
        self._root = ThoughtNode(thought=problem, depth=0, value=1.0)
        self._all_nodes.append(self._root)

        # Check if root is already a solution
        if self._solution_checker(problem):
            self._root.is_solution = True
            self._best_solution = self._root
            return self._format_result()

        # Run search
        if self.config.search_strategy == "bfs":
            self._bfs_search()
        else:
            self._dfs_search(self._root)

        return self._format_result()

    def _bfs_search(self) -> None:
        """Breadth-first search through the thought tree."""
        current_level: List[ThoughtNode] = [self._root]

        for depth in range(self.config.max_depth):
            if self._iterations >= self.config.max_iterations:
                logger.debug("ToT BFS reached max iterations")
                break

            next_level: List[ThoughtNode] = []

            for node in current_level:
                if self._iterations >= self.config.max_iterations:
                    break

                # Generate child thoughts
                thoughts = self._generate_thoughts(node)
                for thought, value in thoughts:
                    child = node.add_child(thought, value)
                    self._all_nodes.append(child)
                    self._iterations += 1

                    # Check if solution
                    if self._solution_checker(thought):
                        child.is_solution = True
                        if self._best_solution is None or value > self._best_solution.value:
                            self._best_solution = child
                        continue

                    # Add to next level if promising
                    if value >= self.config.pruning_threshold:
                        next_level.append(child)

            # Keep only top beam_width nodes
            next_level.sort(key=lambda n: n.value, reverse=True)
            current_level = next_level[: self.config.beam_width]

            if not current_level:
                break

    def _dfs_search(self, node: ThoughtNode, visited: Optional[set] = None) -> None:
        """Depth-first search through the thought tree."""
        if visited is None:
            visited = set()

        if self._iterations >= self.config.max_iterations:
            return

        if node.depth >= self.config.max_depth:
            return

        node_id = id(node)
        if node_id in visited:
            return
        visited.add(node_id)

        # Generate child thoughts
        thoughts = self._generate_thoughts(node)
        thoughts.sort(key=lambda x: x[1], reverse=True)

        for thought, value in thoughts:
            if self._iterations >= self.config.max_iterations:
                break

            child = node.add_child(thought, value)
            self._all_nodes.append(child)
            self._iterations += 1

            # Check if solution
            if self._solution_checker(thought):
                child.is_solution = True
                if self._best_solution is None or value > self._best_solution.value:
                    self._best_solution = child
                continue

            # Recurse if promising
            if value >= self.config.pruning_threshold:
                self._dfs_search(child, visited)

        # Backtrack: check if we found a better solution among children
        if self.config.enable_backtracking and node.children:
            best_child = max(node.children, key=lambda c: c.value)
            if best_child.is_solution:
                if self._best_solution is None or best_child.value > self._best_solution.value:
                    self._best_solution = best_child

    def _generate_thoughts(self, node: ThoughtNode) -> List[Tuple[str, float]]:
        """Generate and evaluate candidate thoughts for a node."""
        # Build the current state from the path
        state = node.path_str

        # Generate candidate thoughts
        thoughts = self._thought_generator(state, self.config.branching_factor)

        # Evaluate each thought
        evaluated = []
        for thought in thoughts:
            if self.config.evaluation_method == "value":
                value = self._state_evaluator(thought)
            else:  # vote
                value = self._vote_evaluate(thought)

            evaluated.append((thought, value))

        return evaluated

    def _vote_evaluate(self, thought: str) -> float:
        """Evaluate a thought using voting (simplified)."""
        # In a real implementation, this would use multiple evaluators
        # and take a majority vote. Here we use the state evaluator.
        return self._state_evaluator(thought)

    def _default_thought_generator(self, state: str, n: int) -> List[str]:
        """Default thought generator (placeholder)."""
        # In a real implementation, this would use an LLM to generate
        # diverse candidate next steps. Here we generate simple variations.
        thoughts = []
        for i in range(n):
            thoughts.append(f"Step {i+1}: Analyze the problem from angle {i+1}")
        return thoughts

    def _default_state_evaluator(self, state: str) -> float:
        """Default state evaluator (placeholder)."""
        # In a real implementation, this would use an LLM to evaluate
        # the promise of the current state. Here we use a simple heuristic.
        if not state:
            return 0.0
        # Longer reasoning paths tend to be more developed
        length_score = min(1.0, len(state) / 500)
        # Check for solution-like patterns
        solution_patterns = ["therefore", "thus", "so the answer", "the answer is", "result is"]
        pattern_score = 0.0
        for pattern in solution_patterns:
            if pattern in state.lower():
                pattern_score = 0.3
                break
        return min(1.0, length_score * 0.5 + pattern_score + 0.2)

    def _default_solution_checker(self, state: str) -> bool:
        """Default solution checker (placeholder)."""
        # Check for common solution patterns
        solution_patterns = [
            "the answer is",
            "therefore, the answer",
            "so the answer is",
            "final answer:",
            "result:",
            "answer =",
        ]
        state_lower = state.lower()
        return any(pattern in state_lower for pattern in solution_patterns)

    def _format_result(self) -> Dict[str, Any]:
        """Format the result."""
        if self._best_solution:
            return {
                "solved": True,
                "solution": self._best_solution.thought,
                "reasoning_path": self._best_solution.path,
                "confidence": self._best_solution.value,
                "depth": self._best_solution.depth,
                "nodes_explored": len(self._all_nodes),
                "iterations": self._iterations,
            }
        else:
            # Return the best non-solution node
            best = max(self._all_nodes, key=lambda n: n.value) if self._all_nodes else None
            return {
                "solved": False,
                "solution": best.thought if best else "",
                "reasoning_path": best.path if best else [],
                "confidence": best.value if best else 0.0,
                "depth": best.depth if best else 0,
                "nodes_explored": len(self._all_nodes),
                "iterations": self._iterations,
            }

    def get_tree(self) -> Optional[ThoughtNode]:
        """Return the root of the thought tree."""
        return self._root

    def get_all_nodes(self) -> List[ThoughtNode]:
        """Return all nodes in the tree."""
        return self._all_nodes

    def get_stats(self) -> Dict[str, Any]:
        """Return statistics about the search."""
        return {
            "strategy": self.config.search_strategy,
            "nodes_explored": len(self._all_nodes),
            "iterations": self._iterations,
            "max_depth_reached": max((n.depth for n in self._all_nodes), default=0),
            "solutions_found": sum(1 for n in self._all_nodes if n.is_solution),
        }