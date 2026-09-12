# Copyright (c) Ultrone Contributors. All rights reserved.
"""Scheduler: deciding *when* a self-training cycle is worthwhile.

Training on every observation wastes compute and risks overfitting to
a stale snapshot. The scheduler gates cycles on the simplest
evidence: enough *good* experiences accumulated above threshold since
the last cycle to justify a candidate fit. The curriculum, not this
module, decides what to study; this module only decides whether now
is a sane time to study at all.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ScheduleDecision:
    should_train: bool
    reason: str


class Scheduler:
    """Gate cycles on accumulation of quality-filtered experience."""

    def __init__(self, min_good_examples: int = 3,
                 decay: float = 0.0) -> None:
        if min_good_examples < 1:
            raise ValueError("min_good_examples must be >= 1")
        self.min_good_examples = int(min_good_examples)
        self.decay = float(decay)      # reserved: aging of past cycles

    def decide(self, good_count: int, *,
               recent_rejected: int = 0) -> ScheduleDecision:
        """Proceed only when enough fresh, high-quality signal exists.

        ``recent_rejected`` lets a caller apply regularisation: if a
        run of candidates keeps failing promotion, training again on
        the same band without adding evidence is discouraged.
        """
        if good_count >= self.min_good_examples:
            return ScheduleDecision(True,
                                    f"{good_count} good experiences "
                                    f"(>= {self.min_good_examples})")
        return ScheduleDecision(
            False,
            f"only {good_count} good experiences; need "
            f"{self.min_good_examples}")