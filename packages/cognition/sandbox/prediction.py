# Copyright (c) Ultrone Contributors. All rights reserved.
"""General-world prediction benchmark (Sprint D flagship).

Protocol:

1. Give the agent incomplete, noisy observations of a hidden world state.
2. The agent maintains an explicit probability distribution over states.
3. New information arrives each tick; measure **calibration** (does 80%
   confidence mean 80% accuracy?) and **accuracy** (Brier / log loss).
4. Introduce unexpected events (regime switches); measure **recovery**
   (ticks until the agent's beliefs re-converge).
5. Present a regime the agent was never told exists; measure whether it
   degrades gracefully instead of collapsing.

Any agent exposing ``predict() -> {state: prob}`` and ``observe(symbol)``
competes on equal footing -- this measures generality of belief
maintenance, not one specialized algorithm.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

EPS = 1e-9


class HypothesisWorld:
    """Hidden-regime world emitting regime-conditioned symbols."""

    def __init__(
        self,
        emissions: Dict[str, Dict[str, float]],
        seed: int = 0,
        start: Optional[str] = None,
    ) -> None:
        self.emissions = emissions
        keys = sorted(emissions)
        self.state = start if start is not None else keys[0]
        self.rng = random.Random(seed)

    def observe(self, dropout_probability: float = 0.0) -> Optional[str]:
        """Sample one symbol from the hidden regime (or drop the packet)."""
        if self.rng.random() < dropout_probability:
            return None  # observation lost: the agent must hold its belief
        dist = self.emissions[self.state]
        roll = self.rng.random()
        acc = 0.0
        for sym in sorted(dist):
            acc += dist[sym]
            if roll <= acc:
                return sym
        return sorted(dist)[-1]

    def switch(self, state: str) -> None:
        self.state = state


class BeliefAgent:
    """Minimal contract every competitor implements."""

    def __init__(self, hypotheses: List[str]) -> None:
        self.hypotheses = tuple(hypotheses)
        u = 1.0 / len(hypotheses)
        self._dist: Dict[str, float] = {h: u for h in hypotheses}

    def predict(self) -> Dict[str, float]:
        return dict(self._dist)

    def observe(self, symbol: Optional[str]) -> None:  # pragma: no cover
        raise NotImplementedError


class UniformAgent(BeliefAgent):
    """Know-nothing baseline: never updates, always uniform."""

    def observe(self, symbol: Optional[str]) -> None:
        pass


class BayesianBeliefAgent(BeliefAgent):
    """Posterior maintenance with a noise floor.

    The floor keeps hypotheses alive under unmodeled evidence -- the
    mechanism behind graceful degradation on novel regimes.
    """

    def __init__(
        self,
        hypotheses: List[str],
        emissions: Dict[str, Dict[str, float]],
        noise_floor: float = 0.02,
    ) -> None:
        super().__init__(hypotheses)
        self.noise_floor = noise_floor
        self._lik: Dict[str, Dict[str, float]] = {
            h: {s: max(float(p), noise_floor)
                for s, p in emissions.get(h, {}).items()}
            for h in hypotheses
        }
        self._seen_symbols = sorted({s for row in self._lik.values() for s in row})

    def observe(self, symbol: Optional[str]) -> None:
        if symbol is None:
            return  # dropout: beliefs persist unchanged
        raw: Dict[str, float] = {}
        for h in self.hypotheses:
            lik = self._lik[h].get(symbol)
            if lik is None:
                lik = max(self.noise_floor, 0.05)
            raw[h] = self._dist[h] * lik
        z = sum(raw.values()) or EPS
        floored = {h: max(v / z, 1e-6) for h, v in raw.items()}
        z2 = sum(floored.values()) or EPS
        self._dist = {h: v / z2 for h, v in floored.items()}


def make_bayesian(
    emissions: Dict[str, Dict[str, float]], exclude: Optional[str] = None,
) -> Callable[[], BeliefAgent]:
    """Factory producing a Bayesian agent over the given regimes."""
    def factory():
        hyps = [h for h in sorted(emissions) if h != exclude]
        return BayesianBeliefAgent(hyps, emissions)
    return factory


# --------------------------------------------------------------------- #
# Metrics                                                                #
# --------------------------------------------------------------------- #
@dataclass(frozen=True)
class PredictionRecord:
    tick: int
    true_state: str
    observed: Optional[str]
    top_hypothesis: str
    confidence: float
    correct: bool
    brier: float


def _argmax(dist: Dict[str, float]) -> Tuple[str, float]:
    label = sorted(dist.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
    return label, dist[label]


def brier_multiclass(dist: Dict[str, float], truth: str) -> float:
    return sum((p - (1.0 if k == truth else 0.0)) ** 2 for k, p in dist.items())


def expected_calibration_error(
    records: List["PredictionRecord"], n_bins: int = 10,
) -> float:
    """|mean confidence - accuracy| weighted across confidence bins."""
    if not records:
        return 0.0
    buckets: List[List[Tuple[float, float]]] = [[] for _ in range(n_bins)]
    for r in records:
        idx = min(n_bins - 1, int(r.confidence * n_bins))
        buckets[idx].append((r.confidence, 1.0 if r.correct else 0.0))
    ece = 0.0
    total = len(records)
    for b in buckets:
        if not b:
            continue
        conf = sum(x for x, _ in b) / len(b)
        acc = sum(y for _, y in b) / len(b)
        ece += (len(b) / total) * abs(conf - acc)
    return ece


def recovery_ticks(
    records: List["PredictionRecord"],
    switch_tick: int,
    confidence_threshold: float = 0.5,
) -> Optional[int]:
    """Ticks after a switch until top-belief is right AND confident again."""
    for r in records:
        if r.tick <= switch_tick:
            continue
        if r.correct and r.confidence >= confidence_threshold:
            return r.tick - switch_tick
    return None


def steady_records(
    records: List["PredictionRecord"],
    switch_ticks: Tuple[int, ...] = (),
    settle_ticks: int = 6,
) -> List["PredictionRecord"]:
    """Records outside every [switch, switch+settle] window.

    Calibration and accuracy are measured here: immediately after an
    unexpected event even a good agent *should* be miscalibrated for a few
    ticks -- that transient is what ``recovery_ticks`` scores separately.
    """
    windows = [(s, s + settle_ticks) for s in switch_ticks]
    return [
        r for r in records
        if not any(lo < r.tick <= hi for lo, hi in windows)
    ]


# --------------------------------------------------------------------- #
# Benchmark driver                                                       #
# --------------------------------------------------------------------- #
class PredictionBenchmark:
    """Runs one agent through the full protocol; fully deterministic."""

    def __init__(
        self,
        agent_factory: Callable[[], BeliefAgent],
        emissions: Dict[str, Dict[str, float]],
        seed: int = 0,
        n_ticks: int = 60,
        dropout_probability: float = 0.15,
        switches: Tuple[Tuple[int, str], ...] = (),
    ) -> None:
        self.agent_factory = agent_factory
        self.emissions = emissions
        self.seed = seed
        self.n_ticks = n_ticks
        self.dropout = dropout_probability
        self.switches = switches

    def run(self) -> List[PredictionRecord]:
        world = HypothesisWorld(self.emissions, seed=self.seed)
        agent = self.agent_factory()
        schedule = dict(self.switches)
        records: List[PredictionRecord] = []
        for tick in range(1, self.n_ticks + 1):
            if tick in schedule:
                world.switch(schedule[tick])
            dist = agent.predict()
            top, conf = _argmax(dist)
            truth = world.state
            observed = world.observe(self.dropout)
            agent.observe(observed)
            records.append(PredictionRecord(
                tick=tick,
                true_state=truth,
                observed=observed,
                top_hypothesis=top,
                confidence=round(conf, 6),
                correct=(top == truth),
                brier=round(brier_multiclass(dist, truth), 6),
            ))
        return records


def summarize(
    records: List[PredictionRecord], switch_ticks: Tuple[int, ...] = (),
) -> Dict[str, object]:
    """Aggregate metrics for one episode (deterministic)."""
    n = len(records) or 1
    out: Dict[str, object] = {
        "ticks": len(records),
        "brier_mean": round(sum(r.brier for r in records) / n, 6),
        "accuracy": round(sum(1 for r in records if r.correct) / n, 6),
        "ece": round(expected_calibration_error(records), 6),
    }
    for st in switch_ticks:
        out[f"recovery_after_{st}"] = recovery_ticks(records, st)
    return out

