from __future__ import annotations

"""Fast path / slow path decision architecture with change detection and reasoning scheduling.

Implements the core optimization pattern:
    Observation → Change Detector → Fast Policy → confidence sufficient?
        ├── YES → Action (fast path)
        └── NO → Deep Reasoning (slow path) → Action

Also implements reasoning scheduling so heavyweight LLM/planner calls happen
only on significant state changes or scheduled intervals, not every tick.
"""

import hashlib
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("Ultrone.Runtime.Policy")


@dataclass
class PolicyConfig:
    """Configuration for the fast/slow path decision system."""

    reasoning_interval: int = 5  # Run deep reasoning every N ticks
    change_threshold: float = 0.15  # Fraction of state that must change to trigger deep path
    enable_reasoning_cache: bool = True
    cache_ttl_seconds: float = 60.0
    max_cached_decisions: int = 256
    fast_path_timeout_ms: float = 5.0
    slow_path_timeout_ms: float = 2000.0


class ChangeDetector:
    """Detects significant changes between consecutive observations."""

    def __init__(self, threshold: float = 0.15) -> None:
        self.threshold = threshold
        self._last_hash: Optional[str] = None

    def detect_change(self, state: Any) -> Tuple[bool, float]:
        """Compare state to the last seen state. Returns (changed, change_ratio)."""
        state_hash = self._hash_state(state)
        if self._last_hash is None:
            self._last_hash = state_hash
            return True, 0.0
        changed = state_hash != self._last_hash
        # A different hash means state changed; compute heuristic ratio
        ratio = 1.0 if changed else 0.0
        self._last_hash = state_hash
        return changed, ratio

    def reset(self) -> None:
        self._last_hash = None

    @staticmethod
    def _hash_state(state: Any) -> str:
        """Stable hash of a state object for change detection."""
        if isinstance(state, dict):
            # Only hash top-level keys/values for efficiency
            items = []
            for k, v in state.items():
                if isinstance(v, (str, int, float, bool, tuple)):
                    items.append((str(k), str(v)))
                elif isinstance(v, dict):
                    # Hash nested dicts just by keys and scalar values
                    items.append(
                        (
                            str(k),
                            ChangeDetector._hash_state(v),
                        )
                    )
            items.sort(key=lambda x: x[0])
            return hashlib.sha256(repr(items).encode("utf-8", errors="ignore")).hexdigest()[:16]
        try:
            return hashlib.sha256(str(state).encode("utf-8", errors="ignore")).hexdigest()[:16]
        except Exception:
            return str(id(state))


class ReasoningScheduler:
    """Schedules heavy reasoning to run only when needed."""

    def __init__(self, config: PolicyConfig) -> None:
        self.config = config
        self._tick: int = 0
        self._last_reasoning_tick: int = 0

    def should_reason(self, *, state_changed: bool = False) -> bool:
        """Decide whether to invoke the slow path this tick."""
        if state_changed:
            return True
        self._tick += 1
        if self._tick - self._last_reasoning_tick >= self.config.reasoning_interval:
            self._last_reasoning_tick = self._tick
            return True
        return False

    def mark_reasoned(self) -> None:
        self._last_reasoning_tick = self._tick

    def reset(self) -> None:
        self._tick = 0
        self._last_reasoning_tick = 0


class DecisionCache:
    """Caches expensive reasoning results keyed by state+goal+config."""

    def __init__(self, max_size: int = 256, ttl_seconds: float = 60.0) -> None:
        self.max_size = max(1, max_size)
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            item = self._cache.get(key)
            if item is None:
                self.misses += 1
                return None
            value, timestamp = item
            if time.time() - timestamp > self.ttl_seconds:
                self._cache.pop(key, None)
                self.misses += 1
                return None
            self.hits += 1
            return value

    def put(self, key: str, value: Any) -> None:
        with self._lock:
            self._cache[key] = (value, time.time())
            while len(self._cache) > self.max_size:
                # Remove oldest entry
                oldest_key = min(self._cache, key=lambda k: self._cache[k][1])
                self._cache.pop(oldest_key, None)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    def stats(self) -> Dict[str, Any]:
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": self.hits / max(1, self.hits + self.misses),
        }


