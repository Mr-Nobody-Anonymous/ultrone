# Copyright (c) Ultrone Contributors. All rights reserved.
"""Uncertainty Estimation — quantify model/decision uncertainty.

Implements multiple uncertainty estimation techniques suitable for LLM
and agentic decision layers:

- **Ensemble disagreement**: variance/entropy across multiple samples.
- **Token-level entropy**: approximated from repeated samples.
- **Confidence calibration** hooks via :class:`ConfidenceEstimator`.

The estimates feed the Bayesian decision layer and the self-improvement loop
so the system can know when to trust its own answers.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Ultrone.Frontier.Decision.Uncertainty")


@dataclass
class UncertaintyEstimate:
    """The result of an uncertainty estimation."""

    method: str
    estimate: float  # 0..1, higher = more uncertain
    samples: int = 0
    entropy: float = 0.0
    variance: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)

    def confidence(self) -> float:
        """Return the derived confidence (1 - uncertainty)."""
        return max(0.0, min(1.0, 1.0 - self.estimate))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "method": self.method,
            "estimate": self.estimate,
            "samples": self.samples,
            "entropy": self.entropy,
            "variance": self.variance,
            "confidence": self.confidence(),
            "details": self.details,
        }


class UncertaintyEstimator:
    """Estimates decision uncertainty from multiple samples.

    Parameters
    ----------
    method : str
        One of ``"ensemble"``, ``"entropy"``, or ``"variance"``.
    sample_vocab : Optional[List[str]]
        The set of possible answer tokens used for entropy normalization.
    """

    def __init__(self, method: str = "ensemble", sample_vocab: Optional[List[str]] = None) -> None:
        self.method = method
        self.sample_vocab = sample_vocab
        self._history: List[UncertaintyEstimate] = []

    def estimate(self, samples: List[str]) -> UncertaintyEstimate:
        """Estimate uncertainty from a list of sampled answers.

        Returns
        -------
        UncertaintyEstimate
            Quantified uncertainty with a derived confidence.
        """
        if not samples:
            est = UncertaintyEstimate(method=self.method, estimate=1.0, samples=0)
            self._history.append(est)
            return est

        if self.method == "entropy":
            est = self._entropy(samples)
        elif self.method == "variance":
            est = self._variance(samples)
        else:
            est = self._ensemble(samples)

        self._history.append(est)
        return est

    def _ensemble(self, samples: List[str]) -> UncertaintyEstimate:
        """Disagreement-based uncertainty (1 - majority fraction)."""
        counts: Dict[str, int] = {}
        for s in samples:
            counts[s] = counts.get(s, 0) + 1
        best_count = max(counts.values())
        majority_frac = best_count / len(samples)
        # Normalize: 0 disagreement -> 0 uncertainty, 0.5 majority -> ~1.0
        uncertainty = 1.0 - (majority_frac - 0.5) * 2  # range [0,1]
        uncertainty = max(0.0, min(1.0, uncertainty))

        # Entropy of the distribution
        entropy = self._compute_entropy(counts, len(samples))

        return UncertaintyEstimate(
            method="ensemble",
            estimate=uncertainty,
            samples=len(samples),
            entropy=entropy,
            variance=self._compute_variance_scalar(samples),
            details={"agreement": majority_frac},
        )

    def _entropy(self, samples: List[str]) -> UncertaintyEstimate:
        """Normalized Shannon entropy of the sample distribution."""
        counts: Dict[str, int] = {}
        for s in samples:
            counts[s] = counts.get(s, 0) + 1
        entropy = self._compute_entropy(counts, len(samples))
        # Normalize entropy by log(num_unique) for 0..1 range.
        max_entropy = math.log(max(1, len(counts)))
        normalized = entropy / max_entropy if max_entropy > 0 else 0.0
        return UncertaintyEstimate(
            method="entropy",
            estimate=normalized,
            samples=len(samples),
            entropy=entropy,
            variance=self._compute_variance_scalar(samples),
        )

    def _variance(self, samples: List[str]) -> UncertaintyEstimate:
        """Normalized variance-based uncertainty (via token overlap)."""
        variance = self._compute_variance_scalar(samples)
        # Approximate normalized variance in [0,1].
        uncertainty = min(1.0, variance)
        return UncertaintyEstimate(
            method="variance",
            estimate=uncertainty,
            samples=len(samples),
            variance=variance,
            details={"scaled_variance": uncertainty},
        )

    @staticmethod
    def _compute_entropy(counts: Dict[str, int], total: int) -> float:
        """Compute Shannon entropy (in nats) of a categorical distribution."""
        if total == 0:
            return 0.0
        entropy = 0.0
        for count in counts.values():
            p = count / total
            if p > 0:
                entropy -= p * math.log(p)
        return entropy

    @staticmethod
    def _compute_variance_scalar(samples: List[str]) -> float:
        """Compute a scalar variance proxy from string samples.

        Uses the average pairwise normalized Levenshtein distance as a
        diversity proxy. Falls back to 0.0 for identical samples.
        """
        if not samples or len(samples) < 2:
            return 0.0
        total = 0.0
        pairs = 0
        for i in range(len(samples)):
            for j in range(i + 1, len(samples)):
                total += UncertaintyEstimator._normalized_levenshtein(samples[i], samples[j])
                pairs += 1
        return total / pairs if pairs else 0.0

    @staticmethod
    def _normalized_levenshtein(a: str, b: str) -> float:
        """Return normalized Levenshtein distance in [0,1]."""
        if a == b:
            return 0.0
        if not a or not b:
            return 1.0
        prev = list(range(len(b) + 1))
        for i, ca in enumerate(a, 1):
            curr = [i]
            for j, cb in enumerate(b, 1):
                cost = 0 if ca == cb else 1
                curr.append(min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + cost))
            prev = curr
        distance = prev[len(b)]
        return distance / max(len(a), len(b))

    def get_history(self) -> List[UncertaintyEstimate]:
        """Return all uncertainty estimates."""
        return list(self._history)

    def get_stats(self) -> Dict[str, Any]:
        """Return aggregate statistics."""
        if not self._history:
            return {"estimates": 0, "avg_uncertainty": 0.0}
        avg = sum(e.estimate for e in self._history) / len(self._history)
        return {"estimates": len(self._history), "avg_uncertainty": avg}
