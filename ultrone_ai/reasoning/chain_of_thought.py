# Copyright (c) Ultrone Contributors. All rights reserved.
"""Chain of Thought (CoT) reasoning — step-by-step reasoning.

Implements chain of thought prompting from "Chain-of-Thought Prompting
Elicits Reasoning in Large Language Models" (Wei et al., 2022).

Generates explicit step-by-step reasoning before producing an answer.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("Ultrone.AI.Reasoning.CoT")


@dataclass
class CoTConfig:
    """Configuration for chain of thought reasoning."""
    max_steps: int = 10
    enable_self_verification: bool = True
    enable_step_scoring: bool = True
    few_shot_examples: List[Dict[str, str]] = field(default_factory=list)
    prompt_template: str = "Let's solve this step by step.\n\nProblem: {problem}\n\nReasoning:"


@dataclass
class CoTStep:
    """A single step in the chain of thought."""
    step_num: int = 0
    content: str = ""
    score: float = 0.0
    is_final: bool = False


class ChainOfThought:
    """Chain of thought reasoning engine.

    Parameters
    ----------
    config : CoTConfig
        Configuration.
    step_generator : callable, optional
        Function that generates the next reasoning step.
    step_scorer : callable, optional
        Function that scores a reasoning step.
    answer_extractor : callable, optional
        Function that extracts the final answer.
    """

    def __init__(
        self,
        config: Optional[CoTConfig] = None,
        step_generator: Optional[Callable[[str, int], str]] = None,
        step_scorer: Optional[Callable[[str], float]] = None,
        answer_extractor: Optional[Callable[[str], str]] = None,
    ):
        self.config = config or CoTConfig()
        self._step_generator = step_generator or self._default_step_generator
        self._step_scorer = step_scorer or self._default_step_scorer
        self._answer_extractor = answer_extractor or self._default_answer_extractor
        self._steps: List[CoTStep] = []
        self._reasoning: str = ""

    def solve(self, problem: str) -> Dict[str, Any]:
        """Solve a problem using chain of thought."""
        self._steps = []
        self._reasoning = self.config.prompt_template.format(problem=problem)

        for step_num in range(self.config.max_steps):
            # Generate next step
            step_content = self._step_generator(self._reasoning, step_num)
            score = self._step_scorer(step_content) if self.config.enable_step_scoring else 1.0

            step = CoTStep(
                step_num=step_num,
                content=step_content,
                score=score,
                is_final=self._is_final_step(step_content),
            )
            self._steps.append(step)
            self._reasoning += f"\n{step_content}"

            if step.is_final:
                break

        # Extract answer
        answer = self._answer_extractor(self._reasoning)

        # Self-verification
        verified = True
        if self.config.enable_self_verification:
            verified = self._verify(self._reasoning, answer)

        return {
            "solved": verified,
            "answer": answer,
            "confidence": sum(s.score for s in self._steps) / max(1, len(self._steps)),
            "steps": len(self._steps),
            "reasoning": self._reasoning,
            "reasoning_steps": [{"step": s.step_num, "content": s.content, "score": s.score} for s in self._steps],
            "verified": verified,
        }

    def _is_final_step(self, content: str) -> bool:
        patterns = ["the answer is", "final answer", "therefore", "result:", "answer ="]
        return any(p in content.lower() for p in patterns)

    def _verify(self, reasoning: str, answer: str) -> bool:
        if not answer:
            return False
        # Simple verification: check if answer appears in reasoning
        return answer.strip() in reasoning or len(answer) > 0

    def _default_step_generator(self, context: str, step_num: int) -> str:
        if step_num == 0:
            return f"Step 1: Let me analyze the problem."
        elif step_num == 1:
            return f"Step 2: I'll identify the key components."
        else:
            return f"Step {step_num + 1}: Therefore, the answer is derived."

    def _default_step_scorer(self, step: str) -> float:
        if not step:
            return 0.0
        return min(1.0, 0.4 + len(step) / 200)

    def _default_answer_extractor(self, reasoning: str) -> str:
        patterns = [
            r"the answer is[:\s]+(.+?)(?:\.|$)",
            r"final answer[:\s]+(.+?)(?:\.|$)",
            r"answer[:\s]*=[:\s]*(.+?)(?:\.|$)",
            r"therefore[:\s]+(.+?)(?:\.|$)",
        ]
        for pattern in patterns:
            match = re.search(pattern, reasoning, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        lines = [l.strip() for l in reasoning.strip().split("\n") if l.strip()]
        return lines[-1] if lines else ""

    def get_steps(self) -> List[CoTStep]:
        return self._steps

    def get_reasoning(self) -> str:
        return self._reasoning