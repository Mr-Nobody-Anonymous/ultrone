# Copyright (c) Ultrone Contributors. All rights reserved.
"""Counterfactual Regret Minimization (CFR) for imperfect-information games."""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Ultrone.Brain.Reasoning.GameTheory.CFR")


@dataclass
class CFRConfig:
    """Configuration for CFR."""
    max_iterations: int = 10000
    discount_factor: float = 1.0
    use_linear_cfr: bool = True


class CFR:
    """Counterfactual Regret Minimization for approximating Nash equilibrium
    in imperfect-information extensive-form games."""

    def __init__(self, config: Optional[CFRConfig] = None):
        self.config = config or CFRConfig()
        self._regret: Dict[str, np.ndarray] = {}
        self._strategy: Dict[str, np.ndarray] = {}
        self._cumulative_strategy: Dict[str, np.ndarray] = {}

    def train(self, num_actions: int, info_sets: List[str]) -> Dict[str, Any]:
        """Run CFR training.

        Args:
            num_actions: Number of actions per information set
            info_sets: List of information set identifiers

        Returns:
            Dict with average strategy for each info set
        """
        for info_set in info_sets:
            self._regret[info_set] = np.zeros(num_actions)
            self._cumulative_strategy[info_set] = np.zeros(num_actions)

        for iteration in range(self.config.max_iterations):
            for info_set in info_sets:
                self._update_strategy(info_set, iteration)

        # Compute average strategy
        avg_strategy = {}
        for info_set in info_sets:
            total = self._cumulative_strategy[info_set].sum()
            avg_strategy[info_set] = (self._cumulative_strategy[info_set] / max(total, 1e-10)).tolist()

        return {"avg_strategy": avg_strategy, "iterations": self.config.max_iterations}

    def _update_strategy(self, info_set: str, iteration: int) -> None:
        regret = self._regret[info_set]
        strategy = np.maximum(regret, 0)
        total = strategy.sum()
        if total > 0:
            strategy = strategy / total
        else:
            strategy = np.ones_like(regret) / len(regret)
        self._strategy[info_set] = strategy
        weight = iteration + 1 if self.config.use_linear_cfr else 1.0
        self._cumulative_strategy[info_set] += weight * strategy

    def get_stats(self) -> Dict[str, Any]:
        return {"type": "CFR", "info_sets": len(self._regret)}