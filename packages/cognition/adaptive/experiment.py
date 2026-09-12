# Copyright (c) Ultrone Contributors. All rights reserved.
"""Experiments: reproducible configuration trials over the registry.

An Experiment binds a registry snapshot, an overrides candidate, and its
evaluation outcome into one comparable, serializable unit.
``ExperimentRunner.grid`` sweeps values of a single numeric parameter
and ranks the trials -- the simplest honest way to answer "does this
parameter matter?" before letting the optimizer loose.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from adaptive.evaluator import EvalTask
from adaptive.parameter_registry import ParameterRegistry


@dataclass
class Trial:
    overrides: Dict[str, Any]
    score: float
    config_hash: str


@dataclass
class Experiment:
    experiment_id: str
    parameter: str
    baseline_score: float
    trials: List[Trial] = field(default_factory=list)

    def ranked(self) -> List[Trial]:
        return sorted(self.trials, key=lambda t: (-t.score,
                                                  t.config_hash))

    def best(self) -> Trial:
        return self.ranked()[0]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "parameter": self.parameter,
            "baseline_score": self.baseline_score,
            "best": {"overrides": self.best().overrides,
                     "score": self.best().score},
            "trials": [{"overrides": t.overrides, "score": t.score,
                        "config_hash": t.config_hash}
                       for t in self.trials],
        }


class ExperimentRunner:
    """Deterministic grid trials over one numeric parameter."""

    def __init__(self, registry: ParameterRegistry, task: EvalTask) -> None:
        self.registry = registry
        self.task = task

    def grid(self, experiment_id: str, parameter: str,
             values: List[Any]) -> Experiment:
        spec = self.registry.spec(parameter)
        if spec.type not in ("float", "int"):
            raise ValueError("grid sweeps need a numeric parameter")
        if not values:
            raise ValueError("values list is empty")
        from adaptive.optimizer import config_hash

        baseline_config = self.registry.snapshot()
        experiment = Experiment(
            experiment_id=experiment_id,
            parameter=parameter,
            baseline_score=round(self.task(baseline_config), 6))

        original = self.registry.get(parameter)
        try:
            for value in sorted(values):
                self.registry.set(parameter, value)
                config = self.registry.snapshot()
                experiment.trials.append(Trial(
                    overrides={parameter: value},
                    score=round(self.task(config), 6),
                    config_hash=config_hash(config)))
        finally:
            self.registry.set(parameter, original)      # restore exactly
        return experiment