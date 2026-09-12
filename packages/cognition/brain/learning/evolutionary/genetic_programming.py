"""
Genetic Programming
====================
Evolves program trees to represent tactical decision logic.

Unlike NEAT which evolves neural networks, GP evolves symbolic
expression trees - making the evolved strategies interpretable
by human commanders.

Each tree is a composition of:
- Terminals: Sensors, constants, action primitives
- Functions: Logical/arithmetic operators, tactical combinators
"""

from __future__ import annotations

import math
import random
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Callable

logger = logging.getLogger("Ultrone.Brain.Learning.Evolutionary.GeneticProgramming")


@dataclass
class GPTreeNode:
    """A single node in a GP tree."""
    value: Any
    arity: int = 0
    children: List["GPTreeNode"] = field(default_factory=list)

    def depth(self) -> int:
        if not self.children:
            return 1
        return 1 + max(c.depth() for c in self.children)

    def size(self) -> int:
        return 1 + sum(c.size() for c in self.children)

    def clone(self) -> "GPTreeNode":
        return GPTreeNode(
            value=self.value,
            arity=self.arity,
            children=[c.clone() for c in self.children],
        )

    def evaluate(self, context: Dict[str, float]) -> float:
        if self.arity == 0:
            if isinstance(self.value, (int, float)):
                return float(self.value)
            return float(context.get(self.value, 0.0))
        args = [c.evaluate(context) for c in self.children]
        fn = self.value
        if fn == "add":
            return args[0] + args[1]
        if fn == "sub":
            return args[0] - args[1]
        if fn == "mul":
            return args[0] * args[1]
        if fn == "div":
            return args[0] / args[1] if abs(args[1]) > 1e-9 else 1.0
        if fn == "min":
            return min(args)
        if fn == "max":
            return max(args)
        if fn == "if_gt":
            return args[1] if args[0] > args[2] else args[3]
        if fn == "if_lt":
            return args[1] if args[0] < args[2] else args[3]
        if fn == "neg":
            return -args[0]
        if fn == "abs":
            return abs(args[0])
        if fn == "clamp":
            return max(0.0, min(1.0, args[0]))
        return 0.0

    def to_string(self) -> str:
        if self.arity == 0:
            return str(self.value)
        return f"{self.value}({', '.join(c.to_string() for c in self.children)})"


@dataclass
class GPTree:
    """A GP program tree with fitness tracking."""
    root: GPTreeNode
    genome_id: str
    fitness: float = 0.0
    depth: int = 0
    size: int = 0
    generation: int = 0

    def __post_init__(self):
        self.depth = self.root.depth()
        self.size = self.root.size()

    def evaluate(self, context: Dict[str, float]) -> float:
        return self.root.evaluate(context)

    def clone(self) -> "GPTree":
        return GPTree(
            root=self.root.clone(),
            genome_id=self.genome_id,
            fitness=self.fitness,
            depth=self.depth,
            size=self.size,
            generation=self.generation,
        )

    def to_string(self) -> str:
        return self.root.to_string()


@dataclass
class GPConfig:
    """Configuration for Genetic Programming."""
    population_size: int = 100
    generations: int = 50
    max_depth: int = 6
    min_depth: int = 2
    crossover_prob: float = 0.7
    mutation_prob: float = 0.2
    reproduction_prob: float = 0.1
    tournament_size: int = 3
    elitism: int = 2
    max_init_depth: int = 4
    function_set: List[str] = field(default_factory=lambda: [
        "add", "sub", "mul", "div", "min", "max", "if_gt", "if_lt", "clamp",
    ])
    terminal_names: List[str] = field(default_factory=lambda: [
        "threat_level", "health", "ammo", "distance", "cover", "speed",
        "reinforcements", "intel_quality",
    ])
    constant_min: float = 0.0
    constant_max: float = 1.0


