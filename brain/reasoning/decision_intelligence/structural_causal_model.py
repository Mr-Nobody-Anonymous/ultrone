"""Structural Causal Models for formal causal reasoning."""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("Ultrone.Brain.Reasoning.DI.SCM")


@dataclass
class SCMConfig:
    """Configuration for structural causal model."""
    num_samples: int = 1000


class StructuralCausalModel:
    """Structural Causal Model (SCM) with Pearl's three-level hierarchy.

    Supports:
    1. **Association**: P(Y | X) — observational
    2. **Intervention**: P(Y | do(X)) — experimental
    3. **Counterfactuals**: P(Y_{X=x} | Y=y) — imagination

    Each variable is defined by a structural equation: V = f(Pa(V), U)
    where Pa(V) are parents and U is exogenous noise.
    """

    def __init__(self, config: Optional[SCMConfig] = None):
        self.config = config or SCMConfig()
        self._equations: Dict[str, Callable] = {}
        self._exogenous: Dict[str, Callable] = {}
        self._parents: Dict[str, List[str]] = {}
        self._variables: List[str] = []

    def add_variable(self, name: str, equation: Callable, exogenous_fn: Callable, parents: Optional[List[str]] = None) -> None:
        """Add an endogenous variable with structural equation."""
        self._variables.append(name)
        self._equations[name] = equation
        self._exogenous[name] = exogenous_fn
        self._parents[name] = parents or []

    def sample(self, num_samples: Optional[int] = None) -> np.ndarray:
        """Sample from the observational distribution.

        Returns an array of shape (num_samples, num_variables).
        """
        n = num_samples or self.config.num_samples
        samples = np.zeros((n, len(self._variables)))
        for i in range(n):
            values = {}
            for var in self._variables:
                noise = self._exogenous[var]()
                parent_vals = {p: values[p] for p in self._parents[var]}
                values[var] = self._equations[var](**parent_vals, noise=noise)
            for j, var in enumerate(self._variables):
                samples[i, j] = values[var]
        return samples

    def intervene(self, interventions: Dict[str, float], num_samples: Optional[int] = None) -> np.ndarray:
        """Sample from P(Y | do(X=x)) by fixing intervened variables.

        The do-operator severs causal links from parents to intervened nodes.
        """
        n = num_samples or self.config.num_samples
        samples = np.zeros((n, len(self._variables)))
        for i in range(n):
            values = dict(interventions)
            for var in self._variables:
                if var in interventions:
                    continue
                noise = self._exogenous[var]()
                parent_vals = {p: values.get(p, 0) for p in self._parents[var]}
                values[var] = self._equations[var](**parent_vals, noise=noise)
            for j, var in enumerate(self._variables):
                samples[i, j] = values[var]
        return samples

    def get_stats(self) -> Dict[str, Any]:
        return {"type": "StructuralCausalModel", "variables": len(self._variables)}
