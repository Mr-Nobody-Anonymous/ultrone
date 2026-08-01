# Copyright (c) Ultrone Contributors. All rights reserved.
"""
CoDeepNEAT: Co-evolution of Deep Neural Network Modules and Blueprints
========================================================================
Extends NEAT to evolve deep networks by co-evolving:
1. Modules: Small subnetworks (like convolutional blocks, LSTM cells)
2. Blueprints: Graph structures that assemble modules into a full network

Implementation based on:
"CoDeepNEAT: Co-evolution of Deep Neural Networks" (Miikkulainen et al., 2019)
"""

from __future__ import annotations

import logging
import random
import copy
import numpy as np
from typing import Any, Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum

from .neat import NEATGenome, NEATNode, NEATConnection, NEATConfig

logger = logging.getLogger("Ultrone.Brain.Learning.Evolutionary.CoDeepNEAT")


class ModuleType(Enum):
    """Types of modules that can be evolved."""
    DENSE = "dense"
    LSTM = "lstm"
    GRU = "gru"
    ATTENTION = "attention"
    CONV1D = "conv1d"
    RESIDUAL = "residual"
    GATING = "gating"


@dataclass
class ModuleGene:
    """A single module gene - a small subnetwork component."""
    module_id: str
    module_type: ModuleType = ModuleType.DENSE
    n_neurons: int = 16
    activation: str = "relu"
    dropout_rate: float = 0.0
    learning_rate_mult: float = 1.0
    frozen: bool = False
    innovation_number: int = 0

    def mutate(self, mutation_rate: float = 0.15) -> bool:
        """Mutate this module gene. Returns True if changed."""
        changed = False
        if random.random() < mutation_rate:
            self.n_neurons = max(4, min(256, int(self.n_neurons * random.uniform(0.5, 2.0))))
            changed = True
        if random.random() < mutation_rate:
            self.dropout_rate = max(0.0, min(0.9, self.dropout_rate + random.gauss(0, 0.05)))
            changed = True
        if random.random() < mutation_rate:
            self.learning_rate_mult = max(0.1, min(10.0, self.learning_rate_mult * random.uniform(0.5, 2.0)))
            changed = True
        if random.random() < mutation_rate * 0.5:
            types = list(ModuleType)
            self.module_type = random.choice(types)
            changed = True
        return changed

    def clone(self) -> ModuleGene:
        return ModuleGene(
            module_id=self.module_id,
            module_type=self.module_type,
            n_neurons=self.n_neurons,
            activation=self.activation,
            dropout_rate=self.dropout_rate,
            learning_rate_mult=self.learning_rate_mult,
            frozen=self.frozen,
            innovation_number=self.innovation_number,
        )


@dataclass
class BlueprintNode:
    """A node in the blueprint graph - references a module."""
    node_id: str
    module_id: str  # References ModuleGene.module_id
    depth: int = 0
    n_parallel: int = 1  # Parallel copies of this module
    aggregation: str = "sum"  # How to combine parallel outputs: sum, mean, concat

    def clone(self) -> BlueprintNode:
        return BlueprintNode(
            node_id=self.node_id,
            module_id=self.module_id,
            depth=self.depth,
            n_parallel=self.n_parallel,
            aggregation=self.aggregation,
        )


@dataclass
class BlueprintEdge:
    """Connection between two blueprint nodes."""
    source_id: str
    target_id: str
    weight: float = 1.0
    enabled: bool = True
    innovation_number: int = 0

    def clone(self) -> BlueprintEdge:
        return BlueprintEdge(
            source_id=self.source_id,
            target_id=self.target_id,
            weight=self.weight,
            enabled=self.enabled,
            innovation_number=self.innovation_number,
        )


