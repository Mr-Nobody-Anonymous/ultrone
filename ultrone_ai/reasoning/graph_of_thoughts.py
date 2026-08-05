# Copyright (c) Ultrone Contributors. All rights reserved.
"""Graph of Thoughts (GoT) reasoning engine.

Implements the Graph of Thoughts framework from "Graph of Thoughts: Solving
Elaborate Problems with Large Language Models" (Besta et al., 2023).

GoT extends ToT by allowing arbitrary graph structures, enabling:
- Thought merging (combining multiple thoughts)
- Thought refinement (iterative improvement)
- Thought backtracking (revisiting and improving)
- Arbitrary DAG structures for complex reasoning
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("Ultrone.AI.Reasoning.GoT")


@dataclass
class GoTConfig:
    """Configuration for Graph of Thoughts reasoning."""
    max_iterations: int = 30
    max_thoughts: int = 50
    branching_factor: int = 3
    merge_threshold: float = 0.7  # Similarity threshold for merging
    refinement_rounds: int = 2
    pruning_threshold: float = 0.1
    enable_merging: bool = True
    enable_refinement: bool = True


@dataclass
class ThoughtVertex:
    """A vertex in the thought graph."""
    vertex_id: str
    thought: str = ""
    score: float = 0.0
    generation: int = 0
    is_solution: bool = False
    merged_from: List[str] = field(default_factory=list)
    refined_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ThoughtEdge:
    """An edge in the thought graph."""
    source_id: str
    target_id: str
    edge_type: str = "derives"  # derives, merges, refines
    weight: float = 1.0


class ThoughtGraph:
    """A graph structure for thoughts."""

    def __init__(self) -> None:
        self._vertices: Dict[str, ThoughtVertex] = {}
        self._edges: List[ThoughtEdge] = []
        self._adjacency: Dict[str, List[str]] = {}

    def add_vertex(self, vertex: ThoughtVertex) -> None:
        self._vertices[vertex.vertex_id] = vertex
        if vertex.vertex_id not in self._adjacency:
            self._adjacency[vertex.vertex_id] = []

    def add_edge(self, edge: ThoughtEdge) -> None:
        self._edges.append(edge)
        if edge.source_id not in self._adjacency:
            self._adjacency[edge.source_id] = []
        self._adjacency[edge.source_id].append(edge.target_id)

    def get_vertex(self, vertex_id: str) -> Optional[ThoughtVertex]:
        return self._vertices.get(vertex_id)

    def get_children(self, vertex_id: str) -> List[ThoughtVertex]:
        child_ids = self._adjacency.get(vertex_id, [])
        return [self._vertices[cid] for cid in child_ids if cid in self._vertices]

    def get_all_vertices(self) -> List[ThoughtVertex]:
        return list(self._vertices.values())

    def get_all_edges(self) -> List[ThoughtEdge]:
        return list(self._edges)

    def get_best_vertices(self, n: int = 5) -> List[ThoughtVertex]:
        return sorted(self._vertices.values(), key=lambda v: v.score, reverse=True)[:n]

    def get_solutions(self) -> List[ThoughtVertex]:
        return [v for v in self._vertices.values() if v.is_solution]

    @property
    def num_vertices(self) -> int:
        return len(self._vertices)

    @property
    def num_edges(self) -> int:
        return len(self._edges)


class GraphOfThoughts:
    """Graph of Thoughts reasoning engine.

    Parameters
    ----------
    config : GoTConfig
        Configuration for the reasoning engine.
    thought_generator : callable, optional
        Function that generates candidate thoughts.
    thought_evaluator : callable, optional
        Function that evaluates thought quality.
    thought_merger : callable, optional
        Function that merges two thoughts.
    thought_refiner : callable, optional
        Function that refines a thought.
    solution_checker : callable, optional
        Function that checks if a thought is a solution.
    """

    def __init__(
        self,
        config: Optional[GoTConfig] = None,
        thought_generator: Optional[Callable[[str, int], List[str]]] = None,
        thought_evaluator: Optional[Callable[[str], float]] = None,
        thought_merger: Optional[Callable[[str, str], str]] = None,
        thought_refiner: Optional[Callable[[str], str]] = None,
        solution_checker: Optional[Callable[[str], bool]] = None,
    ):
        self.config = config or GoTConfig()
        self._thought_generator = thought_generator or self._default_generator
        self._thought_evaluator = thought_evaluator or self._default_evaluator
        self._thought_merger = thought_merger or self._default_merger
        self._thought_refiner = thought_refiner or self._default_refiner
        self._solution_checker = solution_checker or self._default_solution_checker
        self._graph = ThoughtGraph()
        self._vertex_counter = 0
        self._iteration = 0

    def solve(self, problem: str) -> Dict[str, Any]:
        """Solve a problem using Graph of Thoughts."""
        self._graph = ThoughtGraph()
        self._vertex_counter = 0
        self._iteration = 0

        # Create root vertex
        root = self._create_vertex(problem, generation=0)
        self._graph.add_vertex(root)

        if self._solution_checker(problem):
            root.is_solution = True
            return self._format_result()

        # Main reasoning loop
        current_vertices = [root]
        for gen in range(self.config.max_iterations):
            if self._iteration >= self.config.max_iterations:
                break
            if self._graph.num_vertices >= self.config.max_thoughts:
                break

            # Generate new thoughts from current vertices
            new_vertices = []
            for vertex in current_vertices:
                if self._iteration >= self.config.max_iterations:
                    break
                children = self._expand_vertex(vertex)
                new_vertices.extend(children)

            # Merge similar thoughts
            if self.config.enable_merging and new_vertices:
                new_vertices = self._merge_thoughts(new_vertices)

            # Refine thoughts
            if self.config.enable_refinement:
                new_vertices = self._refine_thoughts(new_vertices)

            # Check for solutions
            for v in new_vertices:
                if self._solution_checker(v.thought):
                    v.is_solution = True

            current_vertices = new_vertices
            if not current_vertices:
                break

        return self._format_result()

    def _create_vertex(self, thought: str, generation: int = 0) -> ThoughtVertex:
        """Create a new thought vertex."""
        self._vertex_counter += 1
        vertex = ThoughtVertex(
            vertex_id=f"v{self._vertex_counter}",
            thought=thought,
            score=self._thought_evaluator(thought),
            generation=generation,
        )
        self._iteration += 1
        return vertex

    def _expand_vertex(self, vertex: ThoughtVertex) -> List[ThoughtVertex]:
        """Expand a vertex by generating child thoughts."""
        thoughts = self._thought_generator(vertex.thought, self.config.branching_factor)
        children = []
        for thought in thoughts:
            child = self._create_vertex(thought, generation=vertex.generation + 1)
            self._graph.add_vertex(child)
            self._graph.add_edge(ThoughtEdge(
                source_id=vertex.vertex_id,
                target_id=child.vertex_id,
                edge_type="derives",
                weight=child.score,
            ))
            children.append(child)
        return children

    def _merge_thoughts(self, vertices: List[ThoughtVertex]) -> List[ThoughtVertex]:
        """Merge similar thoughts."""
        if len(vertices) < 2:
            return vertices

        merged = []
        used = set()

        for i, v1 in enumerate(vertices):
            if v1.vertex_id in used:
                continue
            for j, v2 in enumerate(vertices[i + 1:], i + 1):
                if v2.vertex_id in used:
                    continue
                # Check similarity (simplified: check if scores are close)
                if abs(v1.score - v2.score) < (1 - self.config.merge_threshold):
                    # Merge
                    merged_thought = self._thought_merger(v1.thought, v2.thought)
                    merged_vertex = self._create_vertex(merged_thought, generation=max(v1.generation, v2.generation))
                    merged_vertex.merged_from = [v1.vertex_id, v2.vertex_id]
                    merged_vertex.score = max(v1.score, v2.score)
                    self._graph.add_vertex(merged_vertex)
                    self._graph.add_edge(ThoughtEdge(v1.vertex_id, merged_vertex.vertex_id, "merges"))
                    self._graph.add_edge(ThoughtEdge(v2.vertex_id, merged_vertex.vertex_id, "merges"))
                    merged.append(merged_vertex)
                    used.add(v1.vertex_id)
                    used.add(v2.vertex_id)
                    break
            if v1.vertex_id not in used:
                merged.append(v1)

        return merged

    def _refine_thoughts(self, vertices: List[ThoughtVertex]) -> List[ThoughtVertex]:
        """Refine thoughts through iterative improvement."""
        refined = []
        for vertex in vertices:
            current = vertex
            for _ in range(self.config.refinement_rounds):
                if current.score >= 0.9:
                    break
                refined_thought = self._thought_refiner(current.thought)
                refined_vertex = self._create_vertex(refined_thought, generation=current.generation)
                refined_vertex.refined_count = current.refined_count + 1
                self._graph.add_vertex(refined_vertex)
                self._graph.add_edge(ThoughtEdge(
                    current.vertex_id, refined_vertex.vertex_id, "refines"
                ))
                current = refined_vertex
            refined.append(current)
        return refined

    def _default_generator(self, state: str, n: int) -> List[str]:
        return [f"Approach {i+1}: Extend reasoning from current state" for i in range(n)]

    def _default_evaluator(self, thought: str) -> float:
        if not thought:
            return 0.0
        return min(1.0, 0.3 + len(thought) / 500)

    def _default_merger(self, thought1: str, thought2: str) -> str:
        return f"Combined: {thought1[:100]} + {thought2[:100]}"

    def _default_refiner(self, thought: str) -> str:
        return f"Refined: {thought} (improved clarity and precision)"

    def _default_solution_checker(self, state: str) -> bool:
        patterns = ["the answer is", "final answer", "result:", "answer ="]
        return any(p in state.lower() for p in patterns)

    def _format_result(self) -> Dict[str, Any]:
        solutions = self._graph.get_solutions()
        if solutions:
            best = max(solutions, key=lambda v: v.score)
            return {
                "solved": True,
                "solution": best.thought,
                "confidence": best.score,
                "vertices": self._graph.num_vertices,
                "edges": self._graph.num_edges,
                "iterations": self._iteration,
            }
        best = self._graph.get_best_vertices(1)[0] if self._graph.num_vertices > 0 else None
        return {
            "solved": False,
            "solution": best.thought if best else "",
            "confidence": best.score if best else 0.0,
            "vertices": self._graph.num_vertices,
            "edges": self._graph.num_edges,
            "iterations": self._iteration,
        }

    def get_graph(self) -> ThoughtGraph:
        return self._graph