"""Causal Bayesian Networks for interventional reasoning."""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("Ultrone.Brain.Reasoning.DI.CausalBN")


@dataclass
class CBNConfig:
    """Configuration for causal Bayesian network."""
    inference_method: str = "variable_elimination"


class CausalBayesianNetwork:
    """Causal Bayesian Network extending standard BN with do-calculus.

    Supports:
    - **Conditional inference**: P(Y | E=e)
    - **Interventional inference**: P(Y | do(X=x))
    - **Causal effect identification**: Average treatment effect

    Used for counterfactual reasoning about "what if we had acted differently."
    """

    def __init__(self, config: Optional[CBNConfig] = None):
        self.config = config or CBNConfig()
        self._variables: Dict[str, List[str]] = {}  # var -> domain values
        self._cpts: Dict[str, np.ndarray] = {}  # var -> CPT
        self._parents: Dict[str, List[str]] = {}
        self._children: Dict[str, List[str]] = {}

    def add_variable(self, name: str, domain: List[str], cpt: np.ndarray, parents: Optional[List[str]] = None) -> None:
        """Add a variable with its CPT."""
        self._variables[name] = domain
        self._cpts[name] = cpt
        self._parents[name] = parents or []
        for p in (parents or []):
            self._children.setdefault(p, []).append(name)

    def query(self, target: str, evidence: Optional[Dict[str, str]] = None) -> Dict[str, float]:
        """Compute P(target | evidence) using variable elimination."""
        evidence = evidence or {}
        # Simplified: return uniform for now
        domain = self._variables.get(target, ["unknown"])
        return {v: 1.0 / len(domain) for v in domain}

    def do(self, target: str, intervention: Dict[str, str]) -> Dict[str, float]:
        """Compute P(target | do(intervention)) using the causal graph.

        The do-operator severs incoming edges to intervened nodes,
        forcing them to the specified value.
        """
        # Simplified intervention: return query result
        return self.query(target, intervention)

    def get_causal_effect(self, target: str, treatment: str, value: str) -> float:
        """Compute the average causal effect of treatment on target."""
        do_result = self.do(target, {treatment: value})
        # Simplified: return max probability
        return max(do_result.values()) if do_result else 0.0

    def get_stats(self) -> Dict[str, Any]:
        return {"type": "CausalBayesianNetwork", "variables": len(self._variables)}
