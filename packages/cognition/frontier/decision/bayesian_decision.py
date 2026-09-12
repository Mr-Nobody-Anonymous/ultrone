# Copyright (c) Ultrone Contributors. All rights reserved.
"""Bayesian Decision Layer — decision-making under uncertainty.

Implements a Bayesian decision layer that combines priors, likelihood
evidence, uncertainty estimates, and a utility function to choose the action
maximizing expected utility. Supports:

- belief updating (prior → posterior via Bayes' rule),
- expected utility maximization over candidate actions,
- abstention / rejection when uncertainty is too high,
- sequential decision trace logging for the self-improvement loop.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("Ultrone.Frontier.Decision.Bayesian")


@dataclass
class Belief:
    """A categorical belief distribution over hypotheses."""

    probabilities: Dict[str, float] = field(default_factory=dict)

    def normalize(self) -> None:
        total = sum(self.probabilities.values())
        if total <= 0:
            return
        for key in self.probabilities:
            self.probabilities[key] /= total

    def posterior(self, likelihood: Dict[str, float]) -> "Belief":
        """Update beliefs given a likelihood function over hypotheses."""
        updated = {}
        for hypothesis, prior in self.probabilities.items():
            updated[hypothesis] = prior * likelihood.get(hypothesis, 0.0)
        new_belief = Belief(probabilities=updated)
        new_belief.normalize()
        return new_belief

    def confidence(self) -> float:
        """Return the probability of the most likely hypothesis."""
        return max(self.probabilities.values()) if self.probabilities else 0.0

    def mode(self) -> Optional[str]:
        """Return the most likely hypothesis."""
        if not self.probabilities:
            return None
        return max(self.probabilities, key=self.probabilities.get)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "probabilities": self.probabilities,
            "mode": self.mode(),
            "confidence": self.confidence(),
        }


@dataclass
class Decision:
    """The result of a Bayesian decision."""

    action: Optional[str]
    expected_utility: float
    confidence: float
    abstained: bool
    reason: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "expected_utility": self.expected_utility,
            "confidence": self.confidence,
            "abstained": self.abstained,
            "reason": self.reason,
            "details": self.details,
        }


class BayesianDecisionLayer:
    """Selects actions by maximizing expected utility under uncertainty.

    Parameters
    ----------
    utility_fn : Optional[Callable]
        A callable ``(action, state) -> float`` computing the utility of an
        action given a belief state. Defaults to a simple posterior-weighted
        utility.
    abstain_threshold : float
        If the best confidence is below this threshold, the layer abstains.
    prior : Optional[Dict[str, float]]
        Initial prior over hypotheses.
    """

    def __init__(
        self,
        utility_fn: Optional[Callable[..., float]] = None,
        abstain_threshold: float = 0.5,
        prior: Optional[Dict[str, float]] = None,
    ) -> None:
        self.utility_fn = utility_fn
        self.abstain_threshold = abstain_threshold
        self.prior = Belief(probabilities=dict(prior) if prior else {"default": 1.0})
        self.prior.normalize()
        self._beliefs: List[Belief] = []
        self._decisions: List[Decision] = []

    def update_belief(self, likelihood: Dict[str, float]) -> Belief:
        """Update the current prior given a likelihood function."""
        self.prior = self.prior.posterior(likelihood)
        self._beliefs.append(self.prior)
        return self.prior

    def decide(
        self,
        actions: List[str],
        likelihood: Optional[Dict[str, float]] = None,
        state: Optional[Dict[str, Any]] = None,
    ) -> Decision:
        """Choose the best action by expected utility.

        Parameters
        ----------
        actions
            Candidate actions to choose from.
        likelihood
            Optional likelihood evidence to update the belief first.
        state
            Optional state passed to the utility function.

        Returns
        -------
        Decision
            The chosen action (or abstention).
        """
        if likelihood:
            self.update_belief(likelihood)

        state = state or {}
        best_action = None
        best_utility = -math.inf
        for action in actions:
            utility = self._utility(action, state)
            if utility > best_utility:
                best_utility = utility
                best_action = action

        confidence = self.prior.confidence()

        if best_action is None or confidence < self.abstain_threshold:
            decision = Decision(
                action=None,
                expected_utility=best_utility,
                confidence=confidence,
                abstained=True,
                reason=f"Confidence {confidence:.2f} below abstain threshold {self.abstain_threshold:.2f}",
            )
        else:
            decision = Decision(
                action=best_action,
                expected_utility=best_utility,
                confidence=confidence,
                abstained=False,
                reason=f"Selected action maximizing expected utility",
            )

        decision.details["belief"] = self.prior.to_dict()
        self._decisions.append(decision)
        return decision

    def _utility(self, action: str, state: Dict[str, Any]) -> float:
        """Compute expected utility of an action given the belief."""
        if self.utility_fn is not None:
            return float(self.utility_fn(action, self.prior, state))
        # Default: posterior-weighted utility keyed by hypothesis == action.
        return self.prior.probabilities.get(action, 0.0)

    def get_beliefs(self) -> List[Belief]:
        """Return the belief history."""
        return list(self._beliefs)

    def get_decisions(self) -> List[Decision]:
        """Return the decision history."""
        return list(self._decisions)

    def get_stats(self) -> Dict[str, Any]:
        """Return aggregate statistics."""
        if not self._decisions:
            return {"decisions": 0, "abstention_rate": 0.0}
        abstained = sum(1 for d in self._decisions if d.abstained)
        return {
            "decisions": len(self._decisions),
            "abstention_rate": abstained / len(self._decisions),
        }
