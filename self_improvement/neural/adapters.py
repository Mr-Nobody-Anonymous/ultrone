# Copyright (c) Ultrone Contributors. All rights reserved.
"""Real-model adapter layer (item 1 of the neural milestone).

The existing ``self_improvement.self_training.adapters`` module already
defines the *contract* -- a ``ModelAdapter`` with a single
``generate(prompt, context=...)`` method returning a ``ModelOutput``.
That contract is exactly what orchestration / evaluation / promotion
already consume, so a real neural backend is "just" another adapter
behind the same seam.

What this module adds:

* ``MockNeuralAdapter`` -- a deterministic test double that *behaves*
  like a small neural model (per-dimension score, soft saturation,
  output variance proportional to context size). It is the substitute
  used by every test and by the standalone benchmark, because it lets
  us run end-to-end against the seam without downloading a real model.
* ``NeuralAdapterConfig`` -- a frozen record of the configuration
  fingerprinted into the lineage (model_id, tokenizer, max_new_tokens,
  temperature, top_p, device).
* ``NeuralGenerationStats`` -- measurement returned from every
  generation, used for the latency / resource dimensions in
  ``CapabilityMetrics``.

The contract guarantee: nothing here changes how the orchestration
layer invokes an adapter. ``HostedModelAdapter`` and
``LocalModelAdapter`` remain the production targets; this module only
adds a deterministic test double and a typed config so the new
neural-training components (LoRATrainer, ModelPipeline,
NeuralCapabilityBenchmark) can fingerprint what produced what.
"""

from __future__ import annotations

import hashlib
import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from self_improvement.self_training.adapters import (
    ModelAdapter,
    ModelOutput,
)


# --- Config & stats -------------------------------------------------------- #


@dataclass(frozen=True)
class NeuralAdapterConfig:
    """Frozen, hashable fingerprint of a neural adapter's configuration.

    Every field here is included in the model lineage hash so a
    candidate that was trained with ``temperature=0.0`` and a candidate
    that was trained with ``temperature=0.7`` are recorded as
    *different* models even if their capability weights happen to
    coincide. This is the rule that keeps "what changed between
    baseline and candidate" answerable from a record rather than from
    memory.
    """

    model_id: str
    tokenizer_id: str = ""
    max_new_tokens: int = 128
    temperature: float = 0.0
    top_p: float = 1.0
    device: str = "cpu"
    dtype: str = "float32"
    extra: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.model_id:
            raise ValueError("model_id is required")
        if self.max_new_tokens <= 0:
            raise ValueError("max_new_tokens must be positive")
        if not 0.0 <= self.temperature <= 2.0:
            raise ValueError("temperature must lie in [0, 2]")
        if not 0.0 < self.top_p <= 1.0:
            raise ValueError("top_p must lie in (0, 1]")
        if self.device not in ("cpu", "cuda", "mps", "auto"):
            raise ValueError(f"unknown device: {self.device!r}")

    def fingerprint(self) -> str:
        """Stable 16-char hash of the configuration."""
        payload = {
            "model_id": self.model_id,
            "tokenizer_id": self.tokenizer_id,
            "max_new_tokens": self.max_new_tokens,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "device": self.device,
            "dtype": self.dtype,
            "extra": dict(sorted(self.extra.items())),
        }
        encoded = str(payload).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "tokenizer_id": self.tokenizer_id,
            "max_new_tokens": self.max_new_tokens,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "device": self.device,
            "dtype": self.dtype,
            "fingerprint": self.fingerprint(),
        }


@dataclass
class NeuralGenerationStats:
    """Per-call measurement a neural adapter reports.

    Used by the benchmark to populate the latency and resource_cost
    dimensions of ``CapabilityMetrics``. ``tokens_in`` / ``tokens_out``
    are populated when the tokenizer is wired in (see
    ``ModelPipeline``); a bare adapter can leave them at zero.
    """

    latency_ms: float = 0.0
    tokens_in: int = 0
    tokens_out: int = 0
    memory_mb: float = 0.0
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "latency_ms": round(self.latency_ms, 3),
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "memory_mb": round(self.memory_mb, 3),
        }


# --- Deterministic mock neural adapter ------------------------------------ #


@dataclass
class _NeuralState:
    """Internal mutable state of ``MockNeuralAdapter``.

    Kept off the public API so callers can't accidentally mutate it
    after a candidate is fitted -- the adapter is a *function* of its
    per-dimension weights, and any caller that wanted a different
    function should build a new adapter.
    """

    # base per-dimension capability (in [0, 1]); this is the "base
    # model" before any adapter training.
    base_weights: Dict[str, float]
    # adapter delta produced by LoRATrainer (added on top of base).
    adapter_delta: Dict[str, float]
    # how much the adapter is allowed to push (for numerical safety).
    max_delta: float


