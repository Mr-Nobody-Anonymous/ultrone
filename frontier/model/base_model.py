# Copyright (c) Ultrone Contributors. All rights reserved.
"""Base model interface for frontier models.

Defines the unified interface that all frontier models must implement,
along with adapters for HuggingFace Transformers, vLLM, llama.cpp, and
other production backends.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple


class BaseModel(abc.ABC):
    """Abstract base class for all frontier models.

    Provides the unified interface used by the reasoning stack, benchmark
    harness, and inference engine. All models must implement ``generate``
    and ``get_stats``.
    """

    def __init__(self, model_id: str = "base"):
        self.model_id = model_id
        self._generation_calls = 0
        self._total_tokens = 0

    @abc.abstractmethod
    def generate(self, prompt: str, **kwargs: Any) -> str:
        """Generate a response for a prompt.

        Parameters
        ----------
        prompt : str
            The input prompt.
        **kwargs
            Generation parameters (max_tokens, temperature, etc.).

        Returns
        -------
        str
            The generated response.
        """
        ...

    @abc.abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Return model statistics."""
        ...

    # ------------------------------------------------------------------
    # Solver protocol compatibility (for frontier.reasoning)
    # ------------------------------------------------------------------
    def __call__(self, prompt: str, **kwargs: Any) -> str:
        """Make the model callable as a solver."""
        self._generation_calls += 1
        output = self.generate(prompt, **kwargs)
        self._total_tokens += len(output.split())
        return output

    # ------------------------------------------------------------------
    # Common helpers
    # ------------------------------------------------------------------
    def get_model_id(self) -> str:
        """Return the model identifier."""
        return self.model_id

    def _base_stats(self) -> Dict[str, Any]:
        """Return common statistics."""
        return {
            "model_id": self.model_id,
            "type": type(self).__name__,
            "generation_calls": self._generation_calls,
            "total_tokens": self._total_tokens,
        }


class RuleBasedModel(BaseModel):
    """A simple rule-based model for testing and fallback.

    Implements a real (but simple) model: extracts the most informative
    chunk of the prompt. Used for benchmarking the harness without an LLM.
    """

    def __init__(self, model_id: str = "rule-based"):
        super().__init__(model_id)

    def generate(self, prompt: str, **kwargs: Any) -> str:
        """Generate a response using rule-based heuristics.

        Extracts the "Answer:" section from the prompt if present, otherwise
        returns a keyword-based summary.
        """
        max_tokens = kwargs.get("max_tokens", 50)
        # Look for "Answer:" section
        if "Answer:" in prompt:
            answer = prompt.split("Answer:", 1)[1].strip()
            words = answer.split()[:max_tokens]
            return " ".join(words)

        # Keyword-based summary: return key phrases from the prompt
        words = prompt.split()[:max_tokens]
        return " ".join(words)

    def get_stats(self) -> Dict[str, Any]:
        """Return model statistics."""
        stats = self._base_stats()
        stats["description"] = "Rule-based model for testing"
        return stats


class MockModel(BaseModel):
    """A mock model that returns predetermined responses.

    Used for testing the reasoning stack and benchmark harness where a
    deterministic response is needed.
    """

    def __init__(
        self,
        responses: Optional[Dict[str, str]] = None,
        default_response: str = "Mock response",
        model_id: str = "mock",
    ):
        super().__init__(model_id)
        self.responses = responses or {}
        self.default_response = default_response

    def generate(self, prompt: str, **kwargs: Any) -> str:
        """Return a predetermined response."""
        return self.responses.get(prompt, self.default_response)

    def get_stats(self) -> Dict[str, Any]:
        """Return model statistics."""
        stats = self._base_stats()
        stats["responses"] = len(self.responses)
        return stats


class HuggingFaceModel(BaseModel):
    """Adapter for HuggingFace Transformers models.

    Wraps ``transformers.AutoModelForCausalLM`` and ``AutoTokenizer`` to
    provide real pretrained LLM inference through the unified interface.
    """

    def __init__(
        self,
        model_name: str,
        model_id: Optional[str] = None,
        device: Optional[str] = None,
        torch_dtype: Optional[str] = None,
    ):
        super().__init__(model_id or model_name)
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer

            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                device_map="auto" if device is None else device,
                torch_dtype=torch_dtype,
            )
        except ImportError as exc:
            raise ImportError(
                "HuggingFaceModel requires 'transformers' installed"
            ) from exc
        self.model_name = model_name

    def generate(self, prompt: str, **kwargs: Any) -> str:
        """Generate using the HuggingFace model."""
        import torch

        inputs = self.tokenizer(prompt, return_tensors="pt")
        max_new_tokens = kwargs.get("max_tokens", kwargs.get("max_new_tokens", 50))
        temperature = kwargs.get("temperature", 1.0)
        do_sample = kwargs.get("do_sample", temperature != 1.0)

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature if do_sample else None,
                do_sample=do_sample,
                pad_token_id=self.tokenizer.eos_token_id,
            )
        return self.tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)

    def get_stats(self) -> Dict[str, Any]:
        """Return model statistics."""
        stats = self._base_stats()
        stats["model_name"] = self.model_name
        stats["parameters"] = sum(p.numel() for p in self.model.parameters())
        return stats


