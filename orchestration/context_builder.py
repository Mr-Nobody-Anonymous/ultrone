# Copyright (c) Ultrone Contributors. All rights reserved.
"""Context assembly under a token budget.

The context builder turns a TaskProfile plus the selected memory
strategy into a concrete working-context plan: which sections exist,
how many tokens each gets, and whether anything had to be truncated.
It never fabricates content -- with no live backend attached it plans
structure deterministically; real deployments fill the same structure
from stores. Truncation is reported, never silent, because the
validator treats silently-dropped context as an unexplained quality
loss.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple

from orchestration.memory_router import MemoryStrategy
from orchestration.task_classifier import TaskProfile

#: Rough section proportions of the planned budget.
_SECTION_SHARES = (("task", 0.45), ("recalled_memory", 0.35),
                   ("tool_preflight", 0.20))


@dataclass(frozen=True)
class ContextBundle:
    """Deterministic description of the context a run will operate on."""

    task_id: str
    memory_strategy: str
    tokens_requested: int
    tokens_provided: int
    truncated: bool
    sections: Tuple[Tuple[str, int], ...]

    def to_dict(self):
        return {
            "task_id": self.task_id,
            "memory_strategy": self.memory_strategy,
            "tokens_requested": self.tokens_requested,
            "tokens_provided": self.tokens_provided,
            "truncated": self.truncated,
            "sections": [list(s) for s in self.sections],
        }


def build_context(profile: TaskProfile, strategy: MemoryStrategy,
                  token_budget: int) -> ContextBundle:
    """Plan the context payload for one routed run.

    ``token_budget`` is the effective window available for this run
    (model window minus policy headroom); demand comes from the
    profile. Sections are filled proportionally -- unless recalled
    memory contributes nothing (the ``none`` strategy), in which case
    its share is redistributed to the task itself rather than wasted.
    """
    requested = profile.context_tokens
    provided = min(requested, max(token_budget, 1))
    use_memory = strategy.recall_boost > 0.0

    sections = []
    remaining = provided
    shares = [(name, share) for name, share in _SECTION_SHARES
              if use_memory or name != "recalled_memory"]
    total_share = sum(share for _, share in shares)
    for index, (name, share) in enumerate(shares):
        if index == len(shares) - 1:
            allocation = remaining            # last takes rounding rest
        else:
            allocation = int(provided * share / total_share)
            remaining -= allocation
        sections.append((name, max(allocation, 0)))

    return ContextBundle(
        task_id=profile.task_id,
        memory_strategy=strategy.name,
        tokens_requested=requested,
        tokens_provided=provided,
        truncated=requested > provided,
        sections=tuple(sections),
    )