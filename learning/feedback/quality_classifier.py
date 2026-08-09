# Copyright (c) Ultrone Contributors. All rights reserved.
"""Quality classifier for user feedback signals.

Classifies user feedback into quality tiers (excellent, good, poor, harmful)
using a rule-based + ML hybrid approach. Feeds signals into the training
pipeline for preference optimization.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Ultrone.Learning.Feedback.QualityClassifier")


class FeedbackQuality(Enum):
    """Quality tiers for feedback classification."""
    EXCELLENT = "excellent"
    GOOD = "good"
    NEUTRAL = "neutral"
    POOR = "poor"
    HARMFUL = "harmful"


class SignalStrength(Enum):
    """Strength of a feedback signal."""
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"


@dataclass
class FeedbackSignal:
    """Extracted signal from a single user feedback interaction."""
    category: str
    signal: str
    strength: SignalStrength
    confidence: float
    source: str  # "explicit_rating", "correction", "implicit", "conversation_end"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FeedbackFeatures:
    """Feature vector for quality classification."""
    explicit_rating: Optional[float] = None  # -1 to 1
    correction_length_ratio: float = 0.0  # relative length of correction vs response
    has_correction: bool = False
    conversation_end: bool = False  # User stopped responding without accepting
    response_length: int = 0
    tool_calls_made: int = 0
    retrieval_sources: int = 0
    negative_keywords: int = 0
    positive_keywords: int = 0
    prompt_injection_flag: bool = False


class QualityClassifier:
    """Classifies feedback quality using rule-based + heuristic scoring.

    The classifier examines:
    - Explicit ratings (thumb up/down, star ratings)
    - Corrections (user edited the response)
    - Implicit signals (conversation ending without acceptance, response length)
    - Keyword analysis (positive/negative sentiment indicators)
    - Safety flags (prompt injection, harmful content)
    """

    POSITIVE_KEYWORDS = {
        "good", "great", "excellent", "perfect", "awesome", "helpful",
        "thanks", "thank you", "correct", "right", "yes", "accurate",
        "useful", "amazing", "wonderful", "fantastic", "great job",
    }
    NEGATIVE_KEYWORDS = {
        "bad", "wrong", "incorrect", "terrible", "awful", "useless",
        "stupid", "dumb", "hate", "hated", "pointless", "worthless",
        "nonsense", "boring", "slow", "buggy", "broken", "error",
    }
    INJECTION_PATTERNS = [
        r"ignore (all |previous )?instructions",
        r"disregard (all |previous )?instructions",
        r"new instructions:",
        r"system prompt:",
        r"forget (all |previous )?instructions",
        r"you are now (in |mode)",
        r"override (all |previous )?safety",
        r"bypass (safety|filter|security)",
    ]

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._feedback_history: List[FeedbackSignal] = []
        self._quality_history: List[Dict[str, Any]] = []

    def classify(self, features: FeedbackFeatures) -> Tuple[FeedbackQuality, float]:
        """Classify feedback quality and return (quality, confidence).

        Returns a tuple of (FeedbackQuality, confidence_score 0-1).
        """
        score = 0.0
        signal_count = 0

        # Explicit rating contribution
        if features.explicit_rating is not None:
            score += features.explicit_rating  # -1 to 1
            signal_count += 1

        # Correction contribution
        if features.has_correction:
            if features.correction_length_ratio < 0.3:
                score -= 0.5  # Small correction = significant error
            else:
                score -= 0.2  # Large correction = minor issue
            signal_count += 1

        # Conversation end (no acceptance)
        if features.conversation_end:
            score -= 0.3
            signal_count += 1

        # Keyword sentiment
        keyword_score = features.positive_keywords - features.negative_keywords
        if keyword_score != 0:
            score += keyword_score * 0.15
            signal_count += 1

        # Safety flags
        if features.prompt_injection_flag:
            score -= 1.0
            signal_count += 1

        # Tool use quality (more tools = more complex, weight accordingly)
        if features.tool_calls_made > 0:
            signal_count += 0.2

        # Retrieval quality
        if features.retrieval_sources > 0:
            signal_count += 0.1

        # Normalize score
        if signal_count > 0:
            score = score / signal_count

        # Clamp to [-1, 1]
        score = max(-1.0, min(1.0, score))

        # Map score to quality tier
        quality = self._score_to_quality(score)
        confidence = abs(score) * 0.9 + 0.1  # At least 0.1 confidence

        return quality, confidence

    def _score_to_quality(self, score: float) -> FeedbackQuality:
        """Map numerical score to quality tier."""
        if score >= 0.6:
            return FeedbackQuality.EXCELLENT
        elif score >= 0.2:
            return FeedbackQuality.GOOD
        elif score >= -0.2:
            return FeedbackQuality.NEUTRAL
        elif score >= -0.6:
            return FeedbackQuality.POOR
        else:
            return FeedbackQuality.HARMFUL

    def extract_features(
        self,
        prompt: str,
        model_response: str,
        user_correction: Optional[str] = None,
        explicit_rating: Optional[float] = None,
        conversation_ended: bool = False,
        tools_used: Optional[List[str]] = None,
        retrieved_docs: Optional[List[Dict]] = None,
    ) -> FeedbackFeatures:
        """Extract features from a feedback interaction."""
        features = FeedbackFeatures(
            explicit_rating=explicit_rating,
            has_correction=user_correction is not None,
            correction_length_ratio=(
                len(user_correction) / max(len(model_response), 1)
                if user_correction else 0.0
            ),
            conversation_end=conversation_ended,
            response_length=len(model_response),
            tool_calls_made=len(tools_used) if tools_used else 0,
            retrieval_sources=len(retrieved_docs) if retrieved_docs else 0,
        )

        # Keyword analysis on response text
        lower = model_response.lower()
        text = " ".join(re.findall(r'\w+', lower))
        words = set(text.split())

        features.positive_keywords = len(words & self.POSITIVE_KEYWORDS)
        features.negative_keywords = len(words & self.NEGATIVE_KEYWORDS)

        # Prompt injection check on combined text
        combined = (prompt + " " + model_response + " " + (user_correction or "")).lower()
        features.prompt_injection_flag = any(
            re.search(pattern, combined, re.IGNORECASE)
            for pattern in self.INJECTION_PATTERNS
        )

        return features

    def process_feedback(
        self,
        prompt: str,
        model_response: str,
        user_correction: Optional[str] = None,
        explicit_rating: Optional[float] = None,
        conversation_ended: bool = False,
        tools_used: Optional[List[str]] = None,
        retrieved_docs: Optional[List[Dict]] = None,
        task_category: str = "general",
    ) -> Dict[str, Any]:
        """Process a full feedback interaction and return classification."""
        features = self.extract_features(
            prompt, model_response, user_correction, explicit_rating,
            conversation_ended, tools_used, retrieved_docs,
        )
        quality, confidence = self.classify(features)

        signal = FeedbackSignal(
            category=task_category,
            signal=quality.value,
            strength=SignalStrength.STRONG if abs(confidence) > 0.7 else SignalStrength.MODERATE,
            confidence=confidence,
            source="explicit_rating" if explicit_rating is not None else (
                "correction" if user_correction else "implicit"
            ),
            metadata={"features": features.__dict__},
        )

        self._feedback_history.append(signal)
        result = {
            "quality": quality.value,
            "confidence": confidence,
            "features": features.__dict__,
            "signal": signal,
            "timestamp": __import__("time").time(),
        }
        self._quality_history.append(result)

        logger.info(
            "Feedback classified: quality=%s confidence=%.2f category=%s",
            quality.value, confidence, task_category,
        )
        return result

    def get_signal_statistics(self) -> Dict[str, Any]:
        """Return statistics on classified feedback signals."""
        from collections import Counter
        quality_counts = Counter(s.signal for s in self._feedback_history)
        category_counts = Counter(s.category for s in self._feedback_history)
        return {
            "total_feedback": len(self._feedback_history),
            "quality_distribution": dict(quality_counts),
            "category_distribution": dict(category_counts),
            "average_confidence": (
                sum(s.confidence for s in self._feedback_history) / max(len(self._feedback_history), 1)
            ),
        }
