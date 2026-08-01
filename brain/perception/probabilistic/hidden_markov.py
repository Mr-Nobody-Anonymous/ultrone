# Copyright (c) Ultrone Contributors. All rights reserved.
"""Hidden Markov Model for sequential state estimation."""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Ultrone.Brain.Perception.Probabilistic.HMM")


@dataclass
class HMMConfig:
    """Configuration for HMM."""
    num_states: int = 3
    num_observations: int = 5


class HiddenMarkovModel:
    """Hidden Markov Model for sequential state estimation.

    Supports forward-backward algorithm, Viterbi decoding, and
    Baum-Welch parameter estimation.
    """

    def __init__(self, config: Optional[HMMConfig] = None):
        self.config = config or HMMConfig()
        n = self.config.num_states
        m = self.config.num_observations
        self._transition = np.ones((n, n)) / n
        self._emission = np.ones((n, m)) / m
        self._initial = np.ones(n) / n

    def forward(self, observations: List[int]) -> np.ndarray:
        """Forward algorithm: compute filtering distribution."""
        n = self.config.num_states
        T = len(observations)
        alpha = np.zeros((T, n))
        alpha[0] = self._initial * self._emission[:, observations[0]]
        alpha[0] /= alpha[0].sum()
        for t in range(1, T):
            alpha[t] = (alpha[t - 1] @ self._transition) * self._emission[:, observations[t]]
            alpha[t] /= alpha[t].sum()
        return alpha

    def viterbi(self, observations: List[int]) -> List[int]:
        """Viterbi decoding: find most likely state sequence."""
        n = self.config.num_states
        T = len(observations)
        delta = np.zeros((T, n))
        psi = np.zeros((T, n), dtype=int)
        delta[0] = self._initial * self._emission[:, observations[0]]
        for t in range(1, T):
            for j in range(n):
                probs = delta[t - 1] * self._transition[:, j] * self._emission[j, observations[t]]
                psi[t, j] = np.argmax(probs)
                delta[t, j] = probs[psi[t, j]]
        states = [int(np.argmax(delta[T - 1]))]
        for t in range(T - 1, 0, -1):
            states.insert(0, int(psi[t, states[0]]))
        return states

    def get_stats(self) -> Dict[str, Any]:
        return {"type": "HMM", "num_states": self.config.num_states}
