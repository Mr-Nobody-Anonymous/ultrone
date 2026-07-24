"""ONNX Runtime adapter for cross-platform model inference."""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Ultrone.Brain.Learning.ML.ONNX")


@dataclass
class ONNXConfig:
    """Configuration for ONNX adapter."""
    execution_provider: str = "cpu"  # cpu, cuda, tensorrt


class ONNXAdapter:
    """Adapter for ONNX Runtime inference.

    Enables deployment of trained models across platforms
    with hardware acceleration (CPU, CUDA, TensorRT).

    Requires: ``pip install onnxruntime`` or ``pip install onnxruntime-gpu``
    """

    def __init__(self, config: Optional[ONNXConfig] = None):
        self.config = config or ONNXConfig()
        self._session = None
        self._input_name = None
        self._output_name = None

    def load_model(self, path: str) -> bool:
        """Load an ONNX model."""
        try:
            import onnxruntime as ort
            providers = {"cpu": ["CPUExecutionProvider"], "cuda": ["CUDAExecutionProvider", "CPUExecutionProvider"]}
            self._session = ort.InferenceSession(
                path,
                providers=providers.get(self.config.execution_provider, ["CPUExecutionProvider"]),
            )
            self._input_name = self._session.get_inputs()[0].name
            self._output_name = self._session.get_outputs()[0].name
            logger.info("Loaded ONNX model from %s", path)
            return True
        except ImportError:
            logger.warning("onnxruntime not installed.")
            return False
        except Exception as e:
            logger.error("Failed to load ONNX model: %s", e)
            return False

    def infer(self, inputs: np.ndarray) -> Optional[np.ndarray]:
        """Run inference with the ONNX model."""
        if self._session is None:
            return None
        return self._session.run([self._output_name], {self._input_name: inputs})[0]

    def get_stats(self) -> Dict[str, Any]:
        return {"type": "ONNXAdapter", "model_loaded": self._session is not None}
