"""PyTorch Geometric adapter for graph neural network training."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

logger = logging.getLogger("Ultrone.Brain.Learning.ML.PyG")


@dataclass
class PyGConfig:
    """Configuration for PyG adapter."""
    hidden_channels: int = 64
    num_layers: int = 3
    lr: float = 1e-3


class PyGAdapter:
    """Adapter for PyTorch Geometric GNN training.

    Provides a unified interface for:
    - GNN model creation (GCN, GAT, SAGE)
    - Graph dataset handling
    - Node/edge/graph-level prediction

    Requires: ``pip install torch-geometric``
    """

    def __init__(self, config: Optional[PyGConfig] = None):
        self.config = config or PyGConfig()
        self._model = None

    def create_gnn(self, in_channels: int, out_channels: int, gnn_type: str = "gcn") -> Any:
        """Create a GNN model."""
        try:
            import torch
            import torch.nn.functional as F
            from torch_geometric.nn import GCNConv, GATConv, SAGEConv

            gnn_map = {"gcn": GCNConv, "gat": GATConv, "sage": SAGEConv}
            conv = gnn_map.get(gnn_type, GCNConv)

            class SimpleGNN(torch.nn.Module):
                def __init__(self):
                    super().__init__()
                    self.conv1 = conv(in_channels, self.config.hidden_channels)
                    self.conv2 = conv(self.config.hidden_channels, self.config.hidden_channels)
                    self.conv3 = conv(self.config.hidden_channels, out_channels)

                def forward(self, x, edge_index):
                    x = self.conv1(x, edge_index).relu()
                    x = self.conv2(x, edge_index).relu()
                    x = self.conv3(x, edge_index)
                    return x

            self._model = SimpleGNN()
            return self._model
        except ImportError:
            logger.warning("torch-geometric not installed.")
            return None

    def get_stats(self) -> Dict[str, Any]:
        return {"type": "PyGAdapter"}
