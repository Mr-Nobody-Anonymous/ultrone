"""XGBoost adapter for gradient boosting models."""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("Ultrone.Brain.Learning.ML.XGBoost")


@dataclass
class XGBConfig:
    """Configuration for XGBoost adapter."""
    n_estimators: int = 100
    max_depth: int = 6
    learning_rate: float = 0.3
    objective: str = "reg:squarederror"
    use_gpu: bool = False


class XGBoostAdapter:
    """Adapter for XGBoost/LightGBM gradient boosting.

    Provides a unified interface for training and inference
    with gradient boosted trees, with GPU support.

    Requires: ``pip install xgboost``
    """

    def __init__(self, config: Optional[XGBConfig] = None):
        self.config = config or XGBConfig()
        self._model = None

    def train(self, X: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
        """Train an XGBoost model."""
        try:
            import xgboost as xgb
            params = {
                "n_estimators": self.config.n_estimators,
                "max_depth": self.config.max_depth,
                "learning_rate": self.config.learning_rate,
                "objective": self.config.objective,
                "tree_method": "gpu_hist" if self.config.use_gpu else "hist",
            }
            self._model = xgb.XGBRegressor(**params)
            self._model.fit(X, y)
            return {"status": "trained", "features": X.shape[1]}
        except ImportError:
            logger.warning("xgboost not installed.")
            return {"status": "skipped"}

    def predict(self, X: np.ndarray) -> Optional[np.ndarray]:
        """Run inference."""
        if self._model is None:
            return None
        return self._model.predict(X)

    def save(self, path: str) -> None:
        if self._model:
            self._model.save_model(path)

    def load(self, path: str) -> None:
        try:
            import xgboost as xgb
            self._model = xgb.XGBRegressor()
            self._model.load_model(path)
        except Exception as e:
            logger.error("Failed to load model: %s", e)

    def get_stats(self) -> Dict[str, Any]:
        return {"type": "XGBoostAdapter", "trained": self._model is not None}
