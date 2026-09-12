# Copyright (c) Ultrone Contributors. All rights reserved.
"""Beam Search Reasoner.

A reasoning strategy that performs beam search over intermediate reasoning
steps. At each level, the top ``beam_width`` partial reasonings (beams) are
kept, and each beam is expanded into several candidate next steps. Final
answers are generated from the surviving beams.

This mirrors the classic beam-search decoding used to improve LLM reasoning
(and is closely related to the beam-search variant of ToT), but is implemented
as an independent, backend-agnostic strategy.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from .base import ReasoningResult, ReasoningStrategy, Solver

logger = logging.getLogger("Ultrone.Frontier.Reasoning.Beam")


@dataclass
class BeamSearchConfig:
    """Configuration for the Beam Search Reasoner."""

    beam_width: int = 3
    max_depth: int = 3
    expansions_per_beam: int = 3
    temperature: float = 0.7


class BeamSearchReasoner(ReasoningStrategy):
    """Beam Search Reasoner strategy.

    Parameters
    ----------
    solver : Optional[Solver]
        The backend solver used to expand beams and generate final answers.
    step_generator : Optional[Callable]
        Optional callable producing candidate next reasoning steps for a beam.
    **config
        Overrides for :class:`BeamSearchConfig`.
    """

    def __init__(
        self,
        solver: Optional[Solver] = None,
        step_generator: Optional[Callable[..., List[str]]] = None,
        **config: Any,
    ) -> None:
        super().__init__(solver=solver, **config)
        self.cfg = BeamSearchConfig(**{
            k: v for k, v in config.items() if hasattr(BeamSearchConfig, k)
        })
        self._step_generator = step_generator

    def strategy_name(self) -> str:
        return "beam_search"

    def solve(self, prompt: str, **kwargs: Any) -> ReasoningResult:
        """Solve ``prompt`` via beam search over reasoning steps."""
        if self.solver is None:
            raise ValueError("BeamSearchReasoner requires a solver")

        beam_width = kwargs.get("beam_width", self.cfg.beam_width)
        max_depth = kwargs.get("max_depth", self.cfg.max_depth)

        # Beams are represented as (cumulative_text, path, score).
        beams: List[Tuple[str, List[str], float]] = [("", [], 1.0)]
        steps: List[str] = [f"Starting beam search (width={beam_width}, depth={max_depth})"]

        for level in range(max_depth):
            candidates: List[Tuple[str, List[str], float]] = []
            for text, path, score in beams:
                next_steps = self._generate_steps(prompt, text)
                for step in next_steps[: self.cfg.expansions_per_beam]:
                    new_text = (text + "\n" + step).strip()
                    new_path = path + [step]
                    # Heuristic: prefer longer, more specific steps (scores grow
                    # slowly with depth but are normalized relative to siblings).
                    candidates.append((new_text, new_path, score * (1.0 + 0.1 * len(step) / 100)))

            if not candidates:
                steps.append(f"Level {level}: no expansions, stopping")
                break

            candidates.sort(key=lambda item: item[2], reverse=True)
            beams = candidates[:beam_width]
            steps.append(f"Level {level}: kept {len(beams)} beams")

        # Generate a final answer from the best beam.
        best_text, best_path, best_score = beams[0]
        final_prompt = f"{prompt}\n\nReasoning path:\n{best_text}\n\nFinal answer:"
        solution = self.solver(final_prompt, temperature=self.cfg.temperature)

        return ReasoningResult(
            solution=solution,
            confidence=min(1.0, best_score / (1.0 + 0.1 * max_depth)),
            candidates=[text for text, _, _ in beams],
            metadata={"beam_width": beam_width, "steps": steps},
        )

    def _generate_steps(self, prompt: str, current_text: str) -> List[str]:
        """Generate candidate next reasoning steps for a beam."""
        if self._step_generator is not None:
            return self._step_generator(prompt, current_text, self.cfg)
        gen_prompt = (
            f"{prompt}\n\nCurrent partial reasoning:\n{current_text or '(start)'}\n\n"
            f"Generate up to {self.cfg.expansions_per_beam} distinct next reasoning "
            f"steps. Output each on its own line, prefixed with '- '."
        )
        raw = self.solver(gen_prompt, temperature=self.cfg.temperature)
        steps = [
            line.strip().lstrip("- ").strip()
            for line in raw.splitlines()
            if line.strip()
        ]
        return steps[: self.cfg.expansions_per_beam]