@dataclass
class BlueprintGenome:
    """
    A blueprint genome that assembles modules into a network architecture.
    
    The blueprint is a DAG where each node references a module,
    and edges define the flow between modules.
    """
    genome_id: str
    nodes: Dict[str, BlueprintNode] = field(default_factory=dict)
    edges: Dict[str, BlueprintEdge] = field(default_factory=dict)
    input_node_ids: List[str] = field(default_factory=list)
    output_node_ids: List[str] = field(default_factory=list)
    fitness: float = 0.0
    generation: int = 0
    mutation_rate: float = 0.15
    n_inputs: int = 1
    n_outputs: int = 1

    def add_node(self, node: BlueprintNode) -> None:
        self.nodes[node.node_id] = node

    def add_edge(self, edge: BlueprintEdge) -> None:
        key = f"{edge.source_id}->{edge.target_id}"
        self.edges[key] = edge

    def mutate(self, module_pool: Dict[str, ModuleGene]) -> bool:
        """Mutate blueprint structure. Returns True if changed."""
        changed = False

        # Add new node (insert between existing nodes)
        if random.random() < self.mutation_rate * 0.3 and len(self.edges) > 0:
            edge_key = random.choice(list(self.edges.keys()))
            edge = self.edges[edge_key]
            edge.enabled = False
            
            # Pick a random module from pool
            module_id = random.choice(list(module_pool.keys()))
            new_node = BlueprintNode(
                node_id=f"bp_node_{len(self.nodes)}",
                module_id=module_id,
                depth=self.nodes[edge.target_id].depth - 1,
            )
            self.add_node(new_node)
            
            # Connect source -> new node -> target
            self.add_edge(BlueprintEdge(
                source_id=edge.source_id,
                target_id=new_node.node_id,
                weight=1.0,
                innovation_number=len(self.edges),
            ))
            self.add_edge(BlueprintEdge(
                source_id=new_node.node_id,
                target_id=edge.target_id,
                weight=edge.weight,
                innovation_number=len(self.edges),
            ))
            changed = True

        # Add new edge
        if random.random() < self.mutation_rate * 0.2:
            source = random.choice(list(self.nodes.keys()))
            target = random.choice(list(self.nodes.keys()))
            if source != target and f"{source}->{target}" not in self.edges:
                self.add_edge(BlueprintEdge(
                    source_id=source,
                    target_id=target,
                    weight=random.uniform(-1.0, 1.0),
                    innovation_number=len(self.edges),
                ))
                changed = True

        # Mutate edge weights
        for edge in self.edges.values():
            if random.random() < self.mutation_rate:
                edge.weight += random.gauss(0, 0.1)
                edge.weight = max(-3.0, min(3.0, edge.weight))
                changed = True

        # Mutate node parameters
        for node in self.nodes.values():
            if random.random() < self.mutation_rate:
                node.n_parallel = max(1, min(8, node.n_parallel + random.choice([-1, 1])))
                changed = True
            if random.random() < self.mutation_rate * 0.5:
                aggs = ["sum", "mean", "concat"]
                node.aggregation = random.choice(aggs)
                changed = True

        return changed

    def clone(self) -> BlueprintGenome:
        return BlueprintGenome(
            genome_id=f"{self.genome_id}_clone",
            nodes={k: v.clone() for k, v in self.nodes.items()},
            edges={k: v.clone() for k, v in self.edges.items()},
            input_node_ids=list(self.input_node_ids),
            output_node_ids=list(self.output_node_ids),
            fitness=self.fitness,
            generation=self.generation + 1,
            mutation_rate=self.mutation_rate,
            n_inputs=self.n_inputs,
            n_outputs=self.n_outputs,
        )


@dataclass
class CoDeepNEATConfig:
    """Configuration for CoDeepNEAT."""
    module_population_size: int = 50
    blueprint_population_size: int = 50
    module_mutation_rate: float = 0.15
    blueprint_mutation_rate: float = 0.15
    crossover_rate: float = 0.7
    elitism_ratio: float = 0.1
    n_generations: int = 100
    min_module_innovation: int = 0


