from __future__ import annotations

"""Memory management — bounded caches, VRAM/RAM awareness, and eviction policies."""

import logging
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional, Tuple

logger = logging.getLogger("Ultrone.Runtime.Memory")


class LRUCache:
    """Thread-safe LRU cache with optional TTL and max size."""

    def __init__(self, max_size: int = 128, ttl_seconds: Optional[float] = None) -> None:
        self.max_size = max(1, max_size)
        self.ttl_seconds = ttl_seconds
        self._cache: "OrderedDict[str, Tuple[Any, float]]" = OrderedDict()
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0
        self.evictions = 0

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            item = self._cache.get(key)
            if item is None:
                self.misses += 1
                return None
            value, timestamp = item
            if self.ttl_seconds is not None and (time.time() - timestamp) > self.ttl_seconds:
                self._cache.pop(key, None)
                self.evictions += 1
                self.misses += 1
                return None
            self._cache.move_to_end(key)
            self.hits += 1
            return value

    def put(self, key: str, value: Any) -> None:
        with self._lock:
            self._cache[key] = (value, time.time())
            self._cache.move_to_end(key)
            while len(self._cache) > self.max_size:
                oldest_key, _ = self._cache.popitem(last=False)
                self.evictions += 1

    def remove(self, key: str) -> None:
        with self._lock:
            self._cache.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
            self.evictions += 1

    def __len__(self) -> int:
        with self._lock:
            return len(self._cache)

    def keys(self) -> list:
        with self._lock:
            return list(self._cache.keys())

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "hits": self.hits,
                "misses": self.misses,
                "evictions": self.evictions,
                "hit_rate": self.hits / max(1, self.hits + self.misses),
            }


class MemoryMonitor:
    """Monitor RAM/VRAM usage and provide memory-aware decisions."""

    def __init__(self) -> None:
        self._torch = None
        self._psutil = None
        try:
            import psutil  # type: ignore

            self._psutil = psutil
        except ImportError:
            self._psutil = None

    def available_ram(self) -> int:
        """Available RAM in bytes, or 0 if unknown."""
        if self._psutil is not None:
            return int(self._psutil.virtual_memory().available)
        return 0

    def total_ram(self) -> int:
        """Total RAM in bytes, or 0 if unknown."""
        if self._psutil is not None:
            return int(self._psutil.virtual_memory().total)
        return 0

    def available_vram(self) -> int:
        """Available VRAM in bytes, or 0 if no GPU or unknown."""
        torch = self._get_torch()
        if torch is None:
            return 0
        try:
            if torch.cuda.is_available():
                return int(torch.cuda.mem_get_info()[0])
        except Exception:
            pass
        return 0

    def reserved_vram(self) -> int:
        """Reserved VRAM in bytes, or 0 if no GPU or unknown."""
        torch = self._get_torch()
        if torch is None:
            return 0
        try:
            if torch.cuda.is_available():
                return int(torch.cuda.memory_reserved())
        except Exception:
            pass
        return 0

    def allocated_vram(self) -> int:
        """Allocated VRAM in bytes, or 0 if no GPU or unknown."""
        torch = self._get_torch()
        if torch is None:
            return 0
        try:
            if torch.cuda.is_available():
                return int(torch.cuda.memory_allocated())
        except Exception:
            pass
        return 0

    def peak_vram(self) -> int:
        """Peak VRAM usage in bytes, or 0 if no GPU or unknown."""
        torch = self._get_torch()
        if torch is None:
            return 0
        try:
            if torch.cuda.is_available():
                return int(torch.cuda.max_memory_allocated())
        except Exception:
            pass
        return 0

    def _get_torch(self):
        if self._torch is None:
            try:
                import torch  # type: ignore

                self._torch = torch
            except ImportError:
                self._torch = False
        return self._torch if self._torch is not False else None

    def get_stats(self) -> Dict[str, Any]:
        return {
            "ram_available": self.available_ram(),
            "ram_total": self.total_ram(),
            "vram_available": self.available_vram(),
            "vram_reserved": self.reserved_vram(),
            "vram_allocated": self.allocated_vram(),
            "vram_peak": self.peak_vram(),
        }


class ModelEvictionManager:
    """Evicts cached models under memory pressure using LRU policy."""

    def __init__(
        self,
        model_cache: Any,
        monitor: Optional[MemoryMonitor] = None,
        max_models: int = 8,
        memory_threshold: float = 0.9,
    ) -> None:
        self.model_cache = model_cache
        self.monitor = monitor or MemoryMonitor()
        self.max_models = max(1, max_models)
        self.memory_threshold = memory_threshold
        self._access_order: list = []
        self._evicted: list = []

    def touch(self, model_id: str) -> None:
        """Record a model access for LRU ordering."""
        if model_id in self._access_order:
            self._access_order.remove(model_id)
        self._access_order.append(model_id)

    def check_pressure(self) -> bool:
        """Check if memory pressure requires eviction."""
        vram_avail = self.monitor.available_vram()
        if vram_avail > 0:
            # Check VRAM pressure if available
            ram_total = self.monitor.total_ram()
            if ram_total > 0:
                # Heuristic: if VRAM is very low, evict
                if vram_avail < ram_total * 0.05:
                    return True
        return False

    def evict_if_needed(self) -> int:
        """Evict models if over limits or under memory pressure. Returns evicted count."""
        evicted = 0
        cached = list(self.model_cache._models.keys()) if hasattr(self.model_cache, "_models") else []
        while len(cached) > self.max_models:
            # Evict oldest accessed
            for mid in list(self._access_order):
                if mid in cached:
                    self.model_cache.remove(mid)
                    self._evicted.append(mid)
                    self._access_order.remove(mid)
                    evicted += 1
                    cached = list(self.model_cache._models.keys())
                    break
            else:
                break
        if self.check_pressure():
            # Evict least-recently-used model
            for mid in list(self._access_order):
                if mid in cached:
                    self.model_cache.remove(mid)
                    self._evicted.append(mid)
                    self._access_order.remove(mid)
                    evicted += 1
                    break
        return evicted

    def stats(self) -> Dict[str, Any]:
        return {
            "max_models": self.max_models,
            "evicted_count": len(self._evicted),
            "recently_evicted": self._evicted[-10:],
        }