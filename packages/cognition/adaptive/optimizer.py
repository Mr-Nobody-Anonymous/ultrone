# Copyright (c) Ultrone Contributors. All rights reserved.
"""AdaptiveOptimizer: evolutionary search over registry configurations.

Generate candidates -> evaluate -> compare -> keep winners -> repeat.
The optimizer NEVER touches production state: it works on candidate
configurations only, and every run is reproducible from its seed.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from adaptive.evaluator import Evaluator
from adaptive.parameter_registry import ParameterRegistry


@dataclass
class Candidate:
    config: Dict[str, Any]
    score: float
    generation: int = 0
    parent_hash: str = ""
    origin: str = "seed"                # seed | mutate | crossover

    def to_dict(self) -> Dict[str, Any]:
        return {"config": self.config, "score": self.score,
                "generation": self.generation,
                "parent_hash": self.parent_hash,
                "origin": self.origin}


@dataclass
class OptimizationResult:
    best: "Candidate"
    baseline_score: float
    generations_run: int
    population_size: int
    history_best: List[float] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"best": self.best.to_dict(),
                "baseline_score": self.baseline_score,
                "generations_run": self.generations_run,
                "population_size": self.population_size,
                "history_best": list(self.history_best)}


def default_patrol_registry() -> ParameterRegistry:
    """Registry for the built-in ground-patrol tuning task."""
    registry = ParameterRegistry()
    registry.declare("patrol.speed", "float", 1.2, bounds=(0.5, 2.4),
                     metric="ground_patrol_score",
                     description="cruise speed during waypoint patrols")
    registry.declare("patrol.wear_sensitivity", "float", 1.0,
                     bounds=(0.0, 3.0), metric="ground_patrol_score",
                     description="wear penalty multiplier")
    registry.declare("patrol.waypoint_budget", "int", 240,
                     bounds=(60, 400), metric="ground_patrol_score",
                     description="max ticks per waypoint leg")
    return registry


class AdaptiveOptimizer:
    """Deterministic evolutionary search over a ParameterRegistry."""

    def __init__(self, registry: ParameterRegistry, evaluator: Evaluator,
                 tunable: Optional[List[str]] = None,
                 population_size: int = 12,
                 mutation_sigma: float = 0.25,
                 elite_fraction: float = 0.25,
                 seed: int = 0) -> None:
        self.registry = registry
        self.evaluator = evaluator
        self.tunable = sorted(tunable or registry.names())
        if not self.tunable:
            raise ValueError("no tunable parameters given")
        self.population_size = max(4, int(population_size))
        self.mutation_sigma = float(mutation_sigma)
        self.elite_count = max(1, int(self.population_size * elite_fraction))
        self.rng = random.Random(seed)
        self._numeric_specs = {
            name: registry.spec(name) for name in self.tunable
            if registry.spec(name).type in ("float", "int")
        }

    # -- search ------------------------------------------------------------- #
    def run(self, generations: int = 6) -> "OptimizationResult":
        baseline_config = self.registry.snapshot()
        baseline_score = self.evaluator.task(baseline_config)

        population = self._seed_population()
        history_best: List[float] = []
        best_overall = min(population,
                           key=lambda c: (-c.score, config_hash(c.config)))

        for generation in range(1, generations + 1):
            population.sort(key=lambda c: (-c.score,
                                           config_hash(c.config)))
            elites = population[:self.elite_count]
            best_overall = self._better(best_overall, elites[0])
            history_best.append(elites[0].score)

            next_population: List[Candidate] = list(elites)
            while len(next_population) < self.population_size:
                if self.rng.random() < 0.7:
                    p1, p2 = self._tournament(population)
                    next_population.append(
                        self._crossover(p1, p2, generation))
                parent = self._tournament(population)[0]
                next_population.append(self._mutate(parent, generation))
            population = next_population

        return OptimizationResult(
            best=self._better(best_overall, population[0]),
            baseline_score=baseline_score,
            generations_run=generations,
            population_size=self.population_size,
            history_best=history_best)

    # -- population mechanics ------------------------------------------------- #
    def _seed_population(self) -> List[Candidate]:
        seeds = [Candidate(self.registry.snapshot(),
                           self.evaluator.task(self.registry.snapshot()),
                           generation=0)]
        while len(seeds) < self.population_size:
            overrides = {name: self._random_value(self.registry.spec(name))
                         for name in self.tunable}
            config = {**self.registry.snapshot(), **overrides}
            seeds.append(Candidate(config, self.evaluator.task(config)))
        return seeds

    def _random_value(self, spec) -> Any:
        if spec.type == "bool":
            return self.rng.random() < 0.5
        if spec.type == "str":
            return self.rng.choice(spec.choices) \
                if spec.choices else spec.default
        lo, hi = spec.bounds or (spec.default, spec.default)
        value = self.rng.uniform(lo, hi)
        return round(value) if spec.type == "int" else round(value, 4)

    def _perturb(self, name: str, value: Any) -> Any:
        spec = self._numeric_specs.get(name)
        if spec is None:
            return value                       # bool/str unchanged here
        lo, hi = spec.bounds
        mutated = float(value) + self.rng.gauss(
            0.0, self.mutation_sigma * (hi - lo))
        mutated = min(hi, max(lo, mutated))
        return round(mutated) if spec.type == "int" else round(mutated, 4)

    def _mutate(self, parent: Candidate, generation: int) -> Candidate:
        config = dict(parent.config)
        targets = [n for n in self.tunable if n in self._numeric_specs]
        name = self.rng.choice(targets or self.tunable)
        config[name] = self._perturb(
            name, config.get(name, self.registry.spec(name).default))
        score = self.evaluator.task(config)
        return Candidate(config, score, generation=generation,
                         parent_hash=config_hash(parent.config),
                         origin="mutate")

    def _crossover(self, a: Candidate, b: Candidate,
                   generation: int) -> Candidate:
        config = dict(a.config)
        for name in self.tunable:
            if self.rng.random() < 0.5 and name in b.config:
                config[name] = b.config[name]
        return Candidate(config, self.evaluator.task(config),
                         generation=generation,
                         parent_hash=config_hash(a.config),
                         origin="crossover")

    def _tournament(self, population: List[Candidate]):
        entrants = self.rng.sample(population,
                                   min(3, len(population)))
        entrants.sort(key=lambda c: -c.score)
        return entrants[0], entrants[min(1, len(entrants) - 1)]

    @staticmethod
    def _better(current: Candidate, challenger: Candidate) -> Candidate:
        if challenger.score > current.score:
            return challenger
        if challenger.score == current.score \
                and config_hash(challenger.config) \
                < config_hash(current.config):
            return challenger
        return current


def config_hash(config: Dict[str, Any]) -> str:
    import hashlib
    import json as _json

    payload = _json.dumps(config, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]