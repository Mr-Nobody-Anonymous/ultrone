"""
NEAT: NeuroEvolution of Augmenting Topologies
=============================================
Evolves neural network structures and weights simultaneously.

Paper: "Evolving Neural Networks through Augmenting Topologies"
(Stanley & Miikkulainen, 2002)

Key innovation: Protecting innovation through historical tracking
and speciation, allowing complex topologies to emerge from simple ones.
"""

from __future__ import annotations

import math
import random
import copy
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Callable, Any, Set
from enum import Enum

logger = logging.getLogger("Ultrone.Brain.Learning.Evolutionary.NEAT")


class NodeType(Enum):
    """Types of nodes in a NEAT network."""
    INPUT = "input"
    HIDDEN = "hidden"
    OUTPUT = "output"


@dataclass
class NEATNode:
    """A single node/gene in the NEAT network."""
    node_id: int
    node_type: NodeType = NodeType.HIDDEN
    bias: float = 0.0
    activation: str = "tanh"  # tanh, sigmoid, relu, linear
    frozen: bool = False

    def clone(self) -> NEATNode:
        return NEATNode(
            node_id=self.node_id,
            node_type=self.node_type,
            bias=self.bias,
            activation=self.activation,
            frozen=self.frozen,
        )


@dataclass
class NEATConnection:
    """A connection/gene between two nodes."""
    innovation_id: int  # Historical marker for crossover
    from_node: int
    to_node: int
    weight: float = 0.0
    enabled: bool = True

    def clone(self) -> NEATConnection:
        return NEATConnection(
            innovation_id=self.innovation_id,
            from_node=self.from_node,
            to_node=self.to_node,
            weight=self.weight,
            enabled=self.enabled,
        )


@dataclass
class NEATGenome:
    """Complete NEAT genome encoding a neural network topology."""
    genome_id: str
    nodes: Dict[int, NEATNode] = field(default_factory=dict)
    connections: Dict[int, NEATConnection] = field(default_factory=dict)
    fitness: float = 0.0
    adjusted_fitness: float = 0.0
    species_id: int = -1
    generation: int = 0

    def mutate(self, config: NEATConfig) -> None:
        """Apply structural and weight mutations."""
        # Weight mutation
        for conn in self.connections.values():
            if random.random() < config.weight_mutate_prob:
                if random.random() < 0.9:
                    # Perturb
                    conn.weight += random.gauss(0, config.weight_mutate_power)
                else:
                    # Reset
                    conn.weight = random.gauss(0, 1)
                conn.weight = max(-config.max_weight, min(config.max_weight, conn.weight))

        # Add node mutation (split a connection)
        if random.random() < config.add_node_prob:
            enabled_conns = [c for c in self.connections.values() if c.enabled]
            if enabled_conns:
                conn_to_split = random.choice(enabled_conns)
                conn_to_split.enabled = False

                new_id = max(self.nodes.keys()) + 1
                new_node = NEATNode(node_id=new_id, node_type=NodeType.HIDDEN)
                self.nodes[new_id] = new_node

                # Create forward connection with weight 1.0
                forward_id = config.next_innovation()
                forward_conn = NEATConnection(
                    innovation_id=forward_id,
                    from_node=conn_to_split.from_node,
                    to_node=new_id,
                    weight=1.0,
                )
                self.connections[forward_id] = forward_conn

                # Create backward connection with original weight
                backward_id = config.next_innovation()
                backward_conn = NEATConnection(
                    innovation_id=backward_id,
                    from_node=new_id,
                    to_node=conn_to_split.to_node,
                    weight=conn_to_split.weight,
                )
                self.connections[backward_id] = backward_conn

        # Add connection mutation
        if random.random() < config.add_conn_prob:
            possible_pairs = []
            for from_id in self.nodes:
                if self.nodes[from_id].node_type == NodeType.OUTPUT:
                    continue
                for to_id in self.nodes:
                    if self.nodes[to_id].node_type == NodeType.INPUT:
                        continue
                    if from_id == to_id:
                        continue
                    # Check if connection already exists
                    exists = any(
                        c.from_node == from_id and c.to_node == to_id
                        for c in self.connections.values()
                    )
                    if not exists:
                        possible_pairs.append((from_id, to_id))

            if possible_pairs:
                from_id, to_id = random.choice(possible_pairs)
                new_id = config.next_innovation()
                new_conn = NEATConnection(
                    innovation_id=new_id,
                    from_node=from_id,
                    to_node=to_id,
                    weight=random.gauss(0, 1),
                )
                self.connections[new_id] = new_conn

        # Toggle connection enabled/disabled
        if random.random() < config.toggle_conn_prob:
            conns = list(self.connections.values())
            if conns:
                conn = random.choice(conns)
                conn.enabled = not conn.enabled

    def forward(self, inputs: List[float]) -> List[float]:
        """Forward pass through the network."""
        # Initialize node values
        node_values: Dict[int, float] = {}
        for nid, node in self.nodes.items():
            node_values[nid] = 0.0

        # Set input values
        input_nodes = [n for n in self.nodes.values() if n.node_type == NodeType.INPUT]
        for i, node in enumerate(sorted(input_nodes, key=lambda n: n.node_id)):
            if i < len(inputs):
                node_values[node.node_id] = inputs[i]

        # Process in topological order (simplified: iterate multiple times)
        output_nodes = [n for n in self.nodes.values() if n.node_type == NodeType.OUTPUT]
        output_node_ids = set(n.node_id for n in output_nodes)

        for _ in range(5):  # Fixed iterations for stability
            for conn in sorted(self.connections.values(), key=lambda c: c.innovation_id):
                if not conn.enabled:
                    continue
                if conn.from_node in node_values and conn.to_node in node_values:
                    val = node_values[conn.from_node] * conn.weight
                    node_values[conn.to_node] += val

            # Apply activations
            for nid, node in self.nodes.items():
                if node.node_type != NodeType.INPUT:
                    node_values[nid] = self._activate(node_values[nid], node.activation)

        # Collect outputs
        outputs = []
        for node in sorted(output_nodes, key=lambda n: n.node_id):
            outputs.append(node_values[node.node_id])
        return outputs

    def _activate(self, x: float, activation: str) -> float:
        if activation == "tanh":
            return math.tanh(x)
        elif activation == "sigmoid":
            return 1.0 / (1.0 + math.exp(-max(-100, min(100, x))))
        elif activation == "relu":
            return max(0.0, x)
        elif activation == "linear":
            return x
        return math.tanh(x)

    def clone(self) -> NEATGenome:
        return NEATGenome(
            genome_id=self.genome_id,
            nodes={k: v.clone() for k, v in self.nodes.items()},
            connections={k: v.clone() for k, v in self.connections.items()},
            fitness=self.fitness,
            adjusted_fitness=self.adjusted_fitness,
            species_id=self.species_id,
            generation=self.generation,
        )

    def complexity(self) -> int:
        """Return number of connections (network complexity)."""
        return len(self.connections)


