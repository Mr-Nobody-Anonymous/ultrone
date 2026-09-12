"""Prediction models for time-series and sequence forecasting.

Provides models for simulation analysis and forecasting:

- ``SequencePredictor``: Abstract base for all predictors
- ``LSTMPredictor``: LSTM-based sequence prediction
- ``GRUPredictor``: GRU-based sequence prediction
- ``TransformerPredictor``: Transformer encoder for time-series
- ``TemporalFusionTransformer``: Interpretable multi-horizon forecasting
- ``TrajectoryPredictor``: Multi-agent trajectory prediction
- ``ChangePointDetector``: Change-point detection in sequences

All predictors implement the ``SequencePredictor`` interface.
"""

from .base import SequencePredictor, PredictionConfig, PredictionResult
from .lstm import LSTMPredictor, LSTMConfig
from .gru import GRUPredictor, GRUConfig
from .transformer import TransformerPredictor, TransformerConfig
from .temporal_fusion import TemporalFusionTransformer, TFTConfig
from .trajectory import TrajectoryPredictor, TrajectoryConfig
from .change_point import ChangePointDetector, ChangePointConfig

__all__ = [
    "SequencePredictor", "PredictionConfig", "PredictionResult",
    "LSTMPredictor", "LSTMConfig",
    "GRUPredictor", "GRUConfig",
    "TransformerPredictor", "TransformerConfig",
    "TemporalFusionTransformer", "TFTConfig",
    "TrajectoryPredictor", "TrajectoryConfig",
    "ChangePointDetector", "ChangePointConfig",
]

