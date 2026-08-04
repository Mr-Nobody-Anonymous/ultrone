"""Automatic ensemble creation."""
from __future__ import annotations
from typing import Any, List

class AutoEnsemble:
    def __init__(self, strategy: str = "voting") -> None:
        self.strategy = strategy
        self._models: List[Any] = []
    def add_model(self, model: Any) -> None:
        self._models.append(model)
    def predict(self, X: Any) -> Any:
        if not self._models:
            return None
        preds = [m for m in self._models]
        return preds[0] if len(preds) == 1 else preds
    @property
    def model_count(self) -> int:
        return len(self._models)
