"""Scientific metrics computation for AI autonomy evaluations."""

from __future__ import annotations

import math
from typing import List, Sequence, Tuple


def calculate_task_accuracy(predictions: Sequence[Any], ground_truth: Sequence[Any]) -> float:
    if not predictions or len(predictions) != len(ground_truth):
        return 0.0
    correct = sum(1 for p, g in zip(predictions, ground_truth) if p == g)
    return correct / len(predictions)


def calculate_brier_score(predicted_probs: Sequence[float], binary_outcomes: Sequence[int | bool]) -> float:
    """Calculates Mean Squared Error of probabilistic forecasts (Brier Score)."""
    if not predicted_probs or len(predicted_probs) != len(binary_outcomes):
        return 1.0
    total = sum((p - (1.0 if y else 0.0)) ** 2 for p, y in zip(predicted_probs, binary_outcomes))
    return total / len(predicted_probs)


def calculate_safety_violation_rate(violations: int, total_steps: int) -> float:
    if total_steps <= 0:
        return 0.0
    return max(0.0, min(1.0, violations / total_steps))


def calculate_expected_calibration_error(
    probabilities: Sequence[float],
    outcomes: Sequence[int | bool],
    n_bins: int = 10,
) -> float:
    """Calculates Expected Calibration Error (ECE)."""
    if not probabilities or len(probabilities) != len(outcomes):
        return 1.0

    bin_boundaries = [i / n_bins for i in range(n_bins + 1)]
    ece = 0.0
    n = len(probabilities)

    for i in range(n_bins):
        low, high = bin_boundaries[i], bin_boundaries[i + 1]
        bin_indices = [
            idx for idx, p in enumerate(probabilities)
            if low <= p < high or (i == n_bins - 1 and p == high)
        ]
        if not bin_indices:
            continue
        bin_size = len(bin_indices)
        bin_acc = sum(1 for idx in bin_indices if outcomes[idx]) / bin_size
        bin_conf = sum(probabilities[idx] for idx in bin_indices) / bin_size
        ece += (bin_size / n) * abs(bin_acc - bin_conf)

    return ece
