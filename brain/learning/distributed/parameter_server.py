"""Parameter server for distributed training."""
from __future__ import annotations
from typing import Any, Dict, List
import numpy as np

class ParameterServer:
    def __init__(self) -> None:
        self._params: Dict[str, np.ndarray] = {}
        self._gradients: List[Dict[str, np.ndarray]] = []
    def initialize(self, params: Dict[str, np.ndarray]) -> None:
        self._params = {k: v.copy() for k, v in params.items()}
    def push_gradients(self, gradients: Dict[str, np.ndarray]) -> None:
        self._gradients.append(gradients)
    def pull_params(self) -> Dict[str, np.ndarray]:
        return {k: v.copy() for k, v in self._params.items()}
    def apply_gradients(self, lr: float = 0.01) -> None:
        if not self._gradients:
            return
        for key in self._params:
            avg_grad = np.mean([g[key] for g in self._gradients if key in g], axis=0)
            self._params[key] -= lr * avg_grad
        self._gradients.clear()
    @property
    def pending_gradients(self) -> int:
        return len(self._gradients)