class GeneticProgramming:
    """Genetic Programming for evolving interpretable tactical logic."""

    FUNCTION_ARITY = {
        "add": 2, "sub": 2, "mul": 2, "div": 2,
        "min": 2, "max": 2, "if_gt": 3, "if_lt": 3,
        "neg": 1, "abs": 1, "clamp": 1,
    }

    def __init__(self, config: Optional[GPConfig] = None):
        self.config = config or GPConfig()
        self.population: List[GPTree] = []
        self.generation = 0
        self.best_tree: Optional[GPTree] = None
        self.best_fitness: float = -float('inf')
        self._fitness_history: List[float] = []
        self._genome_counter = 0

    def _next_id(self) -> str:
        self._genome_counter += 1
        return f"GP-{self._genome_counter}"

    def _random_terminal(self) -> GPTreeNode:
        if random.random() < 0.5:
            return GPTreeNode(value=random.choice(self.config.terminal_names), arity=0)
        return GPTreeNode(
            value=random.uniform(self.config.constant_min, self.config.constant_max),
            arity=0,
        )

    def _random_function(self) -> str:
        return random.choice(self.config.function_set)

    def _grow_tree(self, max_depth: int, current_depth: int = 0) -> GPTreeNode:
        if current_depth >= max_depth:
            return self._random_terminal()
        if random.random() < 0.4 and current_depth > 0:
            return self._random_terminal()
        fn = self._random_function()
        arity = self.FUNCTION_ARITY.get(fn, 2)
        children = [self._grow_tree(max_depth, current_depth + 1) for _ in range(arity)]
        return GPTreeNode(value=fn, arity=arity, children=children)

    def _full_tree(self, depth: int, current_depth: int = 0) -> GPTreeNode:
        if current_depth >= depth:
            return self._random_terminal()
        fn = self._random_function()
        arity = self.FUNCTION_ARITY.get(fn, 2)
        children = [self._full_tree(depth, current_depth + 1) for _ in range(arity)]
        return GPTreeNode(value=fn, arity=arity, children=children)

    def _ramped_half_half(self) -> GPTreeNode:
        depth = random.randint(self.config.min_depth, self.config.max_init_depth)
        if random.random() < 0.5:
            return self._grow_tree(depth)
        return self._full_tree(depth)

    def initialize_population(self) -> None:
        self.population = []
        for _ in range(self.config.population_size):
            tree = GPTree(root=self._ramped_half_half(), genome_id=self._next_id())
            self.population.append(tree)

    def evaluate_population(self, fitness_fn: Callable[[GPTree], float]) -> None:
        for tree in self.population:
            tree.fitness = fitness_fn(tree)
            if tree.fitness > self.best_fitness:
                self.best_fitness = tree.fitness
                self.best_tree = tree.clone()

    def _select_parent(self) -> GPTree:
        tournament = random.sample(
            self.population,
            min(self.config.tournament_size, len(self.population)),
        )
        return max(tournament, key=lambda t: t.fitness)

    def _crossover(self, p1: GPTree, p2: GPTree) -> GPTree:
        def get_random_subtree(node: GPTreeNode) -> Tuple[GPTreeNode, Optional[GPTreeNode]]:
            if not node.children or random.random() < 0.3:
                return node, None
            child_idx = random.randrange(len(node.children))
            return get_random_subtree(node.children[child_idx])

        child_root = p1.root.clone()
        subtree1, parent1 = get_random_subtree(child_root)
        subtree2, _ = get_random_subtree(p2.root)

        if parent1 is None:
            child_root = subtree2.clone()
        else:
            for i, c in enumerate(parent1.children):
                if c is subtree1:
                    parent1.children[i] = subtree2.clone()
        return GPTree(root=child_root, genome_id=self._next_id())

    def _mutate(self, tree: GPTree) -> GPTree:
        def mutate_node(node: GPTreeNode, depth: int) -> GPTreeNode:
            if not node.children or random.random() < 0.2:
                return self._grow_tree(max(1, self.config.max_depth - depth))
            idx = random.randrange(len(node.children))
            node.children[idx] = mutate_node(node.children[idx], depth + 1)
            return node
        new_root = mutate_node(tree.root.clone(), 0)
        return GPTree(root=new_root, genome_id=self._next_id())

    def evolve_generation(self, fitness_fn: Callable[[GPTree], float]) -> None:
        self.evaluate_population(fitness_fn)
        self.population.sort(key=lambda t: t.fitness, reverse=True)
        avg_fitness = sum(t.fitness for t in self.population) / len(self.population)
        self._fitness_history.append(avg_fitness)
        next_population = [t.clone() for t in self.population[:self.config.elitism]]
        while len(next_population) < self.config.population_size:
            r = random.random()
            if r < self.config.crossover_prob:
                p1 = self._select_parent()
                p2 = self._select_parent()
                child = self._crossover(p1, p2)
            elif r < self.config.crossover_prob + self.config.mutation_prob:
                parent = self._select_parent()
                child = self._mutate(parent)
            else:
                parent = self._select_parent()
                child = parent.clone()
            while child.root.depth() > self.config.max_depth:
                child = self._mutate(child)
            next_population.append(child)
        self.population = next_population
        self.generation += 1

    def train(self, fitness_fn: Callable[[GPTree], float], n_generations: int = 50) -> GPTree:
        if not self.population:
            self.initialize_population()
        for _ in range(n_generations):
            self.evolve_generation(fitness_fn)
        return self.best_tree if self.best_tree else self.population[0]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "generation": self.generation,
            "population_size": len(self.population),
            "best_fitness": self.best_fitness,
            "best_tree_depth": self.best_tree.depth if self.best_tree else 0,
            "best_tree_size": self.best_tree.size if self.best_tree else 0,
            "best_tree_string": self.best_tree.to_string() if self.best_tree else "",
        }

