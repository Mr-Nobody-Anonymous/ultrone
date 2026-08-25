"""Performance tests for the ULTRONE runtime subsystem.

Tests must pass on CPU-only machines. GPU tests skip cleanly when unavailable.
"""

import os
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from runtime import (
    BackendManager,
    ChangeDetector,
    DecisionCache,
    FastSlowPolicy,
    InferenceScheduler,
    LRUCache,
    MemoryMonitor,
    ModelCache,
    ModelRuntime,
    ModelState,
    PolicyConfig,
    Priority,
    Runtime,
    RuntimeConfig,
    benchmark_hardware,
    detect_backends,
    detect_capabilities,
)


# ---------------------------------------------------------------------------
# Device detection
# ---------------------------------------------------------------------------
def test_device_detection_works_on_cpu():
    runtime = Runtime(RuntimeConfig(device="auto"))
    assert runtime.get_backend() in {"cpu", "cuda", "rocm", "mps", "other"}
    assert runtime.get_device() in {"cpu", "cuda", "rocm", "mps"}
    assert runtime.get_device_info()["device_type"] in {"cpu", "cuda", "rocm", "mps"}


def test_backend_detection_never_crashes():
    backends = detect_backends()
    assert "cpu" in backends
    assert backends["cpu"].available is True
    # All backends should have a reason
    for name, info in backends.items():
        assert info.reason, f"Backend {name} missing reason"


def test_capabilities_detection():
    caps = detect_capabilities()
    assert caps.device_type in {"cpu", "cuda", "rocm", "mps"}
    assert caps.cpu_count >= 1
    assert caps.ram_bytes >= 0


def test_backend_manager_selects_cpu_fallback():
    manager = BackendManager()
    selected = manager.select(preferred="cuda")
    # Should fall back to CPU if CUDA unavailable
    assert selected.available is True
    assert manager.preferred in {"cuda", "rocm", "mps", "cpu"}


# ---------------------------------------------------------------------------
# Model cache / lifecycle
# ---------------------------------------------------------------------------
def test_model_cache_tracks_lifecycle():
    cache = ModelCache(max_size=4)
    cache.set_state("model-a", ModelState.LOADING.value)
    assert cache.get_state("model-a") == ModelState.LOADING.value
    cache.set_state("model-a", ModelState.READY.value)
    assert cache.get_state("model-a") == ModelState.READY.value


def test_model_cache_evicts_oldest():
    cache = ModelCache(max_size=2)
    cache.put("a", object())
    cache.put("b", object())
    cache.put("c", object())
    # Should have evicted "a" (oldest)
    assert cache.get("a") is None
    assert cache.get("b") is not None
    assert cache.get("c") is not None


def test_model_cache_offloads_to_cpu_on_eviction():
    cache = ModelCache(max_size=1)
    model = DummyTorchModel()
    cache.put("m1", model)
    cache.put("m2", DummyTorchModel())
    # m1 should be evicted and moved to CPU
    assert cache.get("m1") is None
    assert model.device == "cpu"


class DummyTorchModel:
    def __init__(self):
        self.device = "cuda"

    def to(self, device):
        self.device = device
        return self