class CoDeepNEAT:
    """
    CoDeepNEAT: Co-evolution of Modules and Blueprints.
    
    Evolves both:
    - Module population: Small subnetworks
    - Blueprint population: Assembly graphs
    
    The fitness of a module depends on how well it performs
    when used in blueprints, creating a co-evolutionary dynamic.
    """

    def __init__(self, config: Optional[CoDeepNEATConfig] = None):
        self.config = config or CoDeepNEATConfig()
        self.generation = 0
        
        # Module population
        self.modules: Dict[str, ModuleGene] = {}
        self.module_population: List[str] = []  # List of module_ids
        
        # Blueprint population
        self.blueprints: Dict[str, BlueprintGenome] = {}
        self.blueprint_population: List[str] = []  # List of genome_ids
        
        self.best_blueprint: Optional[BlueprintGenome] = None
        self.best_blueprint_fitness: float = 0.0
        self._innovation_counter = 0

    def _next_innovation(self) -> int:
        self._innovation_counter += 1
        return self._innovation_counter

    def initialize_module(self, module_type: Optional[ModuleType] = None) -> ModuleGene:
        """Create a random module gene."""
        if module_type is None:
            module_type = random.choice(list(ModuleType))
        
        module = ModuleGene(
            module_id=f"module_{len(self.modules)}",
            module_type=module_type,
            n_neurons=random.choice([8, 16, 32, 64]),
            activation=random.choice(["relu", "tanh", "sigmoid", "gelu"]),
            dropout_rate=random.uniform(0.0, 0.5),
            learning_rate_mult=random.uniform(0.1, 3.0),
            innovation_number=self._next_innovation(),
        )
        self.modules[module.module_id] = module
        return module

    def initialize_blueprint(self, n_inputs: int = 1, n_outputs: int = 1) -> BlueprintGenome:
        """Create a random blueprint genome."""
        blueprint = BlueprintGenome(
            genome_id=f"blueprint_{len(self.blueprints)}",
            n_inputs=n_inputs,
            n_outputs=n_outputs,
            generation=self.generation,
        )
        
        # Create input nodes
        module_ids = list(self.modules.keys())
        if not module_ids:
            module = self.initialize_module()
            module_ids = [module.module_id]
        
        for i in range(n_inputs):
            mid = random.choice(module_ids)
            node = BlueprintNode(
                node_id=f"input_{i}",
                module_id=mid,
                depth=0,
            )
            blueprint.add_node(node)
            blueprint.input_node_ids.append(node.node_id)
        
        # Create hidden nodes (1-3 layers)
        n_hidden = random.randint(1, 3)
        for h in range(n_hidden):
            mid = random.choice(module_ids)
            node = BlueprintNode(
                node_id=f"hidden_{h}",
                module_id=mid,
                depth=h + 1,
                n_parallel=random.choice([1, 2, 4]),
            )
            blueprint.add_node(node)
        
        # Create output nodes
        for i in range(n_outputs):
            mid = random.choice(module_ids)
            node = BlueprintNode(
                node_id=f"output_{i}",
                module_id=mid,
                depth=n_hidden + 1,
            )
            blueprint.add_node(node)
            blueprint.output_node_ids.append(node.node_id)
        
        # Connect layers sequentially
        all_nodes = blueprint.input_node_ids + [n for n in blueprint.nodes if n not in blueprint.input_node_ids and n not in blueprint.output_node_ids] + blueprint.output_node_ids
        for i in range(len(all_nodes) - 1):
            blueprint.add_edge(BlueprintEdge(
                source_id=all_nodes[i],
                target_id=all_nodes[i + 1],
                weight=random.uniform(-1.0, 1.0),
                innovation_number=self._next_innovation(),
            ))
        
        # Add skip connections
        if random.random() < 0.3 and len(all_nodes) > 2:
            source = random.choice(all_nodes[:-1])
            target = random.choice(all_nodes[1:])
            if source != target and f"{source}->{target}" not in blueprint.edges:
                blueprint.add_edge(BlueprintEdge(
                    source_id=source,
                    target_id=target,
                    weight=random.uniform(-0.5, 0.5),
                    innovation_number=self._next_innovation(),
                ))
        
        self.blueprints[blueprint.genome_id] = blueprint
        return blueprint

    def initialize_populations(self, n_modules: int = 30, n_blueprints: int = 30) -> None:
        """Initialize both populations."""
        for _ in range(n_modules):
            module = self.initialize_module()
            self.module_population.append(module.module_id)
        
        for _ in range(n_blueprints):
            bp = self.initialize_blueprint()
            self.blueprint_population.append(bp.genome_id)
        
        logger.info(
            f"CoDeepNEAT initialized: {len(self.module_population)} modules, "
            f"{len(self.blueprint_population)} blueprints"
        )

    def crossover_modules(self, parent_a: ModuleGene, parent_b: ModuleGene) -> ModuleGene:
        """Crossover two module genes."""
        child = ModuleGene(
            module_id=f"module_{len(self.modules)}",
            module_type=random.choice([parent_a.module_type, parent_b.module_type]),
            n_neurons=random.choice([parent_a.n_neurons, parent_b.n_neurons]),
            activation=random.choice([parent_a.activation, parent_b.activation]),
            dropout_rate=(parent_a.dropout_rate + parent_b.dropout_rate) / 2,
            learning_rate_mult=(parent_a.learning_rate_mult + parent_b.learning_rate_mult) / 2,
            innovation_number=self._next_innovation(),
        )
        self.modules[child.module_id] = child
        return child

    def crossover_blueprints(self, parent_a: BlueprintGenome, parent_b: BlueprintGenome) -> BlueprintGenome:
        """Crossover two blueprint genomes."""
        child = BlueprintGenome(
            genome_id=f"blueprint_{len(self.blueprints)}",
            n_inputs=parent_a.n_inputs,
            n_outputs=parent_a.n_outputs,
            generation=self.generation + 1,
        )
        
        # Inherit nodes from both parents
        all_nodes = {}
        for bp in [parent_a, parent_b]:
            for nid, node in bp.nodes.items():
                if nid not in all_nodes:
                    all_nodes[nid] = node.clone()
        
        for node in all_nodes.values():
            child.add_node(node)
        
        # Inherit edges (intersection + random from union)
        parent_edges = set(parent_a.edges.keys()) | set(parent_b.edges.keys())
        for edge_key in parent_edges:
            if edge_key in parent_a.edges and edge_key in parent_b.edges:
                # Both parents have it - blend weights
                edge = parent_a.edges[edge_key].clone()
                edge.weight = (parent_a.edges[edge_key].weight + parent_b.edges[edge_key].weight) / 2
            elif edge_key in parent_a.edges:
                edge = parent_a.edges[edge_key].clone()
            else:
                edge = parent_b.edges[edge_key].clone()
            
            child.edges[edge_key] = edge
        
        child.input_node_ids = list(parent_a.input_node_ids)
        child.output_node_ids = list(parent_a.output_node_ids)
        
        self.blueprints[child.genome_id] = child
        return child

    def evolve_modules(self, fitness_map: Dict[str, float]) -> List[str]:
        """Evolve module population based on fitness."""
        if not self.module_population:
            return []
        
        # Sort by fitness
        scored = [(mid, fitness_map.get(mid, 0.0)) for mid in self.module_population]
        scored.sort(key=lambda x: x[1], reverse=True)
        
        # Elitism
        n_elite = max(1, int(len(scored) * self.config.elitism_ratio))
        elites = [mid for mid, _ in scored[:n_elite]]
        
        # Generate offspring
        offspring = list(elites)
        while len(offspring) < len(self.module_population):
            if random.random() < self.config.crossover_rate and len(elites) >= 2:
                a = random.choice(elites)
                b = random.choice([e for e in elites if e != a])
                child = self.crossover_modules(self.modules[a], self.modules[b])
            else:
                parent = random.choice(elites)
                child = self.modules[parent].clone()
                child.mutate(self.config.module_mutation_rate)
                self.modules[child.module_id] = child
            
            offspring.append(child.module_id)
        
        self.module_population = offspring
        return offspring

    def evolve_blueprints(self, fitness_map: Dict[str, float]) -> List[str]:
        """Evolve blueprint population based on fitness."""
        if not self.blueprint_population:
            return []
        
        # Sort by fitness
        scored = [(bid, fitness_map.get(bid, 0.0)) for bid in self.blueprint_population]
        scored.sort(key=lambda x: x[1], reverse=True)
        
        # Track best
        if scored and scored[0][1] > self.best_blueprint_fitness:
            self.best_blueprint_fitness = scored[0][1]
            self.best_blueprint = self.blueprints[scored[0][0]].clone()
        
        # Elitism
        n_elite = max(1, int(len(scored) * self.config.elitism_ratio))
        elites = [bid for bid, _ in scored[:n_elite]]
        
        # Generate offspring
        offspring = list(elites)
        while len(offspring) < len(self.blueprint_population):
            if random.random() < self.config.crossover_rate and len(elites) >= 2:
                a = random.choice(elites)
                b = random.choice([e for e in elites if e != a])
                child = self.crossover_blueprints(self.blueprints[a], self.blueprints[b])
            else:
                parent = random.choice(elites)
                child = self.blueprints[parent].clone()
                child.mutate(self.modules)
                self.blueprints[child.genome_id] = child
            
            offspring.append(child.genome_id)
        
        self.blueprint_population = offspring
        self.generation += 1
        return offspring

    def evaluate_blueprint_fitness(
        self,
        blueprint: BlueprintGenome,
        fitness_fn: Callable[[BlueprintGenome, Dict[str, ModuleGene]], float],
    ) -> float:
        """Evaluate a blueprint's fitness using the provided function."""
        fitness = fitness_fn(blueprint, self.modules)
        blueprint.fitness = fitness
        return fitness

    def evaluate_module_fitness(
        self,
        module: ModuleGene,
        fitness_fn: Callable[[ModuleGene, List[BlueprintGenome]], float],
    ) -> float:
        """
        Evaluate a module's fitness based on its usage in blueprints.
        
        Module fitness is typically the average fitness of blueprints
        that use this module.
        """
        fitness = fitness_fn(module, [self.blueprints[bid] for bid in self.blueprint_population])
        return fitness

    def get_stats(self) -> Dict[str, Any]:
        """Get CoDeepNEAT statistics."""
        return {
            "generation": self.generation,
            "n_modules": len(self.module_population),
            "n_blueprints": len(self.blueprint_population),
            "best_blueprint_fitness": self.best_blueprint_fitness,
            "n_module_types": len(set(self.modules[mid].module_type.value for mid in self.module_population)),
        }
