"""Counterfactual and interventional reasoning for causal decision analysis."""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("Ultrone.Brain.Reasoning.DecisionIntelligence.CounterfactualReasoner")


@dataclass
class CFConfig:
    """Configuration for counterfactual reasoning."""
    num_samples: int = 1000
    intervention_noise: float = 0.1
    counterfactual_std: float = 0.05
    max_iterations: int = 50
    tolerance: float = 1e-4


@dataclass
class CounterfactualResult:
    """Result of counterfactual reasoning."""
    factual_outcome: float
    counterfactual_outcome: float
    causal_effect: float
    intervention: Dict[str, Any]
    confidence: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)


class CounterfactualReasoner:
    """Performs counterfactual and interventional reasoning on causal models."""

    def __init__(self, config: Optional[CFConfig] = None):
        self.config = config or CFConfig()

    def compute_counterfactual(self, factual_state: Dict[str, float],
                                intervention: Dict[str, float],
                                causal_graph: Optional[Dict[str, List[str]]] = None) -> CounterfactualResult:
        """Compute what would have happened under a different intervention."""
        factual_outcome = self._evaluate_state(factual_state)
        counterfactual_state = dict(factual_state)
        counterfactual_state.update(intervention)

        if causal_graph:
            counterfactual_state = self._propagate_intervention(
                counterfactual_state, intervention, causal_graph
            )

        counterfactual_outcome = self._evaluate_state(counterfactual_state)
        causal_effect = counterfactual_outcome - factual_outcome

        return CounterfactualResult(
            factual_outcome=factual_outcome,
            counterfactual_outcome=counterfactual_outcome,
            causal_effect=causal_effect,
            intervention=intervention,
            confidence=self._estimate_confidence(factual_state, intervention),
        )

    def compute_multiple_counterfactuals(self, factual_state: Dict[str, float],
                                          interventions: List[Dict[str, float]],
                                          causal_graph: Optional[Dict[str, List[str]]] = None) -> List[CounterfactualResult]:
        """Compute multiple counterfactuals for different interventions."""
        return [self.compute_counterfactual(factual_state, inv, causal_graph)
                for inv in interventions]

    def find_best_intervention(self, factual_state: Dict[str, float],
                                possible_interventions: List[Dict[str, float]],
                                objective: str = "maximize",
                                causal_graph: Optional[Dict[str, List[str]]] = None) -> CounterfactualResult:
        """Find the intervention that maximizes or minimizes the outcome."""
        results = self.compute_multiple_counterfactuals(
            factual_state, possible_interventions, causal_graph
        )
        key = lambda r: r.causal_effect
        return max(results, key=key) if objective == "maximize" else min(results, key=key)

    def _propagate_intervention(self, state: Dict[str, float],
                                 intervention: Dict[str, float],
                                 causal_graph: Dict[str, List[str]]) -> Dict[str, float]:
        """Propagate intervention effects through the causal graph."""
        updated = dict(state)
        for target, sources in causal_graph.items():
            if target not in intervention:
                source_vals = [updated.get(s, 0.0) for s in sources]
                noise = np.random.randn() * self.config.intervention_noise
                updated[target] = sum(source_vals) / max(len(source_vals), 1) + noise
        return updated

    def _evaluate_state(self, state: Dict[str, float]) -> float:
        """Evaluate a state to produce a scalar outcome."""
        return float(sum(state.values()) / max(len(state), 1))

    def _estimate_confidence(self, factual: Dict[str, float],
                              intervention: Dict[str, float]) -> float:
        """Estimate confidence in the counterfactual result."""
        overlap = len(set(factual.keys()) & set(intervention.keys()))
        total = len(set(factual.keys()) | set(intervention.keys()))
        return float(overlap / max(total, 1))