class FastSlowPolicy:
    """Policy that uses a fast path for routine decisions and a slow path for hard ones."""

    def __init__(
        self,
        fast_policy: Callable[[Any], Any],
        slow_policy: Callable[[Any], Any],
        config: Optional[PolicyConfig] = None,
    ):
        self.fast_policy = fast_policy
        self.slow_policy = slow_policy
        self.config = config or PolicyConfig()
        self.change_detector = ChangeDetector(threshold=self.config.change_threshold)
        self.scheduler = ReasoningScheduler(self.config)
        self.cache: Optional[DecisionCache] = None
        if self.config.enable_reasoning_cache:
            self.cache = DecisionCache(
                max_size=self.config.max_cached_decisions,
                ttl_seconds=self.config.cache_ttl_seconds,
            )
        self.stats = {
            "fast_path_calls": 0,
            "slow_path_calls": 0,
            "cache_hits": 0,
            "cache_misses": 0,
        }
        self._is_initial = True

    def decide(
        self,
        observation: Any,
        *,
        goal: Optional[Any] = None,
        force_reason: bool = False,
    ) -> Tuple[Any, str]:
        """Make a decision using the fast path, falling back to slow path when needed.

        Returns
        -------
        (action, path_used)
            path_used is either "fast", "slow", or "cached".
        """
        state_changed, _ = self.change_detector.detect_change(observation)
        is_initial = self._is_initial
        self._is_initial = False

        # Check reasoning cache first
        if self.cache is not None:
            cache_key = self._cache_key(observation, goal)
            cached = self.cache.get(cache_key)
            if cached is not None:
                self.stats["cache_hits"] += 1
                return cached, "cached"

        # Fast path: cheap deterministic policy
        start = time.perf_counter()
        try:
            action = self.fast_policy(observation)
            elapsed_ms = (time.perf_counter() - start) * 1000

            # Fast path is sufficient if:
            # - This is the first call (nothing to compare against), OR
            # - State hasn't changed, AND fast policy is fast, AND no forced reasoning
            if not force_reason and (is_initial or not state_changed) and elapsed_ms < self.config.fast_path_timeout_ms:
                self.stats["fast_path_calls"] += 1
                if self.cache is not None:
                    self.cache.put(self._cache_key(observation, goal), action)
                return action, "fast"

            # Check if scheduled reasoning is needed
            if self.scheduler.should_reason(state_changed=state_changed) or force_reason:
                self.scheduler.mark_reasoned()
                self.stats["slow_path_calls"] += 1
                action = self.slow_policy(observation)
                if self.cache is not None:
                    self.cache.put(self._cache_key(observation, goal), action)
                return action, "slow"

            # Fast path result is acceptable
            self.stats["fast_path_calls"] += 1
            if self.cache is not None:
                self.cache.put(self._cache_key(observation, goal), action)
            return action, "fast"
        except Exception as e:
            logger.warning("Fast path failed (%s), using slow path", e)
            self.stats["slow_path_calls"] += 1
            action = self.slow_policy(observation)
            if self.cache is not None:
                self.cache.put(self._cache_key(observation, goal), action)
            return action, "slow"

    def reset(self) -> None:
        self.change_detector.reset()
        self.scheduler.reset()
        if self.cache is not None:
            self.cache.clear()

    def _cache_key(self, observation: Any, goal: Optional[Any]) -> str:
        """Build a stable cache key from observation, goal, and policy config."""
        h = hashlib.sha256()
        h.update(ChangeDetector._hash_state(observation).encode("utf-8"))
        if goal is not None:
            h.update(str(goal).encode("utf-8", errors="ignore"))
        return h.hexdigest()[:32]

    def get_stats(self) -> Dict[str, Any]:
        stats = dict(self.stats)
        if self.cache is not None:
            stats["cache"] = self.cache.stats()
        return stats