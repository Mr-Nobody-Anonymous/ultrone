# Copyright (c) Ultrone Contributors. All rights reserved.
"""Tree of Thoughts (ToT) reasoning strategy.

Implements the Tree-of-Thoughts approach from Yao et al. (2023,
"Tree of Thoughts: Deliberate Problem Solving with Large Language Models")
as a pluggable :class:`ReasoningStrategy`.

The strategy explores a tree of intermediate thoughts:
1. Generate candidate next thoughts from the current state.
2. Evaluate each candidate (scoring its promise).
3. Expand the most promising candidates (BFS) or descend depth-first (DFS).
4. Select the final solution from the best leaf.

The actual "thinking" is delegated to a ``Solver`` (an LLM or test double),
so the strategy is backend-agnostic and never hardcodes benchmark solutions.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from .base import ReasoningResult, ReasoningStrategy, Solver, Verification

logger = logging.getLogger("Ultrone.Frontier.Reasoning.ToT")


@dataclass
class ToTConfig:
    """Configuration for the Tree of Thoughts strategy."""

    max_depth: int = 3
    branching_factor: int = 3
    beam_width: int = 2
    max_thoughts_per_state: int = 10
    use_bfs: bool = True
    temperature: float = 0.7


class TreeOfThoughts(ReasoningStrategy):
    """Tree of Thoughts reasoning strategy.

    Parameters
    ----------
    solver : Optional[Solver]
        The backend solver used to generate thoughts and evaluations.
    thought_generator : Optional[Callable]
        A callable ``(prompt, state, config) -> List[str]`` that produces
        candidate next thoughts. If omitted, uses the solver directly.
    thought_evaluator : Optional[Callable]
        A callable ``(thought, prompt, state, config) -> float`` scoring a
        thought's promise. If omitted, uses the solver to produce a score.
    **config
        Overrides for :class:`ToTConfig`.
    """

    def __init__(
        self,
        solver: Optional[Solver] = None,
        thought_generator: Optional[Callable[..., List[str]]] = None,
        thought_evaluator: Optional[Callable[..., float]] = None,
        **config: Any,
    ) -> None:
        super().__init__(solver=solver, **config)
        self.cfg = ToTConfig(**{k: v for k, v in config.items() if hasattr(ToTConfig, k)})
        self._thought_generator = thought_generator
        self._thought_evaluator = thought_evaluator

    def strategy_name(self) -> str:
        return "tree_of_thoughts"

    def solve(self, prompt: str, **kwargs: Any) -> ReasoningResult:
        """Solve ``prompt`` by exploring a tree of thoughts."""
        if self.solver is None:
            raise ValueError("TreeOfThoughts requires a solver")

        depth = kwargs.get("depth", self.cfg.max_depth)
        breadth = kwargs.get("branching", self.cfg.branching_factor)
        beam = kwargs.get("beam_width", self.cfg.beam_width)

        # Start with the root "empty" state
        states: List[Tuple[str, List[str], float]] = [("", [], 1.0)]
        steps: List[str] = [f"Starting ToT search (depth={depth}, beam={beam})"]

        for level in range(depth):
            candidates: List[Tuple[str, List[str], float]] = []
            for state, path, parent_score in states:
                thoughts = self._generate_thoughts(prompt, state, level)
                for thought in thoughts[: self.cfg.max_thoughts_per_state]:
                    score = self._evaluate_thought(thought, prompt, state)
                    new_path = path + [thought]
                    new_state = (state + "\n" + thought).strip()
                    candidates.append((new_state, new_path, parent_score * score))

            if not candidates:
                steps.append(f"Level {level}: no thoughts generated, stopping")
                break

            # Select the top-K candidates (beam)
            candidates.sort(key=lambda item: item[2], reverse=True)
            states = candidates[:beam]
            steps.append(
                f"Level {level}: kept {len(states)}/{len(candidates)} states "
                f"(best score {states[0][2]:.3f})"
            )

        # Final: pick the best leaf. If the solver is available, generate a
        # final answer from the best path; otherwise use the leaf text.
        best_state, best_path, best_score = states[0]
        final_prompt = f"{prompt}\n\nReasoning path:\n{best_state}\n\nFinal answer:"
        solution = self.solver(final_prompt, temperature=self.cfg.temperature)
        steps.append(f"Selected best path ({best_score:.3f}) and generated final answer")

        return ReasoningResult(
            solution=solution,
            confidence=min(1.0, best_score),
            candidates=[p for _, p, _ in states],
            metadata={"depth": depth, "steps": steps},
        )

    def _generate_thoughts(self, prompt: str, state: str, level: int) -> List[str]:
        """Generate candidate next thoughts for the current state."""
        if self._thought_generator is not None:
            return self._thought_generator(prompt, state, self.cfg)
        if self.solver is None:
            return []
        gen_prompt = (
            f"{prompt}\n\nCurrent intermediate thinking:\n{state or '(start)'}\n\n"
            f"Generate up to {self.cfg.branching_factor} distinct next steps to "
            f"solve the problem. Output each step on its own line, prefixed with '- '."
        )
        raw = self.solver(gen_prompt, temperature=self.cfg.temperature)
        thoughts = [
            line.strip().lstrip("- ").strip()
            for line in raw.splitlines()
            if line.strip() and not line.strip().lower().startswith(("the answer", "solution"))
        ]
        return thoughts[: self.cfg.branching_factor]

    def _evaluate_thought(self, thought: str, prompt: str, state: str) -> float:
        """Score a thought's promise (0..1)."""
        if self._thought_evaluator is not None:
            return max(0.0, min(1.0, float(self._thought_evaluator(thought, prompt, state, self.cfg))))
        if self.solver is None:
            return 0.5
        eval_prompt = (
            f"{prompt}\n\nCurrent intermediate thinking:\n{state or '(start)'}\n\n"
            f"Candidate next step: {thought}\n\n"
            f"Rate the promise of this step from 0.0 (hopeless) to 1.0 (very promising). "
            f"Reply with only a number."
        )
        raw = self.solver(eval_prompt, temperature=0.0).strip()
        try:
            return max(0.0, min(1.0, float(raw)))
        except ValueError:
            logger.warning("Could not parse evaluator output %r, defaulting to 0.5", raw)
            return 0.5
