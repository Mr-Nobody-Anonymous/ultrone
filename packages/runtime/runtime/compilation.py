from __future__ import annotations

from typing import Any, Optional


class CompilationManager:
    """Wrap optional torch.compile calls with graceful fallback."""

    def __init__(self, mode: str = "auto") -> None:
        self.mode = (mode or "auto").lower()
        self._compiled: dict[str, Any] = {}

    def should_compile(self, model: Any) -> bool:
        if self.mode == "off":
            return False
        if self.mode == "on":
            return True
        try:
            import torch  # type: ignore
        except ImportError:  # pragma: no cover - optional dependency
            return False
        return hasattr(torch, "compile") and hasattr(model, "__class__") and getattr(model, "__class__", None).__name__ != "Dummy"

    def compile(self, model: Any, model_id: Optional[str] = None) -> Any:
        if not self.should_compile(model):
            return model
        try:
            import torch  # type: ignore

            compiled = torch.compile(model, fullgraph=False)
            if model_id is not None:
                self._compiled[model_id] = compiled
            return compiled
        except Exception:
            return model


def compile_model(model: Any, mode: str = "auto", model_id: Optional[str] = None) -> Any:
    return CompilationManager(mode=mode).compile(model, model_id=model_id)
