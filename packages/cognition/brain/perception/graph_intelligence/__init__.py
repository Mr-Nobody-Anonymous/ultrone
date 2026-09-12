# Copyright (c) Ultrone Contributors. All rights reserved.
"""Graph Intelligence module for advanced graph reasoning.

Provides models for graph-structured data analysis:

- ``GraphNeuralNetwork``: Graph Neural Network for node/edge classification
- ``GraphAttentionNetwork``: Graph Attention Network (GAT)
- ``KnowledgeEmbeddings``: Knowledge graph embedding models
- ``CommunityDetection``: Community detection algorithms
- ``TemporalGraph``: Temporal graph analysis
- ``InfluencePropagation``: Influence propagation models
"""

from .gnn import GraphNeuralNetwork, GNNConfig
from .gat import GraphAttentionNetwork, GATConfig
from .knowledge_embeddings import KnowledgeEmbeddings, KGEConfig
from .community_detection import CommunityDetection, CommunityConfig
from .temporal_graph import TemporalGraph, TemporalGraphConfig

__all__ = [
    "GraphNeuralNetwork", "GNNConfig",
    "GraphAttentionNetwork", "GATConfig",
    "KnowledgeEmbeddings", "KGEConfig",
    "CommunityDetection", "CommunityConfig",
    "TemporalGraph", "TemporalGraphConfig",
]