class VLLMModel(BaseModel):
    """Adapter for vLLM.

    Wraps ``vllm.LLM`` for high-throughput inference.
    """

    def __init__(self, model_name: str, model_id: Optional[str] = None, **llm_kwargs: Any):
        super().__init__(model_id or model_name)
        try:
            from vllm import LLM, SamplingParams
        except ImportError as exc:
            raise ImportError("VLLMModel requires 'vllm' installed") from exc
        self._LLM = LLM
        self._SamplingParams = SamplingParams
        self.llm = LLM(model=model_name, **llm_kwargs)
        self.model_name = model_name

    def generate(self, prompt: str, **kwargs: Any) -> str:
        """Generate using vLLM."""
        sampling_params = self._SamplingParams(
            max_tokens=kwargs.get("max_tokens", 50),
            temperature=kwargs.get("temperature", 1.0),
            top_k=kwargs.get("top_k", -1),
            top_p=kwargs.get("top_p", 1.0),
        )
        outputs = self.llm.generate([prompt], sampling_params)
        return outputs[0].outputs[0].text

    def get_stats(self) -> Dict[str, Any]:
        """Return model statistics."""
        stats = self._base_stats()
        stats["model_name"] = self.model_name
        stats["engine"] = "vllm"
        return stats


class LlamaCppModel(BaseModel):
    """Adapter for llama.cpp.

    Wraps ``llama_cpp.Llama`` for local GGUF model inference.
    """

    def __init__(self, model_path: str, model_id: Optional[str] = None, **llama_kwargs: Any):
        super().__init__(model_id or model_path)
        try:
            from llama_cpp import Llama
        except ImportError as exc:
            raise ImportError("LlamaCppModel requires 'llama-cpp-python' installed") from exc
        self._Llama = Llama
        self.llm = Llama(model_path=model_path, **llama_kwargs)
        self.model_path = model_path

    def generate(self, prompt: str, **kwargs: Any) -> str:
        """Generate using llama.cpp."""
        output = self.llm(
            prompt,
            max_tokens=kwargs.get("max_tokens", 50),
            temperature=kwargs.get("temperature", 1.0),
            top_k=kwargs.get("top_k", 40),
            top_p=kwargs.get("top_p", 0.95),
            echo=False,
        )
        return output["choices"][0]["text"]

    def get_stats(self) -> Dict[str, Any]:
        """Return model statistics."""
        stats = self._base_stats()
        stats["model_path"] = self.model_path
        stats["engine"] = "llama.cpp"
        return stats


def create_model(
    backend: str,
    model_name: Optional[str] = None,
    model_path: Optional[str] = None,
    model_id: Optional[str] = None,
    **kwargs: Any,
) -> BaseModel:
    """Create a model by backend name.

    Parameters
    ----------
    backend : str
        One of "rule", "mock", "huggingface", "vllm", "llamacpp".
    model_name : Optional[str]
        Model name for HuggingFace/vLLM.
    model_path : Optional[str]
        Model path for llama.cpp.
    model_id : Optional[str]
        Custom model ID.

    Returns
    -------
    BaseModel
        The created model.
    """
    backend = backend.lower()
    if backend in ("rule", "rules", "rule-based"):
        return RuleBasedModel(model_id=model_id or "rule-based")
    if backend in ("mock", "mock-model"):
        return MockModel(model_id=model_id or "mock")
    if backend in ("huggingface", "hf", "transformers"):
        if model_name is None:
            raise ValueError("model_name required for huggingface backend")
        return HuggingFaceModel(model_name, model_id=model_id, **kwargs)
    if backend in ("vllm", "vllm-engine"):
        if model_name is None:
            raise ValueError("model_name required for vllm backend")
        return VLLMModel(model_name, model_id=model_id, **kwargs)
    if backend in ("llamacpp", "llama.cpp", "gguf"):
        if model_path is None:
            raise ValueError("model_path required for llamacpp backend")
        return LlamaCppModel(model_path, model_id=model_id, **kwargs)
    raise ValueError(f"Unknown model backend: {backend}")