@dataclass
class NEATConfig:
    """Configuration for NEAT evolution."""
    population_size: int = 150
    input_size: int = 5
    output_size: int = 3
    weight_mutate_prob: float = 0.8
    weight_mutate_power: float = 0.5
    add_node_prob: float = 0.03
    add_conn_prob: float = 0.05
    toggle_conn_prob: float = 0.01
    max_weight: float = 3.0
    compatibility_threshold: float = 3.0
    compatibility_disjoint_coeff: float = 1.0
    compatibility_weight_coeff: float = 0.5
    survival_threshold: float = 0.2
    elitism: int = 2
    crossover_prob: float = 0.75
    _innovation_counter: int = 0

    def next_innovation(self) -> int:
        self._innovation_counter += 1
        return self._innovation_counter


class NEAT:
    """
    NEAT: NeuroEvolution of Augmenting Topologies.

    Evolves both the weights and topology of neural networks.
    Uses historical tracking, speciation, and complexification.
    """

    def __init__(self, config: Optional[NEATConfig] = None):
        self.config = config or NEATConfig()
        self.population: List[NEATGenome] = []
        self.species: Dict[int, List[NEATGenome]] = {}
        self.generation = 0
        self.best_genome: Optional[NEATGenome] = None
        self.best_fitness: float = -float('inf')
        self._next_species_id = 0
        self._fitness_history: List[float] = []

    def initialize_population(self) -> None:
        """Create initial population with minimal topologies."""
        self.population = []
        for i in range(self.config.population_size):
            genome = self._create_minimal_genome(f"NEAT-{i}")
            self.population.append(genome)

    def _create_minimal_genome(self, genome_id: str) -> NEATGenome:
        """Create a minimal genome with input->output connections."""
        genome = NEATGenome(genome_id=genome_id)

        # Input nodes
        for i in range(self.config.input_size):
            node = NEATNode(node_id=i, node_type=NodeType.INPUT)
            genome.nodes[i] = node

        # Output nodes
        n_inputs = self.config.input_size
        for i in range(self.config.output_size):
            node = NEATNode(node_id=n_inputs + i, node_type=NodeType.OUTPUT)
            genome.nodes[n_inputs + i] = node

        # Fully connect input to output
        for i in range(self.config.input_size):
            for j in range(self.config.output_size):
                conn_id = self.config.next_innovation()
                conn = NEATConnection(
                    innovation_id=conn_id,
                    from_node=i,
                    to_node=n_inputs + j,
                    weight=random.gauss(0, 1),
                )
                genome.connections[conn_id] = conn

        return genome

    def evaluate_fitness(self, genome: NEATGenome, fitness_fn: Callable[[NEATGenome], float]) -> float:
        """Evaluate and update fitness for a genome."""
        fitness = fitness_fn(genome)
        genome.fitness = fitness
        if fitness > self.best_fitness:
            self.best_fitness = fitness
            self.best_genome = genome.clone()
        return fitness

    def evaluate_population(self, fitness_fn: Callable[[NEATGenome], float]) -> None:
        """Evaluate all genomes in the population."""
        for genome in self.population:
            self.evaluate_fitness(genome, fitness_fn)

    def speciate(self) -> None:
        """Divide population into species based on topological similarity."""
        self.species = {}

        for genome in self.population:
            assigned = False
            for species_id, members in self.species.items():
                if members and self._compatibility_distance(genome, members[0]) < self.config.compatibility_threshold:
                    members.append(genome)
                    genome.species_id = species_id
                    assigned = True
                    break

            if not assigned:
                species_id = self._next_species_id
                self._next_species_id += 1
                self.species[species_id] = [genome]
                genome.species_id = species_id

    def _compatibility_distance(self, g1: NEATGenome, g2: NEATGenome) -> float:
        """Calculate topological distance between two genomes."""
        g1_innov = set(c.innovation_id for c in g1.connections.values())
        g2_innov = set(c.innovation_id for c in g2.connections.values())

        disjoint = len(g1_innov.symmetric_difference(g2_innov))
        matching = g1_innov.intersection(g2_innov)

        weight_diff = 0.0
        for innov in matching:
            w1 = g1.connections[innov].weight
            w2 = g2.connections[innov].weight
            weight_diff += abs(w1 - w2)

        n = max(len(g1.connections), len(g2.connections))
        n = max(n, 1)

        return (self.config.compatibility_disjoint_coeff * disjoint / n +
                self.config.compatibility_weight_coeff * weight_diff / max(len(matching), 1))

    def adjust_fitness(self) -> None:
        """Apply fitness sharing within species."""
        for species_id, members in self.species.items():
            n = len(members)
            for genome in members:
                genome.adjusted_fitness = genome.fitness / n

    def crossover(self, parent1: NEATGenome, parent2: NEATGenome) -> NEATGenome:
        """Perform crossover between two parents."""
        # Determine which parent has higher fitness
        if parent1.fitness >= parent2.fitness:
            dominant = parent1
            recessive = parent2
        else:
            dominant = parent2
            recessive = parent1

        child = NEATGenome(
            genome_id=f"NEAT-CROSS-{random.randint(10000, 99999)}",
            generation=dominant.generation + 1,
            nodes={k: v.clone() for k, v in dominant.nodes.items()},
        )

        # Crossover connections
        for innov in dominant.connections:
            if innov in recessive.connections:
                # Matching gene: randomly inherit from either parent
                if random.random() < 0.5:
                    child.connections[innov] = dominant.connections[innov].clone()
                else:
                    child.connections[innov] = recessive.connections[innov].clone()
            else:
                # Disjoint/excess gene: inherit from dominant parent
                child.connections[innov] = dominant.connections[innov].clone()

        return child

    def reproduce(self) -> List[NEATGenome]:
        """Create next generation through selection, crossover, and mutation."""
        next_population = []

        # Keep elites from each species
        for species_id, members in self.species.items():
            members.sort(key=lambda g: g.fitness, reverse=True)
            n_elite = max(1, int(len(members) * self.config.survival_threshold))
            next_population.extend(m.clone() for m in members[:n_elite])

        # Fill remaining slots
        remaining = self.config.population_size - len(next_population)
        all_members = [g for members in self.species.values() for g in members]

        while len(next_population) < self.config.population_size:
            if random.random() < self.config.crossover_prob and len(all_members) >= 2:
                p1 = random.choice(all_members)
                p2 = random.choice(all_members)
                child = self.crossover(p1, p2)
            else:
                child = random.choice(all_members).clone()

            child.mutate(self.config)
            next_population.append(child)

        return next_population[:self.config.population_size]

    def evolve_generation(self, fitness_fn: Callable[[NEATGenome], float]) -> None:
        """Run one full generation of NEAT evolution."""
        self.evaluate_population(fitness_fn)
        self.speciate()
        self.adjust_fitness()

        avg_fitness = sum(g.fitness for g in self.population) / len(self.population)
        self._fitness_history.append(avg_fitness)

        logger.info(
            f"NEAT Gen {self.generation}: "
            f"Pop={len(self.population)} Species={len(self.species)} "
            f"Best={self.best_fitness:.4f} Avg={avg_fitness:.4f}"
        )

        self.population = self.reproduce()
        self.generation += 1

    def train(self, fitness_fn: Callable[[NEATGenome], float], n_generations: int = 100) -> NEATGenome:
        """Train the NEAT population for a number of generations."""
        if not self.population:
            self.initialize_population()

        for _ in range(n_generations):
            self.evolve_generation(fitness_fn)

        return self.best_genome if self.best_genome else self.population[0]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "generation": self.generation,
            "population_size": len(self.population),
            "species_count": len(self.species),
            "best_fitness": self.best_fitness,
            "avg_fitness": sum(g.fitness for g in self.population) / len(self.population) if self.population else 0,
            "best_complexity": self.best_genome.complexity() if self.best_genome else 0,
        }
