# Copyright (c) Ultrone Contributors. All rights reserved.
"""Interchangeable inference backends for the training loop.

Three adapters implement the charter's replaceability requirement:

- ``TestModelAdapter``   -- deterministic stand-in; hashes prompts into
  stable outputs so tests never touch a network or download weights.
- ``HostedModelAdapter`` -- wraps any injected async-free callable,
  e.g. a provider SDK function or an internal HTTP shim chosen by the
  deployment; this repo adds no networking dependencies itself.
- ``LocalModelAdapter``  -- real transformers generation, lazily
  loaded via ``load()``; construction never downloads anything, and
  calling ``generate()`` before ``load()`` fails loudly instead of
  pretending.

Adapters satisfy the *inference* half of the seam. Numeric execution
fidelity inside the governed loop stays behind
``trainer.make_executor`` / the Orchestrator executor parameter;
``scoring_fn`` lets a deployment attach a measured judge when one
exists. Nothing here fabricates scores.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional

from orchestration.model_registry import DIMENSIONS


@dataclass(frozen=True)
class ModelOutput:
    text: str
    meta: Dict[str, Any] = field(default_factory=dict)


class ModelAdapter:
    """Minimal backend contract shared by all adapters."""

    name: str = "adapter"

    def generate(self, prompt: str, *, context: str = "") -> ModelOutput:
        raise NotImplementedError

    def describe(self) -> Dict[str, Any]:
        return {"name": self.name}


class TestModelAdapter(ModelAdapter):
    """Deterministic pseudo-inference for reproducible pipelines."""

    def __init__(self, name: str = "test-model") -> None:
        self.name = name

    def generate(self, prompt: str, *, context: str = "") -> ModelOutput:
        digest = hashlib.sha256(
            f"{prompt}\n\x1f{context}".encode("utf-8")).hexdigest()
        return ModelOutput(text=f"answer:{digest[:12]}",
                           meta={"adapter": self.name, "sha8": digest[:8]})

    # Tell pytest this is an implementation class, not a test collection
    # (it is imported into test namespaces).
    __test__ = False

    def describe(self) -> Dict[str, Any]:
        return {"name": self.name, "kind": "test", "deterministic": True}


class HostedModelAdapter(ModelAdapter):
    """Bridges an externally supplied endpoint callable."""

    def __init__(self, endpoint: Callable[..., str],
                 name: str = "hosted-model") -> None:
        if endpoint is None:
            raise ValueError("hosted adapters require an endpoint "
                             "callable")
        self._endpoint = endpoint
        self.name = name

    def generate(self, prompt: str, *, context: str = "") -> ModelOutput:
        text = self._endpoint(prompt, context=context) \
            if _accepts_context(self._endpoint) \
            else self._endpoint(prompt)
        return ModelOutput(text=str(text),
                           meta={"adapter": self.name})

    def describe(self) -> Dict[str, Any]:
        return {"name": self.name, "kind": "hosted"}


class LocalModelAdapter(ModelAdapter):
    """Real local transformers generation; weights load lazily."""

    def __init__(self, model_id: str, *,
                 device: str = "cpu",
                 gen_kwargs: Optional[Dict[str, Any]] = None) -> None:
        if not model_id:
            raise ValueError("local adapters require a model_id")
        self.model_id = model_id
        self.device = device
        self.gen_kwargs = dict(gen_kwargs or {})
        self._pipeline: Optional[Any] = None
        self.name = f"local:{model_id}"

    def load(self) -> "LocalModelAdapter":
        try:
            from transformers import pipeline
        except ImportError as exc:              # pragma: no cover
            raise RuntimeError(
                "transformers is required for LocalModelAdapter; "
                "install it or use a hosted/test adapter") from exc
        self._pipeline = pipeline(
            "text-generation", model=self.model_id, device=self.device)
        return self

    def generate(self, prompt: str, *, context: str = "") -> ModelOutput:
        if self._pipeline is None:
            raise RuntimeError(
                f"model '{self.model_id}' not loaded -- call load() "
                f"first (construction deliberately performs no I/O)")
        outputs = self._pipeline(context + prompt,
                                 **self.gen_kwargs)
        generated = outputs[0]["generated_text"]
        completion = generated[len(context + prompt):] \
            if generated.startswith(context + prompt) else generated
        return ModelOutput(text=str(completion),
                           meta={"adapter": self.name,
                                 "model_id": self.model_id})

    def describe(self) -> Dict[str, Any]:
        return {"name": self.name, "kind": "local",
                "loaded": self._pipeline is not None,
                "dimensions": list(DIMENSIONS)}


def _accepts_context(fn: Callable) -> bool:
    import inspect
    try:
        signature = inspect.signature(fn)
    except (TypeError, ValueError):             # pragma: no cover
        return False
    return "context" in signature.parameters
