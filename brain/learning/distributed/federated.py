"""Federated learning coordinator."""
from __future__ import annotations
from typing import Any, Dict, List
import numpy as np

class FederatedLearning:
    def __init__(self, num_clients: int = 10) -> None:
        self.num_clients = num_clients
        self._global_params: Dict[str, np.ndarray] = {}
        self._round: int = 0
    def initialize(self, params: Dict[str, np.ndarray]) -> None:
        self._global_params = {k: v.copy() for k, v in params.items()}
    def aggregate(self, client_params: List[Dict[str, np.ndarray]]) -> Dict[str, np.ndarray]:
        if not client_params:
            return self._global_params
        for key in self._global_params:
            stacked = np.stack([c[key] for c in client_params if key in c])
            self._global_params[key] = np.mean(stacked, axis=0)
        self._round += 1
        return self._global_params
    @property
    def round_number(self) -> int:
        return self._round