# ---------------------------------------------------------------------------
# LRU cache
# ---------------------------------------------------------------------------
def test_lru_cache_basic():
    cache = LRUCache(max_size=3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    assert cache.get("a") == 1
    assert cache.get("b") == 2
    assert cache.get("c") == 3
    assert len(cache) == 3


def test_lru_cache_evicts_oldest():
    cache = LRUCache(max_size=2)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    assert cache.get("a") is None
    assert cache.get("b") == 2
    assert cache.get("c") == 3


def test_lru_cache_ttl():
    cache = LRUCache(max_size=10, ttl_seconds=0.01)
    cache.put("a", 1)
    time.sleep(0.02)
    assert cache.get("a") is None


def test_lru_cache_stats():
    cache = LRUCache(max_size=10)
    cache.put("a", 1)
    cache.get("a")
    cache.get("missing")
    stats = cache.stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1
    assert stats["hit_rate"] == 0.5


# ---------------------------------------------------------------------------
# Inference scheduler
# ---------------------------------------------------------------------------
def test_inference_scheduler_priority():
    scheduler = InferenceScheduler()
    results = []

    def make_task(value):
        def task():
            results.append(value)
            return value
        return task

    scheduler.submit(make_task("low"), priority=Priority.LOW.value)
    scheduler.submit(make_task("critical"), priority=Priority.CRITICAL.value)
    scheduler.submit(make_task("normal"), priority=Priority.NORMAL.value)

    # Process all - critical should be first
    scheduler.process_next()
    scheduler.process_next()
    scheduler.process_next()

    assert results[0] == "critical"
    assert results[1] == "normal"
    assert results[2] == "low"


def test_inference_scheduler_cancellation():
    scheduler = InferenceScheduler()
    task = scheduler.submit(lambda: 42, priority=Priority.NORMAL.value)
    assert scheduler.cancel(task) is True
    assert scheduler.queue_size() == 0
    assert scheduler.total_cancelled == 1


def test_inference_scheduler_backpressure():
    scheduler = InferenceScheduler(max_queue_size=2)
    scheduler.submit(lambda: 1)
    scheduler.submit(lambda: 2)
    with pytest.raises(RuntimeError):
        scheduler.submit(lambda: 3)


# ---------------------------------------------------------------------------
# Fast/slow path policy
# ---------------------------------------------------------------------------
def test_fast_slow_policy_uses_fast_path():
    fast_calls = []
    slow_calls = []

    def fast_policy(obs):
        fast_calls.append(obs)
        return "fast-action"

    def slow_policy(obs):
        slow_calls.append(obs)
        return "slow-action"

    policy = FastSlowPolicy(fast_policy, slow_policy, PolicyConfig(reasoning_interval=100))
    action, path = policy.decide({"state": "stable"})
    assert path == "fast"
    assert action == "fast-action"
    assert len(fast_calls) == 1
    assert len(slow_calls) == 0


def test_fast_slow_policy_uses_slow_path_on_change():
    fast_calls = []
    slow_calls = []

    def fast_policy(obs):
        fast_calls.append(obs)
        return "fast-action"

    def slow_policy(obs):
        slow_calls.append(obs)
        return "slow-action"

    policy = FastSlowPolicy(fast_policy, slow_policy, PolicyConfig(reasoning_interval=100))
    # First call establishes baseline (fast path since nothing to compare)
    action, path = policy.decide({"state": "a"})
    assert path == "fast"

    # Second call with changed state should trigger slow path
    action, path = policy.decide({"state": "b"})
    assert path == "slow"
    assert action == "slow-action"
    assert len(slow_calls) == 1


def test_fast_slow_policy_caches_reasoning():
    slow_calls = []

    def fast_policy(obs):
        return "fast-action"

    def slow_policy(obs):
        slow_calls.append(obs)
        return "slow-action"

    policy = FastSlowPolicy(fast_policy, slow_policy, PolicyConfig(reasoning_interval=100))
    # First call establishes baseline (fast path)
    policy.decide({"state": "a"})

    # Second call with changed state triggers slow path
    action, path = policy.decide({"state": "b"})
    assert path == "slow"
    assert len(slow_calls) == 1

    # Third call with same state should hit cache
    action, path = policy.decide({"state": "b"})
    assert path == "cached"
    assert len(slow_calls) == 1


def test_change_detector():
    detector = ChangeDetector()
    changed, _ = detector.detect_change({"a": 1})
    assert changed is True  # First call always "changed"
    changed, _ = detector.detect_change({"a": 1})
    assert changed is False  # Same state
    changed, _ = detector.detect_change({"a": 2})
    assert changed is True  # Different state


def test_decision_cache():
    cache = DecisionCache(max_size=10, ttl_seconds=60)
    cache.put("key1", "value1")
    assert cache.get("key1") == "value1"
    assert cache.get("missing") is None
    stats = cache.stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1


# ---------------------------------------------------------------------------
# Memory monitor
# ---------------------------------------------------------------------------
def test_memory_monitor_works():
    monitor = MemoryMonitor()
    stats = monitor.get_stats()
    assert "ram_available" in stats
    assert "ram_total" in stats
    assert "vram_available" in stats


# ---------------------------------------------------------------------------
# Runtime integration
# ---------------------------------------------------------------------------
def test_runtime_embedding_cache():
    runtime = Runtime(RuntimeConfig(enable_embedding_cache=True))
    runtime.cache_embedding("test-key", [1.0, 2.0, 3.0])
    assert runtime.get_cached_embedding("test-key") == [1.0, 2.0, 3.0]


def test_runtime_reasoning_cache():
    runtime = Runtime(RuntimeConfig(enable_reasoning_cache=True))
    runtime.cache_reasoning("test-key", {"result": "value"})
    assert runtime.get_cached_reasoning("test-key") == {"result": "value"}
    runtime.invalidate_reasoning_cache()
    assert runtime.get_cached_reasoning("test-key") is None


def test_runtime_reasoning_hash():
    runtime = Runtime()
    h1 = runtime.reasoning_hash("state", "goal", "config")
    h2 = runtime.reasoning_hash("state", "goal", "config")
    h3 = runtime.reasoning_hash("different", "goal", "config")
    assert h1 == h2
    assert h1 != h3


def test_runtime_model_lifecycle():
    runtime = Runtime(RuntimeConfig(max_cached_models=4))
    model_runtime = ModelRuntime(runtime)

    model = DummyCallableModel()
    model_runtime.load("test-model", model)
    assert model_runtime.get_state("test-model") in {ModelState.READY.value, ModelState.WARM.value}

    # Reuse cached model
    result = model_runtime.generate("test-model", [1, 2, 3])
    assert result is not None

    # Unload
    model_runtime.unload("test-model")
    assert model_runtime.get_state("test-model") == ModelState.EVICTED.value


class DummyCallableModel:
    def __call__(self, inputs):
        return [1.0, 2.0, 3.0]


def test_benchmark_hardware_report_enhanced():
    report = benchmark_hardware(RuntimeConfig(device="auto"))
    assert report["backend"]
    assert report["device"]
    assert report["precision"]
    assert "backend_info" in report
    assert "capabilities" in report
    assert "memory_stats" in report
    assert "matmul_latency_ms" in report
    assert "cpu_count" in report
    assert "ram_bytes" in report


# ---------------------------------------------------------------------------
# GPU tests (skip cleanly when unavailable)
# ---------------------------------------------------------------------------
def _torch_cuda_available() -> bool:
    try:
        import torch
        return bool(torch.cuda.is_available())
    except ImportError:
        return False


def _torch_mps_available() -> bool:
    try:
        import torch
        return bool(
            hasattr(torch.backends, "mps")
            and torch.backends.mps.is_available()
        )
    except ImportError:
        return False


@pytest.mark.skipif(not _torch_cuda_available(), reason="CUDA not available")
def test_cuda_detection_when_available():
    runtime = Runtime(RuntimeConfig(device="auto"))
    if runtime.is_cuda_available():
        assert runtime.get_device() == "cuda"
        assert runtime.supports_float16() is True


@pytest.mark.skipif(not _torch_mps_available(), reason="MPS not available")
def test_mps_detection_when_available():
    runtime = Runtime(RuntimeConfig(device="auto"))
    if runtime.is_mps_available():
        assert runtime.get_device() == "mps"
