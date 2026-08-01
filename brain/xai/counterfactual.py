# Copyright (c) Ultrone Contributors. All rights reserved.
"""Counterfactual explanations for model decisions."""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("Ultrone.Brain.XAI.Counterfactual")


@dataclass
class CounterfactualConfig:
    """Configuration for counterfactual generation."""
    max_iterations: int = 100
    step_size: float = 0.1


class CounterfactualExplainer:
    """Generates counterfactual explanations for model decisions."""

    def __init__(self, config: Optional[CounterfactualConfig] = None):
        self.config = config or CounterfactualConfig()

    def explain(
        self,
        x: np.ndarray,
        target_prediction: int = 0,
        model: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """Generate a counterfactual explanation for input ``x``.

        Args:
            x: Input sample (n_features,) or (n_samples, n_features).
            target_prediction: Desired target class (default 0).
            model: Optional model used for perturbation search.

        Returns:
            Dict with the counterfactual sample and perturbation distance.
        """
        x = np.asarray(x, dtype=float)
        if x.ndim == 2:
            x = x[0]
        counterfactual = x.copy()
        distance = 0.0
        if model is not None and self.config.max_iterations > 0:
            step = self.config.step_size
            for _ in range(self.config.max_iterations):
                perturbation = np.random.normal(0, step, size=x.shape)
                candidate = np.clip(counterfactual + perturbation, 0.0, 1.0)
                try:
                    pred = model(candidate.reshape(1, -1))
                    pred_class = int(np.argmax(pred)) if hasattr(pred, 'argmax') else int(pred)
                except Exception:
                    pred_class = target_prediction
                distance = float(np.linalg.norm(candidate - x))
                if pred_class == target_prediction:
                    counterfactual = candidate
                    break
                counterfactual = candidate
        return {
            "counterfactual": counterfactual.tolist(),
            "distance": distance,
        }

    def get_stats(self) -> Dict[str, Any]:
        return {"type": "CounterfactualExplainer"}

