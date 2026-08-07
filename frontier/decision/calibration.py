# Copyright (c) Ultrone Contributors. All rights reserved.
"""Confidence Calibration — align confidence with actual correctness.

Implements calibration evaluation and recalibration:

- **Expected Calibration Error (ECE)**: measures calibration quality.
- **Platt / temperature scaling**: a simple recalibration method.
- **Histogram binning**: bucketing confidences for reliability diagrams.

This is essential for the Bayesian decision layer: a well-calibrated agent
can decide when to abstain, defer, or act with confidence.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

logger = logging.getLogger("Ultrone.Frontier.Decision.Calibration")


@dataclass
class CalibrationResult:
    """The outcome of a calibration evaluation/scaling operation."""

    method: str
    ece: float = 0.0
    bins: int = 10
    num_samples: int = 0
    scale: float = 1.0
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "method": self.method,
            "ece": self.ece,
            "bins": self.bins,
            "num_samples": self.num_samples,
            "scale": self.scale,
            "details": self.details,
        }


class ConfidenceCalibrator:
    """Calibrates model confidences.

    Parameters
    ----------
    num_bins : int
        Number of bins for ECE computation.
    """

    def __init__(self, num_bins: int = 10) -> None:
        self.num_bins = num_bins
        self._scale: float = 1.0
        self._history: List[CalibrationResult] = []

    def compute_ece(
        self,
        confidences: Sequence[float],
        correct: Sequence[bool],
    ) -> float:
        """Compute the Expected Calibration Error.

        Parameters
        ----------
        confidences
            Predicted confidences in [0,1].
        correct
            Whether each prediction was correct.

        Returns
        -------
        float
            The ECE in [0,1] (lower is better).
        """
        if len(confidences) != len(correct) or not confidences:
            return 0.0
        ece = 0.0
        n = len(confidences)
        for b in range(self.num_bins):
            lo = b / self.num_bins
            hi = (b + 1) / self.num_bins
            in_bin = [
                (c, ok)
                for c, ok in zip(confidences, correct)
                if lo <= c < hi or (b == self.num_bins - 1 and c == 1.0)
            ]
            if not in_bin:
                continue
            bin_conf = sum(c for c, _ in in_bin) / len(in_bin)
            bin_acc = sum(1 for _, ok in in_bin if ok) / len(in_bin)
            ece += (len(in_bin) / n) * abs(bin_conf - bin_acc)
        return ece

    def reliability_diagram(
        self,
        confidences: Sequence[float],
        correct: Sequence[bool],
    ) -> List[Dict[str, Any]]:
        """Build the data for a reliability diagram.

        Returns
        -------
        List[Dict[str, Any]]
            A list of bin dictionaries with ``avg_confidence`` and ``accuracy``.
        """
        if len(confidences) != len(correct) or not confidences:
            return []
        diagram = []
        for b in range(self.num_bins):
            lo = b / self.num_bins
            hi = (b + 1) / self.num_bins
            in_bin = [
                (c, ok)
                for c, ok in zip(confidences, correct)
                if lo <= c < hi or (b == self.num_bins - 1 and c == 1.0)
            ]
            if not in_bin:
                continue
            diagram.append(
                {
                    "bin": b,
                    "avg_confidence": sum(c for c, _ in in_bin) / len(in_bin),
                    "accuracy": sum(1 for _, ok in in_bin if ok) / len(in_bin),
                    "count": len(in_bin),
                }
            )
        return diagram

    def temperature_scale(
        self,
        confidences: Sequence[float],
        correct: Sequence[bool],
    ) -> float:
        """Re-scale logits via temperature scaling to reduce ECE.

        Since this module works on confidence (not logit) values, we use a
        simple scalar correction: find the scale ``s`` minimizing ECE when
        confidences are transformed via a monotonic power mapping.

        Returns
        -------
        float
            The learned scale parameter.
        """
        if len(confidences) != len(correct) or not confidences:
            return 1.0
        best_scale = 1.0
        best_ece = self.compute_ece(confidences, correct)
        # Grid search over scales in [0.5, 2.0].
        for scale in [0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0]:
            rescaled = [self._rescale(c, scale) for c in confidences]
            ece = self.compute_ece(rescaled, correct)
            if ece < best_ece:
                best_ece = ece
                best_scale = scale
        self._scale = best_scale
        return best_scale

    @staticmethod
    def _rescale(confidence: float, scale: float) -> float:
        """Apply a monotonic recalibration mapping to a confidence."""
        if confidence <= 0.0 or confidence >= 1.0:
            return confidence
        # Map from [0,1] to logits, scale, then back to probability.
        logit = math.log(confidence / (1.0 - confidence))
        scaled_logit = logit / scale
        return 1.0 / (1.0 + math.exp(-scaled_logit))

    def calibrate(
        self,
        confidences: Sequence[float],
        correct: Sequence[bool],
    ) -> CalibrationResult:
        """Evaluate and recalibrate a set of (confidence, correctness) pairs.

        Returns
        -------
        CalibrationResult
            The ECE before scaling and the learned scale.
        """
        ece = self.compute_ece(confidences, correct)
        scale = self.temperature_scale(confidences, correct)
        result = CalibrationResult(
            method="temperature_scale",
            ece=ece,
            bins=self.num_bins,
            num_samples=len(confidences),
            scale=scale,
            details={"post_scale_ece": self.compute_ece(
                [self._rescale(c, scale) for c in confidences], correct
            )},
        )
        self._history.append(result)
        return result

    def get_scale(self) -> float:
        """Return the current learned scale parameter."""
        return self._scale

    def apply(self, confidence: float) -> float:
        """Apply the learned recalibration mapping to a confidence."""
        return self._rescale(confidence, self._scale)

    def get_stats(self) -> Dict[str, Any]:
        """Return aggregate statistics."""
        return {
            "calibrations": len(self._history),
            "scale": self._scale,
            "num_bins": self.num_bins,
        }
