# Copyright (c) Ultrone Contributors. All rights reserved.
"""Feedback extractor — extracts preference signals from user interactions.

Analyzes user corrections, ratings, and implicit signals to produce
structured preference signals for training.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .experience_db import InteractionRecord

logger = logging.getLogger("Ultrone.Learning.Feedback.Extractor")


@dataclass
class FeedbackSignal:
    """A structured preference signal extracted from an interaction."""

    prompt: str
    preferred_response: str
    dispreferred_response: str = ""
    preference_strength: float = 0.5
    signal_type: str = "explicit"  # explicit, implicit, correction
    task_category: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "prompt": self.prompt,
            "preferred_response": self.preferred_response,
            "dispreferred_response": self.dispreferred_response,
            "preference_strength": self.preference_strength,
            "signal_type": self.signal_type,
            "task_category": self.task_category,
            "metadata": self.metadata,
        }


class FeedbackExtractor:
    """Extracts preference signals from interaction records."""

    def extract(self, record: InteractionRecord) -> Optional[FeedbackSignal]:
        """Extract a preference signal from an interaction.

        Returns None if no usable signal is present.
        """
        # 1. Explicit correction: user provided a corrected answer
        if record.user_correction and record.model_response:
            return FeedbackSignal(
                prompt=record.prompt,
                preferred_response=record.user_correction,
                dispreferred_response=record.model_response,
                preference_strength=0.9,
                signal_type="correction",
                task_category=record.task_category,
            )

        # 2. Explicit rating: high rating = preferred, low = dispreferred
        if record.explicit_rating is not None:
            if record.explicit_rating >= 4.0:
                return FeedbackSignal(
                    prompt=record.prompt,
                    preferred_response=record.final_accepted_answer or record.model_response,
                    preference_strength=0.7,
                    signal_type="explicit",
                    task_category=record.task_category,
                )
            if record.explicit_rating <= 2.0:
                return FeedbackSignal(
                    prompt=record.prompt,
                    preferred_response=record.final_accepted_answer or "",
                    dispreferred_response=record.model_response,
                    preference_strength=0.6,
                    signal_type="explicit",
                    task_category=record.task_category,
                )

        # 3. Implicit feedback: strong positive/negative signal
        if abs(record.implicit_feedback) > 0.5:
            if record.implicit_feedback > 0:
                return FeedbackSignal(
                    prompt=record.prompt,
                    preferred_response=record.final_accepted_answer or record.model_response,
                    preference_strength=abs(record.implicit_feedback),
                    signal_type="implicit",
                    task_category=record.task_category,
                )
            return FeedbackSignal(
                prompt=record.prompt,
                preferred_response=record.final_accepted_answer or "",
                dispreferred_response=record.model_response,
                preference_strength=abs(record.implicit_feedback),
                signal_type="implicit",
                task_category=record.task_category,
            )

        return None

    def extract_all(self, records: List[InteractionRecord]) -> List[FeedbackSignal]:
        """Extract signals from multiple interactions."""
        signals = []
        for record in records:
            signal = self.extract(record)
            if signal is not None:
                signals.append(signal)
        return signals

    def get_stats(self) -> Dict[str, Any]:
        """Return extractor statistics."""
        return {"type": "FeedbackExtractor"}