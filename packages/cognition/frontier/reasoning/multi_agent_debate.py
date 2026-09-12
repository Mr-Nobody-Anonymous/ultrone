# Copyright (c) Ultrone Contributors. All rights reserved.
"""Multi-Agent Debate reasoning strategy.

Implements the Multi-Agent Debate approach from Du et al. (2023,
"Improving Factuality and Reasoning in Language Models through Multiagent
Debate") as a pluggable :class:`ReasoningStrategy`.

Multiple solver "agents" propose answers, then critique each other's answers
across several rounds, converging on a consensus. Because each agent is just a
``Solver``, the debate is fully backend-agnostic and never hardcodes answers.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .base import ReasoningResult, ReasoningStrategy, Solver

logger = logging.getLogger("Ultrone.Frontier.Reasoning.Debate")


@dataclass
class DebateConfig:
    """Configuration for the Multi-Agent Debate strategy."""

    num_agents: int = 3
    num_rounds: int = 2
    temperature: float = 0.7
    consensus_mode: str = "majority"  # "majority" or "proposer"


class MultiAgentDebate(ReasoningStrategy):
    """Multi-Agent Debate reasoning strategy.

    Parameters
    ----------
    solvers : Optional[List[Solver]]
        The list of solver agents participating in the debate. If fewer than
        ``num_agents`` are provided, the first solver is reused to fill in.
    judge : Optional[Callable]
        Optional callable that picks the final answer from proposed answers.
    **config
        Overrides for :class:`DebateConfig`.
    """

    def __init__(
        self,
        solvers: Optional[List[Solver]] = None,
        judge: Optional[Callable[..., str]] = None,
        **config: Any,
    ) -> None:
        super().__init__(solver=(solvers[0] if solvers else None), **config)
        self.cfg = DebateConfig(**{k: v for k, v in config.items() if hasattr(DebateConfig, k)})
        self._solvers = list(solvers) if solvers else []
        self._judge = judge

    def strategy_name(self) -> str:
        return "multi_agent_debate"

    def solve(self, prompt: str, **kwargs: Any) -> ReasoningResult:
        """Run a debate among solver agents and return the consensus."""
        num_agents = kwargs.get("num_agents", self.cfg.num_agents)
        solvers = self._ensure_solvers(num_agents)

        # Round 0: each agent proposes an independent answer.
        answers: List[str] = [s(prompt, temperature=self.cfg.temperature) for s in solvers]
        steps: List[str] = [f"Round 0: {len(answers)} initial proposals"]

        # Subsequent rounds: critique / revise.
        for round_num in range(1, self.cfg.num_rounds + 1):
            new_answers: List[str] = []
            for i, solver in enumerate(solvers):
                others = [a for j, a in enumerate(answers) if j != i]
                critique_prompt = self._build_critique_prompt(prompt, answers[i], others)
                revised = solver(critique_prompt, temperature=self.cfg.temperature)
                new_answers.append(revised)
            answers = new_answers
            steps.append(f"Round {round_num}: agents revised answers after critique")

        # Final consensus.
        final_answer, confidence = self._consensus(prompt, answers)

        return ReasoningResult(
            solution=final_answer,
            confidence=confidence,
            candidates=list(answers),
            metadata={"num_agents": len(solvers), "num_rounds": self.cfg.num_rounds, "steps": steps},
        )

    def _ensure_solvers(self, num_agents: int) -> List[Solver]:
        """Ensure at least ``num_agents`` solvers are available."""
        if not self._solvers:
            raise ValueError("MultiAgentDebate requires at least one solver")
        solvers = list(self._solvers)
        while len(solvers) < num_agents:
            solvers.append(solvers[0])
        return solvers[:num_agents]

    def _build_critique_prompt(self, prompt: str, current: str, others: List[str]) -> str:
        """Build a prompt asking an agent to critique/revise its answer."""
        others_text = "\n".join(f"- Agent {i+1}: {a}" for i, a in enumerate(others))
        return (
            f"{prompt}\n\nYour current answer:\n{current}\n\n"
            f"Other agents' answers:\n{others_text}\n\n"
            f"Review these answers, identify weaknesses, and provide a revised, "
            f"improved final answer."
        )

    def _consensus(self, prompt: str, answers: List[str]) -> "tuple[str, float]":
        """Aggregate the final answers into a consensus."""
        if self._judge is not None:
            chosen = self._judge(prompt, answers)
            return chosen, 0.8

        # Majority voting on the stripped answer.
        if self.cfg.consensus_mode == "majority":
            from collections import Counter
            tally = Counter(a.strip() for a in answers)
            best = max(tally, key=tally.get)
            return best, tally[best] / len(answers)

        # Otherwise, return the first solver's answer.
        return answers[0], 1.0 / len(answers)
