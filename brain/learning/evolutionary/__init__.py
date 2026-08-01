"""
Advanced Evolutionary Algorithms Module
=======================================
Implements cutting-edge evolutionary computation algorithms:

1. NEAT - NeuroEvolution of Augmenting Topologies
2. Novelty Search - Behavioral novelty exploration
3. MAP-Elites Integration - Quality Diversity for tactical genomes
4. CoDeepNEAT - Co-evolution of modules and blueprints
5. Genetic Programming - Evolve program/tactic trees
6. GAN Coevolution - Generative adversarial co-evolution
7. Epigenetic/Lamarckian Evolution - Inherit learned traits
8. NSGA-III - Many-objective evolutionary optimization
9. Quality Diversity (QD) Algorithms - Archive-based search
"""

from .neat import NEAT, NEATConfig, NEATGenome, NEATNode, NEATConnection
from .novelty_search import NoveltySearch, NoveltySearchConfig, NoveltyArchive
from .map_elites_integration import (
    GenomeMAPElites,
    MAPElitesIntegrationConfig,
    GenomeMAPElites as TacticalMAPElites,
    MAPElitesIntegrationConfig as MAPElitesIntegration,
)
from .codeepneat import (
    CoDeepNEAT, CoDeepNEATConfig,
    ModuleGene, ModuleGene as ModuleGenome,
    ModuleType, BlueprintGenome, BlueprintNode, BlueprintEdge,
)
from .genetic_programming import GeneticProgramming, GPConfig, GPTree, GPTreeNode
from .gan_coevolution import GANCoevolution, GANCoevolutionConfig
from .epigenetic import EpigeneticEvolution, EpigeneticConfig, EpigeneticTag
from .nsga3 import NSGA3, NSGA3Config
from .quality_diversity import QualityDiversity, QDConfig, QDArchive

__all__ = [
    "NEAT", "NEATConfig", "NEATGenome", "NEATNode", "NEATConnection",
    "NoveltySearch", "NoveltySearchConfig", "NoveltyArchive",
    "GenomeMAPElites", "MAPElitesIntegrationConfig", "MAPElitesIntegration", "TacticalMAPElites",
    "CoDeepNEAT", "CoDeepNEATConfig", "ModuleGene", "ModuleGenome", "ModuleType",
    "BlueprintGenome", "BlueprintNode", "BlueprintEdge",
    "GeneticProgramming", "GPConfig", "GPTree", "GPTreeNode",
    "GANCoevolution", "GANCoevolutionConfig",
    "EpigeneticEvolution", "EpigeneticConfig", "EpigeneticTag",
    "NSGA3", "NSGA3Config",
    "QualityDiversity", "QDConfig", "QDArchive",
]
