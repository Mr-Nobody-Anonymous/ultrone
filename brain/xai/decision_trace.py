# Copyright (c) Ultrone Contributors. All rights reserved.
"""Decision trace generation for explainable AI."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Ultrone.Brain.XAI.DecisionTrace")


@dataclass
class DecisionTraceConfig:
    """Configuration for decision tracing."""
    max_trace_length: int = 100
    include_alternatives: bool = True


@dataclass
class TraceStep:
    """A single step in a decision trace."""
    step_id: int
    action: str
    state: Dict[str, Any]
    reasoning: str
    alternatives: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


class DecisionTrace:
    """Generates step-by-step decision traces for explainability."""

    def __init__(self, config: Optional[DecisionTraceConfig] = None):
        self.config = config or DecisionTraceConfig()
        self._steps: List[TraceStep] = []
        self._current_step = 0

    def add_step(self, action: str, state: Dict[str, Any], reasoning: str,
                 alternatives: Optional[List[str]] = None) -> None:
        step = TraceStep(
            step_id=self._current_step,
            action=action,
            state=state,
            reasoning=reasoning,
            alternatives=alternatives or [],
        )
        self._steps.append(step)
        self._current_step += 1
        if len(self._steps) > self.config.max_trace_length:
            self._steps.pop(0)

    def get_trace(self) -> List[TraceStep]:
        return self._steps.copy()

    def get_summary(self) -> str:
        lines = []
        for step in self._steps:
            lines.append(f"Step {step.step_id}: {step.action} — {step.reasoning}")
        return "\n".join(lines)

    def clear(self) -> None:
        self._steps.clear()
        self._current_step = 0

    def get_stats(self) -> Dict[str, Any]:
        return {"type": "DecisionTrace", "steps": len(self._steps)}