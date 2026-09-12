# Copyright (c) Ultrone Contributors. All rights reserved.
"""Model Converter — converts models between frameworks and precisions.

Supports PyTorch ↔ TensorFlow, ONNX, and precision conversion (fp32 →
fp16/int8). Produces safe fallback descriptors when backends are missing.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Ultrone.Models.Converter")


class ModelConverter:
    """Converts models between frameworks and precisions."""

    TARGETS = ("pytorch", "tensorflow", "onnx", "torchscript", "fp16", "fp32", "int8")

    def __init__(self):
        self._conversions: List[Dict[str, Any]] = []

    def convert(
        self,
        model: Any,
        target: str,
        model_id: str = "anonymous",
        source: str = "pytorch",
    ) -> Dict[str, Any]:
        """Convert a model to the target framework/precision."""
        if target not in self.TARGETS:
            raise ValueError(f"Unsupported target: {target}. Choose from {self.TARGETS}")

        result = self._perform_conversion(model, target, source)
        entry = {
            "conversion_id": f"C-{uuid.uuid4().hex[:10]}",
            "model_id": model_id,
            "source": source,
            "target": target,
            "converted_model": result["model"],
            "backend_available": result["backend_available"],
            "fallback": result["fallback"],
            "timestamp": time.time(),
        }
        self._conversions.append(entry)
        logger.info("Converted model %s from %s to %s", model_id, source, target)
        return entry

    # ------------------------------------------------------------------
    # Conversion logic
    # ------------------------------------------------------------------
    def _perform_conversion(self, model: Any, target: str, source: str) -> Dict[str, Any]:
        # Precision conversions
        if target == "fp16":
            return self._convert_precision(model, "half")
        if target == "fp32":
            return self._convert_precision(model, "float")
        if target == "int8":
            return self._convert_int8(model)

        # Framework conversions
        try:
            import torch  # type: ignore

            if not isinstance(model, torch.nn.Module):
                raise TypeError("Framework conversion requires a torch.nn.Module")
            if target == "torchscript":
                traced = torch.jit.trace(model, torch.randn(1, 3, 224, 224))
                return {"model": traced, "backend_available": True, "fallback": False}
            if target == "onnx":
                import io
                buf = io.BytesIO()
                torch.onnx.export(model, torch.randn(1, 3, 224, 224), buf, opset_version=17)
                return {"model": buf.getvalue(), "backend_available": True, "fallback": False}
            if target == "tensorflow":
                # tf converters require torch2tf; record descriptor
                logger.warning("PyTorch→TensorFlow conversion requires torch2tf; returning descriptor")
                return {"model": model, "backend_available": False, "fallback": True}
        except ImportError:
            logger.debug("torch not available; producing descriptor")
        except Exception as e:  # pragma: no cover
            logger.warning("Conversion failed (%s); producing descriptor", e)

        return {"model": model, "backend_available": False, "fallback": True}

    def _convert_precision(self, model: Any, method: str) -> Dict[str, Any]:
        if hasattr(model, method):
            try:
                return {"model": getattr(model, method)(), "backend_available": True, "fallback": False}
            except Exception:
                pass
        return {"model": model, "backend_available": False, "fallback": True}

    def _convert_int8(self, model: Any) -> Dict[str, Any]:
        try:
            import torch  # type: ignore

            if isinstance(model, torch.nn.Module):
                imported = torch.quantization.quantize_dynamic(
                    model, {torch.nn.Linear, torch.nn.LSTM}, dtype=torch.qint8
                )
                return {"model": imported, "backend_available": True, "fallback": False}
        except Exception:
            pass
        return {"model": model, "backend_available": False, "fallback": True}

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------
    def list_conversions(self) -> List[Dict[str, Any]]:
        """Return conversion history."""
        return list(self._conversions)

    def get_stats(self) -> Dict[str, Any]:
        targets: Dict[str, int] = {}
        for c in self._conversions:
            targets[c["target"]] = targets.get(c["target"], 0) + 1
        return {
            "type": "ModelConverter",
            "conversions_performed": len(self._conversions),
            "by_target": targets,
        }
