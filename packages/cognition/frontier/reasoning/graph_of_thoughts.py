# Copyright (c) Ultrone Contributors. All rights reserved.
"""Graph of Thoughts (GoT) reasoning strategy.

Implements the Graph-of-Thoughts approach from Besta et al. (2023,
"Graph of Thoughts: Solving Elaborate Problems with Large Language Models")
as a pluggable :class:`ReasoningStrategy`.

Unlike linear chain-of-thought or the tree of thoughts, GoT models reasoning
as an arbitrary directed graph (DAG) where intermediate "thoughts" may be
aggregated, combined, and refined. This enables operations such as:

- **Merge**: combine several thoughts into one.
- **Aggregate**: collect thoughts produced for a sub-problem.
- **Refine / critique**: improve a thought through rounds.

The graph is built generically; the actual operations are performed by a
``Solver`` (an LLM or test double), so no benchmark answers are hardcoded.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from .base import ReasoningResult, ReasoningStrategy, Solver

logger = logging.getLogger("Ultrone.Frontier.Reasoning.GoT")


@dataclass
class GoTConfig:
    """Configuration for the Graph of Thoughts strategy."""

    num_initial_thoughts: int = 4
    aggregation_rounds: int = 2
    max_refinements: int = 2
    temperature: float = 0.7


@dataclass
class ThoughtNode:
    """A single thought node in the reasoning graph."""

    id: int
    content: str
    parents: List[int] = field(default_factory=list)
    children: List[int] = field(default_factory=list)
    score: float = 0.5


class GraphOfThoughts(ReasoningStrategy):
    """Graph of Thoughts reasoning strategy.

    Parameters
    ----------
    solver : Optional[Solver]
        The backend solver used to generate and aggregate thoughts.
    thought_generator : Optional[Callable]
        A callable producing ``n`` initial thoughts from ``prompt``.
    aggregator : Optional[Callable]
        A callable merging a list of thought strings into one.
    **config
        Overrides for :class:`GoTConfig`.
    """

    def __init__(
        self,
        solver: Optional[Solver] = None,
        thought_generator: Optional[Callable[..., List[str]]] = None,
        aggregator: Optional[Callable[..., str]] = None,
        **config: Any,
    ) -> None:
        super().__init__(solver=solver, **config)
        self.cfg = GoTConfig(**{k: v for k, v in config.items() if hasattr(GoTConfig, k)})
        self._thought_generator = thought_generator
        self._aggregator = aggregator

    def strategy_name(self) -> str:
        return "graph_of_thoughts"

    def solve(self, prompt: str, **kwargs: Any) -> ReasoningResult:
        """Solve ``prompt`` by building and aggregating a reasoning graph."""
        if self.solver is None:
            raise ValueError("GraphOfThoughts requires a solver")

        # 1. Generate initial thoughts (the "source" nodes of the graph).
        initial = self._generate_initial_thoughts(prompt)
        nodes: List[ThoughtNode] = []
        for idx, content in enumerate(initial):
            nodes.append(ThoughtNode(id=idx, content=content))
        steps: List[str] = [f"Generated {len(initial)} initial thoughts"]

        # 2. Iteratively aggregate groups of thoughts into higher-level ones.
        round_num = 0
        while len(nodes) > 1 and round_num < self.cfg.aggregation_rounds:
            round_num += 1
            # Group nodes (pairwise merge) and create aggregate nodes.
            ids = [n.id for n in nodes]
            new_nodes: List[ThoughtNode] = []
            next_id = max(n.id for n in nodes) + 1
            for i in range(0, len(ids) - 1, 2):
                a = ids[i]
                b = ids[i + 1]
                merged_content = self._aggregate(
                    prompt, [nodes[j].content for j in range(len(nodes)) if nodes[j].id in (a, b)]
                )
                merged = ThoughtNode(
                    id=next_id,
                    content=merged_content,
                    parents=[a, b],
                    score=0.5 + 0.1 * round_num,
                )
                # Link parent children.
                for node in nodes:
                    if node.id in (a, b):
                        node.children.append(merged.id)
                new_nodes.append(merged)
                next_id += 1
            # If an odd node remains, keep it as-is.
            if len(ids) % 2 == 1 and len(ids) > 1:
                last_id = ids[-1]
                last_node = next(n for n in nodes if n.id == last_id)
                new_nodes.append(last_node)
            nodes.extend(new_nodes)
            steps.append(
                f"Aggregation round {round_num}: graph now has {len(nodes)} nodes"
            )

        # 3. Optionally refine the final aggregated thought.
        final_node = max(nodes, key=lambda n: n.score)
        solution = final_node.content
        if self.cfg.max_refinements > 0:
            solution = self._refine(prompt, solution, self.cfg.max_refinements)
            steps.append(f"Refined final solution ({self.cfg.max_refinements} round(s))")

        return ReasoningResult(
            solution=solution,
            confidence=min(1.0, final_node.score + 0.1),
            metadata={"num_nodes": len(nodes), "steps": steps},
        )

    def _generate_initial_thoughts(self, prompt: str) -> List[str]:
        """Generate the initial set of thoughts for the graph."""
        n = self.cfg.num_initial_thoughts
        if self._thought_generator is not None:
            return self._thought_generator(prompt, n, self.cfg)[:n]
        gen_prompt = (
            f"{prompt}\n\nGenerate {n} distinct, independent solution ideas or "
            f"reasoning directions. Output each idea on its own line, prefixed with '- '."
        )
        raw = self.solver(gen_prompt, temperature=self.cfg.temperature)
        thoughts = [
            line.strip().lstrip("- ").strip()
            for line in raw.splitlines()
            if line.strip()
        ]
        return thoughts[:n]

    def _aggregate(self, prompt: str, thoughts: List[str]) -> str:
        """Merge a list of thoughts into a single higher-level thought."""
        if self._aggregator is not None:
            return self._aggregator(prompt, thoughts)
        if not thoughts:
            return ""
        if len(thoughts) == 1:
            return thoughts[0]
        joined = "\n".join(f"- {t}" for t in thoughts)
        agg_prompt = (
            f"{prompt}\n\nCombine the following solution ideas into one coherent "
            f"best answer, retaining the strongest reasoning:\n{joined}"
        )
        return self.solver(agg_prompt, temperature=self.cfg.temperature).strip()

    def _refine(self, prompt: str, solution: str, rounds: int) -> str:
        """Refine a solution through iterative improvement."""
        current = solution
        for _ in range(rounds):
            refine_prompt = (
                f"{prompt}\n\nReview and improve the following solution. Fix any "
                f"errors, tighten reasoning, and return the best version:\n{current}"
            )
            current = self.solver(refine_prompt, temperature=self.cfg.temperature).strip()
        return current
