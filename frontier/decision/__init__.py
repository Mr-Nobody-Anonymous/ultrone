# Copyright (c) Ultrone Contributors. All rights reserved.
"""Frontier Decision Layer — uncertainty-aware, calibrated decision-making.

Combines uncertainty estimation, confidence calibration, and a Bayesian
decision layer so ULTRONE can act reliably under uncertainty, abstain when
unsure, and keep its confidence aligned with true correctness.
"""

from .uncertainty import UncertaintyEstimator, UncertaintyEstimate
from .calibration import ConfidenceCalibrator, CalibrationResult
from .bayesian_decision import BayesianDecisionLayer, Belief, Decision

__all__ = [
    "UncertaintyEstimator",
    "UncertaintyEstimate",
    "ConfidenceCalibrator",
    "CalibrationResult",
    "BayesianDecisionLayer",
    "Belief",
    "Decision",
]