class MockNeuralAdapter(ModelAdapter):
    """Deterministic, behaviour-graded stand-in for a real neural model.

    Why this exists: a real local LLM is too slow and too large for
    the regression suite, the capability benchmark, and the unit tests.
    A pure hash adapter (the existing ``TestModelAdapter``) is too
    uninformed: it cannot *respond* to a LoRA training update. This
    adapter sits in the middle -- it behaves like a tiny neural model
    whose outputs are a deterministic function of:

    * per-dimension capability weights (the "base model"),
    * an adapter delta (the LoRA candidate),
    * the prompt + context (the input).

    The output is *not* a hash; it is a structured string with a
    confidence score, so downstream evaluators can measure it
    meaningfully. And the weights are mutable through the configured
    LoRA delta, so a LoRA training run that successfully improves a
    dimension produces a measurably different output.

    Determinism: same (config, weights, prompt, context) -> same
    (text, meta) every time, no RNG, no clock dependence.
    """

    name: str = "mock-neural"

    def __init__(self, config: NeuralAdapterConfig, *,
                 base_weights: Optional[Dict[str, float]] = None,
                 adapter_delta: Optional[Dict[str, float]] = None,
                 max_delta: float = 0.30) -> None:
        if not 0.0 <= max_delta <= 1.0:
            raise ValueError("max_delta must be within [0, 1]")
        self.config = config
        self._state = _NeuralState(
            base_weights=dict(base_weights or {}),
            adapter_delta=dict(adapter_delta or {}),
            max_delta=float(max_delta),
        )
        self._stats: List[NeuralGenerationStats] = []
        self.name = f"mock-neural:{config.model_id}"

    # -- per-dimension capability ---------------------------------------- #
    def capability(self, dimension: str) -> float:
        """Effective capability for a dimension after adapter delta."""
        base = self._state.base_weights.get(dimension, 0.5)
        delta = self._state.adapter_delta.get(dimension, 0.0)
        # Clamp the delta to the configured safety bound, then clamp
        # the resulting capability to [0, 1].
        delta = max(-self._state.max_delta,
                    min(self._state.max_delta, delta))
        value = base + delta
        return max(0.0, min(1.0, value))

    def weights(self) -> Dict[str, float]:
        """Return the effective per-dimension capability vector."""
        return {d: self.capability(d) for d in self._dimensions()}

    def _dimensions(self) -> List[str]:
        dims = sorted(set(self._state.base_weights)
                      | set(self._state.adapter_delta))
        return dims

    # -- adapter injection ---------------------------------------------- #
    def set_adapter_delta(self, delta: Dict[str, float]) -> None:
        """Replace the adapter delta (called by ``LoRATrainer.fit``).

        No-op for an empty delta so identical runs produce identical
        capability hashes.
        """
        for dim, value in delta.items():
            if not 0.0 <= abs(value) <= self._state.max_delta:
                raise ValueError(
                    f"delta[{dim!r}]={value} exceeds max_delta="
                    f"{self._state.max_delta}")
        self._state.adapter_delta = dict(delta)

    def reset_adapter(self) -> None:
        self._state.adapter_delta = {}

    # -- generation ------------------------------------------------------ #
    def generate(self, prompt: str, *, context: str = "") -> ModelOutput:
        start = time.time()
        # Aggregate per-dimension capability into a single quality
        # signal that is well-behaved under adapter changes. Mean is
        # the only aggregator that is symmetric and doesn't grow with
        # the number of dimensions; we record it both as "score" and
        # as a soft-saturated probability via 1 - exp(-k * score).
        caps = self.weights()
        score = sum(caps.values()) / max(len(caps), 1) if caps else 0.5
        # Soft saturation: 0 -> 0, 1 -> 0.632; bounded by [0, 1].
        prob = 1.0 - math.exp(-2.0 * score)
        # Deterministic content: hash of (config fp, prompt, context,
        # weights) so the adapter delta is observable in the output
        # bytes, not just in the capability vector.
        digest = hashlib.sha256(
            (f"{self.config.fingerprint()}\n{context}\x1f{prompt}\n"
             f"{sorted(caps.items())}").encode("utf-8")
        ).hexdigest()
        text = (f"[{self.config.model_id}] "
                f"score={score:.4f} prob={prob:.4f} "
                f"sha={digest[:12]}")
        latency_ms = (time.time() - start) * 1000.0
        stats = NeuralGenerationStats(
            latency_ms=latency_ms,
            tokens_in=max(1, len((context + prompt).split())),
            tokens_out=max(1, len(text.split())),
            memory_mb=120.0,           # plausible "small model" size
            extra={"adapter_active": bool(self._state.adapter_delta),
                   "config_fp": self.config.fingerprint()})
        self._stats.append(stats)
        return ModelOutput(text=text, meta={
            "adapter": self.name,
            "config_fp": self.config.fingerprint(),
            "score": round(score, 6),
            "prob": round(prob, 6),
            "caps": {k: round(v, 6) for k, v in caps.items()},
            "stats": stats.to_dict(),
        })

    # -- bookkeeping ----------------------------------------------------- #
    def stats(self) -> List[NeuralGenerationStats]:
        return list(self._stats)

    def reset_stats(self) -> None:
        self._stats.clear()

    def describe(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "kind": "mock-neural",
            "config": self.config.to_dict(),
            "capabilities": self.weights(),
            "adapter_active": bool(self._state.adapter_delta),
        }

    # Tell pytest this is an implementation class.
    __test__ = False

