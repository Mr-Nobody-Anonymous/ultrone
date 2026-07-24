"""Machine Learning adapters for production-grade integrations.

Provides adapters for popular ML frameworks:

- ``PyTorchAdapter``: PyTorch model training/inference
- ``LightningAdapter``: PyTorch Lightning integration
- ``SB3Adapter``: Stable Baselines3 RL algorithm wrapper
- ``RayRLlibAdapter``: Ray RLlib distributed RL
- ``PyGAdapter``: PyTorch Geometric for GNNs
- ``ONNXAdapter``: ONNX Runtime for cross-platform inference
- ``XGBoostAdapter``: XGBoost/LightGBM for gradient boosting
"""

from .torch_adapter import PyTorchAdapter, TorchConfig
from .lightning_adapter import LightningAdapter, LightningConfig
from .sb3_adapter import SB3Adapter, SB3Config
from .ray_adapter import RayRLlibAdapter, RayRLlibConfig
from .pyg_adapter import PyGAdapter, PyGConfig
from .onnx_adapter import ONNXAdapter, ONNXConfig
from .xgboost_adapter import XGBoostAdapter, XGBConfig

__all__ = [
    "PyTorchAdapter", "TorchConfig",
    "LightningAdapter", "LightningConfig",
    "SB3Adapter", "SB3Config",
    "RayRLlibAdapter", "RayRLlibConfig",
    "PyGAdapter", "PyGConfig",
    "ONNXAdapter", "ONNXConfig",
    "XGBoostAdapter", "XGBConfig",
]
