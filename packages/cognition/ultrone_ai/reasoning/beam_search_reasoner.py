# Copyright (c) Ultrone Contributors. All rights reserved.
"""Beam Search Reasoner — efficient approximate search over reasoning paths.

Implements beam search for reasoning, keeping the top-k most promising
partial solutions at each step. More memory-efficient than ToT while
still exploring multiple paths.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("Ultrone.AI.Reasoning.BeamSearch")


@dataclass
class BeamSearchConfig:
    """Configuration for beam search reasoning."""
    beam_width: int = 5
    max_steps: int = 10
    branching_factor: int = 3
    pruning_threshold: float = 0.05
    length_penalty: float = 0.1  # Penalty for longer sequences


@dataclass
class BeamState:
    """A state in the beam."""
    content: str = ""
    score: float = 0.0
    steps: List[str] = field(default_factory=list)
    is_complete: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def length(self) -> int:
        return len(self.steps)


class BeamSearchReasoner:
    """Beam search reasoning engine.

    Parameters
    ----------
    config : BeamSearchConfig
        Configuration.
    step_generator : callable, optional
        Function that generates next steps: (state: str, n: int) -> List[str]
    state_scorer : callable, optional
        Function that scores a state: (state: str) -> float
    completion_checker : callable, optional
        Function that checks if a state is complete: (state: str) -> bool
    """

    def __init__(
        self,
        config: Optional[BeamSearchConfig] = None,
        step_generator: Optional[Callable[[str, int], List[str]]] = None,
        state_scorer: Optional[Callable[[str], float]] = None,
        completion_checker: Optional[Callable[[str], bool]] = None,
    ):
        self.config = config or BeamSearchConfig()
        self._step_generator = step_generator or self._default_step_generator
        self._state_scorer = state_scorer or self._default_state_scorer
        self._completion_checker = completion_checker or self._default_completion_checker
        self._beam_history: List[List[BeamState]] = []

    def solve(self, problem: str) -> Dict[str, Any]:
        """Solve a problem using beam search."""
        self._beam_history = []

        # Initialize beam with the problem
        initial_state = BeamState(
            content=problem,
            score=self._state_scorer(problem),
            steps=[problem],
        )

        if self._completion_checker(problem):
            initial_state.is_complete = True
            return self._format_result([initial_state])

        beam = [initial_state]

        for step in range(self.config.max_steps):
            self._beam_history.append(list(beam))

            # Generate candidates from all beam states
            candidates: List[BeamState] = []
            for state in beam:
                if state.is_complete:
                    candidates.append(state)
                    continue

                # Generate next steps
                next_steps = self._step_generator(state.content, self.config.branching_factor)
                for next_step in next_steps:
                    new_content = f"{state.content}\n{next_step}"
                    raw_score = self._state_scorer(new_content)
                    # Apply length penalty
                    penalized_score = raw_score - self.config.length_penalty * (state.length + 1)
                    new_state = BeamState(
                        content=new_content,
                        score=penalized_score,
                        steps=state.steps + [next_step],
                        is_complete=self._completion_checker(new_content),
                    )
                    candidates.append(new_state)

            # Prune and select top beam_width
            candidates.sort(key=lambda s: s.score, reverse=True)
            candidates = [c for c in candidates if c.score >= self.config.pruning_threshold]
            beam = candidates[: self.config.beam_width]

            # Check if all states are complete
            if all(s.is_complete for s in beam):
                break

            if not beam:
                break

        return self._format_result(beam)

    def _default_step_generator(self, state: str, n: int) -> List[str]:
        return [f"Reasoning step {i+1}" for i in range(n)]

    def _default_state_scorer(self, state: str) -> float:
        if not state:
            return 0.0
        return min(1.0, 0.3 + len(state) / 500)

    def _default_completion_checker(self, state: str) -> bool:
        patterns = ["the answer is", "final answer", "result:", "answer ="]
        return any(p in state.lower() for p in patterns)

    def _format_result(self, beam: List[BeamState]) -> Dict[str, Any]:
        if not beam:
            return {"solved": False, "solution": "", "confidence": 0.0, "steps": 0}
        best = max(beam, key=lambda s: s.score)
        return {
            "solved": best.is_complete,
            "solution": best.content,
            "confidence": best.score,
            "steps": best.length,
            "reasoning_path": best.steps,
            "beam_size": len(beam),
        }

    def get_beam_history(self) -> List[List[BeamState]]:
        return self._beam_history