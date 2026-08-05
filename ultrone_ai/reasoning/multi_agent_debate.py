# Copyright (c) Ultrone Contributors. All rights reserved.
"""Multi-Agent Debate — collaborative reasoning through debate.

Implements multi-agent debate from "Improving Factuality and Reasoning in
Language Models through Multiagent Debate" (Du et al., 2023).

Multiple agents independently generate answers, then critique and refine
each other's answers through multiple rounds of debate.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("Ultrone.AI.Reasoning.Debate")


@dataclass
class DebateConfig:
    """Configuration for multi-agent debate."""
    num_agents: int = 3
    num_rounds: int = 3
    agent_names: List[str] = field(default_factory=lambda: ["Analyst", "Critic", "Synthesizer"])
    consensus_threshold: float = 0.7
    enable_critique: bool = True
    enable_synthesis: bool = True


@dataclass
class AgentResponse:
    """A single agent's response in a debate round."""
    agent_name: str = ""
    round_num: int = 0
    answer: str = ""
    critique: str = ""
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class MultiAgentDebate:
    """Multi-agent debate reasoning engine.

    Parameters
    ----------
    config : DebateConfig
        Configuration.
    answer_generator : callable, optional
        Function that generates an answer: (problem: str, agent_name: str) -> str
    critique_generator : callable, optional
        Function that generates a critique: (answer: str, agent_name: str) -> str
    synthesis_generator : callable, optional
        Function that synthesizes multiple answers: (answers: List[str]) -> str
    """

    def __init__(
        self,
        config: Optional[DebateConfig] = None,
        answer_generator: Optional[Callable[[str, str], str]] = None,
        critique_generator: Optional[Callable[[str, str], str]] = None,
        synthesis_generator: Optional[Callable[[List[str]], str]] = None,
    ):
        self.config = config or DebateConfig()
        self._answer_generator = answer_generator or self._default_answer_generator
        self._critique_generator = critique_generator or self._default_critique_generator
        self._synthesis_generator = synthesis_generator or self._default_synthesis_generator
        self._debate_history: List[List[AgentResponse]] = []

    def solve(self, problem: str) -> Dict[str, Any]:
        """Solve a problem through multi-agent debate."""
        self._debate_history = []
        agent_names = self.config.agent_names[: self.config.num_agents]
        if len(agent_names) < self.config.num_agents:
            agent_names.extend([f"Agent_{i}" for i in range(len(agent_names), self.config.num_agents)])

        # Round 0: Initial answers
        responses: List[AgentResponse] = []
        for name in agent_names:
            answer = self._answer_generator(problem, name)
            responses.append(AgentResponse(
                agent_name=name,
                round_num=0,
                answer=answer,
                confidence=self._compute_confidence(answer),
            ))
        self._debate_history.append(responses)

        # Subsequent rounds: critique and refine
        for round_num in range(1, self.config.num_rounds):
            new_responses: List[AgentResponse] = []
            for i, name in enumerate(agent_names):
                # Get other agents' answers from previous round
                other_answers = [r.answer for j, r in enumerate(responses) if j != i]

                # Generate critique of others
                critique = ""
                if self.config.enable_critique and other_answers:
                    critique = self._critique_generator(" | ".join(other_answers), name)

                # Generate refined answer
                context = f"Problem: {problem}\nPrevious answer: {responses[i].answer}\nCritique: {critique}"
                refined = self._answer_generator(context, name)
                new_responses.append(AgentResponse(
                    agent_name=name,
                    round_num=round_num,
                    answer=refined,
                    critique=critique,
                    confidence=self._compute_confidence(refined),
                ))

            responses = new_responses
            self._debate_history.append(responses)

            # Check for consensus
            if self._check_consensus(responses):
                break

        # Synthesize final answer
        final_answer = responses[0].answer
        if self.config.enable_synthesis:
            all_answers = [r.answer for r in responses]
            final_answer = self._synthesis_generator(all_answers)

        return {
            "solved": True,
            "answer": final_answer,
            "confidence": sum(r.confidence for r in responses) / len(responses),
            "rounds": len(self._debate_history),
            "agents": len(agent_names),
            "consensus_reached": self._check_consensus(responses),
            "debate_history": [
                [{"agent": r.agent_name, "answer": r.answer, "confidence": r.confidence}
                 for r in round_responses]
                for round_responses in self._debate_history
            ],
        }

    def _check_consensus(self, responses: List[AgentResponse]) -> bool:
        """Check if agents have reached consensus."""
        if len(responses) < 2:
            return True
        confidences = [r.confidence for r in responses]
        avg_conf = sum(confidences) / len(confidences)
        return avg_conf >= self.config.consensus_threshold

    def _compute_confidence(self, answer: str) -> float:
        if not answer:
            return 0.0
        return min(1.0, 0.3 + len(answer) / 500)

    def _default_answer_generator(self, problem: str, agent_name: str) -> str:
        return f"[{agent_name}] Analysis of: {problem[:100]}. The answer is derived."

    def _default_critique_generator(self, other_answers: str, agent_name: str) -> str:
        return f"[{agent_name}] The other answers have merit but may be improved."

    def _default_synthesis_generator(self, answers: List[str]) -> str:
        return f"Synthesized answer from {len(answers)} agents: {answers[0][:100]}"

    def get_debate_history(self) -> List[List[AgentResponse]]:
        return self._debate_history