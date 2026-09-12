# Copyright (c) Ultrone Contributors. All rights reserved.
"""ReAct Agent — Reasoning + Acting for tool use.

Implements ReAct from "ReAct: Synergizing Reasoning and Acting in Language
Models" (Yao et al., 2022). Interleaves reasoning steps with tool actions.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("Ultrone.AI.Reasoning.ReAct")


@dataclass
class ReActConfig:
    """Configuration for ReAct agent."""
    max_steps: int = 10
    max_actions: int = 5
    tools: Dict[str, Callable] = field(default_factory=dict)
    enable_observation: bool = True


@dataclass
class ReActStep:
    """A single ReAct step."""
    step_num: int = 0
    thought: str = ""
    action: str = ""
    action_input: str = ""
    observation: str = ""
    is_final: bool = False


class ReActAgent:
    """ReAct reasoning + acting agent.

    Parameters
    ----------
    config : ReActConfig
        Configuration with available tools.
    thought_generator : callable, optional
        Function that generates a thought: (context: str) -> str
    action_selector : callable, optional
        Function that selects an action: (context: str) -> (action, input)
    """

    def __init__(
        self,
        config: Optional[ReActConfig] = None,
        thought_generator: Optional[Callable[[str], str]] = None,
        action_selector: Optional[Callable[[str], tuple]] = None,
    ):
        self.config = config or ReActConfig()
        self._thought_generator = thought_generator or self._default_thought_generator
        self._action_selector = action_selector or self._default_action_selector
        self._steps: List[ReActStep] = []
        self._context: str = ""

    def solve(self, problem: str) -> Dict[str, Any]:
        """Solve a problem using ReAct."""
        self._steps = []
        self._context = f"Problem: {problem}"

        for step_num in range(self.config.max_steps):
            # Generate thought
            thought = self._thought_generator(self._context)
            self._context += f"\nThought: {thought}"

            # Check if we can answer directly
            if self._is_final(thought):
                step = ReActStep(
                    step_num=step_num,
                    thought=thought,
                    is_final=True,
                )
                self._steps.append(step)
                break

            # Select and execute action
            action, action_input = self._action_selector(self._context)
            observation = self._execute_action(action, action_input)

            step = ReActStep(
                step_num=step_num,
                thought=thought,
                action=action,
                action_input=action_input,
                observation=observation,
            )
            self._steps.append(step)
            self._context += f"\nAction: {action}({action_input})\nObservation: {observation}"

        return {
            "solved": self._steps[-1].is_final if self._steps else False,
            "answer": self._steps[-1].thought if self._steps else "",
            "steps": len(self._steps),
            "actions_taken": sum(1 for s in self._steps if s.action),
            "context": self._context,
            "step_history": [
                {"step": s.step_num, "thought": s.thought, "action": s.action,
                 "action_input": s.action_input, "observation": s.observation}
                for s in self._steps
            ],
        }

    def _execute_action(self, action: str, action_input: str) -> str:
        """Execute a tool action."""
        if action in self.config.tools:
            try:
                result = self.config.tools[action](action_input)
                return str(result)
            except Exception as e:
                return f"Error: {e}"
        return f"Unknown action: {action}"

    def _is_final(self, thought: str) -> bool:
        patterns = ["the answer is", "final answer", "therefore", "answer ="]
        return any(p in thought.lower() for p in patterns)

    def _default_thought_generator(self, context: str) -> str:
        return "Let me analyze the current state and determine the next step."

    def _default_action_selector(self, context: str) -> tuple:
        return "search", "query"

    def get_steps(self) -> List[ReActStep]:
        return self._steps