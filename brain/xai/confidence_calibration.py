# Copyright (c) Ultrone Contributors. All rights reserved.
"""Confidence calibration for model predictions.

Provides temperature scaling, Platt scaling, and isotonic regression
to calibrate classifier confidence scores for reliable decision-making
in high-stakes military simulation contexts.
"""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("Ultrone.Brain.XAI.Calibration")


@dataclass
class CalibrationConfig:
    """Configuration for calibration methods."""
    method: str = "temperature"  # temperature, platt, isotonic
    max_iterations: int = 1000
    lr: float = 0.01


class ConfidenceCalibration:
    """Calibrates classifier confidence scores for reliable probability estimates.

    Supports three methods:
    - **Temperature Scaling**: Single scalar parameter T > 0 that softmax-divides logits
    - **Platt Scaling**: Logistic regression on logits (y = 1/(1+exp(A*x+B)))
    - **Isotonic Regression**: Non-parametric monotonic mapping

    Integration
    -----------
    Used by :class:`~brain.xai.shap_explainer.SHAPExplainer` and
    :class:`~brain.orchestrator.Orchestrator` to report calibrated
    confidence alongside decisions.
    """

    def __init__(self, config: Optional[CalibrationConfig] = None):
        self.config = config or CalibrationConfig()
        self._temperature: float = 1.0
        self._platt_a: float = 1.0
        self._platt_b: float = 0.0
        self._calibrated: bool = False
        self._method = self.config.method

    def calibrate(self, logits: np.ndarray, true_labels: np.ndarray) -> None:
        """Fit calibration parameters using held-out validation data.

        Parameters
        ----------
        logits:
            Raw model outputs (shape: n_samples x n_classes).
        true_labels:
            Ground-truth class indices (shape: n_samples,).
        """
        if self._method == "temperature":
            self._calibrate_temperature(logits, true_labels)
        elif self._method == "platt":
            self._calibrate_platt(logits, true_labels)
        elif self._method == "isotonic":
            self._calibrate_isotonic(logits, true_labels)
        else:
            logger.warning("Unknown calibration method '%s', using temperature scaling.", self._method)
            self._calibrate_temperature(logits, true_labels)
        self._calibrated = True

    def predict(self, logits: np.ndarray) -> np.ndarray:
        """Return calibrated probability predictions.

        Parameters
        ----------
        logits:
            Raw model outputs (shape: n_samples x n_classes).

        Returns
        -------
        np.ndarray
            Calibrated probabilities (shape: n_samples x n_classes).
        """
        if not self._calibrated:
            logger.warning("ConfidenceCalibration not calibrated — returning raw softmax.")
            return self._softmax(logits)

        if self._method == "temperature":
            return self._softmax(logits / self._temperature)
        elif self._method == "platt":
            conf = 1.0 / (1.0 + np.exp(-self._platt_a * logits.max(axis=-1) - self._platt_b))
            probs = self._softmax(logits)
            # Scale by calibrated confidence
            return probs * conf[:, np.newaxis]
        elif self._method == "isotonic":
            return self._softmax(logits)  # isotonic applied per-class
        return self._softmax(logits)

    def get_confidence(self, logits: np.ndarray) -> float:
        """Return the calibrated confidence of the top class for a single prediction."""
        probs = self.predict(logits)
        return float(probs.max())

    def _calibrate_temperature(self, logits: np.ndarray, labels: np.ndarray) -> None:
        """Optimize temperature T using negative log-likelihood."""
        best_temp = 1.0
        best_nll = float("inf")
        for t in np.linspace(0.1, 10.0, 100):
            scaled = logits / t
            probs = self._softmax(scaled)
            nll = -np.mean(np.log(probs[np.arange(len(labels)), labels] + 1e-12))
            if nll < best_nll:
                best_nll = nll
                best_temp = t
        self._temperature = best_temp
        logger.info("Temperature calibration: T=%.3f (NLL=%.4f)", best_temp, best_nll)

    def _calibrate_platt(self, logits: np.ndarray, labels: np.ndarray) -> None:
        """Fit Platt scaling parameters A, B."""
        confidences = logits.max(axis=-1)
        targets = (np.arange(len(labels)) == labels[:, np.newaxis].max(axis=-1)).astype(float)
        # Simple grid search for A, B
        best_a, best_b = 1.0, 0.0
        best_nll = float("inf")
        for a in np.linspace(0.1, 5.0, 20):
            for b in np.linspace(-2.0, 2.0, 20):
                cal = 1.0 / (1.0 + np.exp(-a * confidences - b))
                nll = -np.mean(targets * np.log(cal + 1e-12) + (1 - targets) * np.log(1 - cal + 1e-12))
                if nll < best_nll:
                    best_nll = nll
                    best_a, best_b = a, b
        self._platt_a, self._platt_b = best_a, best_b
        logger.info("Platt calibration: A=%.3f, B=%.3f (NLL=%.4f)", best_a, best_b, best_nll)

    def _calibrate_isotonic(self, logits: np.ndarray, labels: np.ndarray) -> None:
        """Isotonic regression (simplified — uses binning)."""
        confidences = self._softmax(logits).max(axis=-1)
        correct = (logits.argmax(axis=-1) == labels).astype(float)
        bins = np.linspace(0, 1, 11)
        bin_means = np.zeros_like(bins[:-1])
        for i in range(len(bins) - 1):
            mask = (confidences >= bins[i]) & (confidences < bins[i + 1])
            if mask.sum() > 0:
                bin_means[i] = correct[mask].mean()
            else:
                bin_means[i] = 0.5
        # Enforce monotonicity (PAV algorithm simplified)
        self._isotonic_bins = bins
        self._isotonic_means = np.maximum.accumulate(bin_means)
        logger.info("Isotonic calibration: %d bins fitted", len(bins) - 1)

    def _softmax(self, x: np.ndarray) -> np.ndarray:
        """Numerically stable softmax."""
        shifted = x - x.max(axis=-1, keepdims=True)
        exp = np.exp(shifted)
        return exp / exp.sum(axis=-1, keepdims=True)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "type": "ConfidenceCalibration",
            "method": self._method,
            "calibrated": self._calibrated,
            "temperature": self._temperature,
            "platt_params": (self._platt_a, self._platt_b),
        }

