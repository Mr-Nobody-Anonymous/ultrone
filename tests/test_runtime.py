import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from frontier.model.inference_engine import InferenceEngine, InferenceRequest
from frontier.model.model_config import ModelConfig
from runtime import ModelCache, ModelRuntime, Runtime, RuntimeConfig, batch_inference, benchmark_hardware


class DummyTokenizer:
    def encode(self, text):
        return [ord(ch) for ch in text]

    def decode(self, ids):
        return "".join(chr(i) for i in ids)


class DummyModel:
    def __init__(self):
        self.calls = 0

    def __call__(self, input_ids):
        self.calls += 1
        return [[1.0, 0.0, 0.0]]


def test_runtime_detects_cpu_fallback():
    runtime = Runtime(RuntimeConfig(device="auto"))
    assert runtime.get_backend() in {"cpu", "cuda", "rocm", "mps", "other"}
    assert runtime.get_device() in {"cpu", "cuda", "rocm", "mps"}


def test_model_cache_reuses_cached_models():
    cache = ModelCache()
    loader_calls = []

    def loader():
        loader_calls.append("loaded")
        return object()

    first = cache.get_or_load("model-a", loader)
    second = cache.get_or_load("model-a", loader)
    assert first is second
    assert loader_calls == ["loaded"]


def test_batch_inference_supports_micro_batches():
    outputs = batch_inference(lambda value: value * 2, [1, 2, 3], batch_size=2)
    assert outputs == [2, 4, 6]


def test_inference_engine_uses_runtime_and_produces_output():
    engine = InferenceEngine(DummyModel(), DummyTokenizer(), ModelConfig())
    result = engine.generate(InferenceRequest(prompt="abc", max_new_tokens=1))
    assert isinstance(result.text, str)
    assert result.num_tokens >= 0
    assert engine.get_stats()["runtime_backend"]


def test_benchmark_hardware_report():
    report = benchmark_hardware(RuntimeConfig(device="auto"))
    assert report["backend"]
    assert report["device"]
    assert report["precision"]
