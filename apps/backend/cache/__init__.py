"""
Cache Module — Redis-backed and in-memory caching with TTL, serialization, and caching decorators.
"""

import os
import json
import time
import pickle
import logging
import threading
from typing import Any, Callable, Dict, Optional, Tuple
from functools import wraps

logger = logging.getLogger("argus.cache")


class CacheBackend:
    """Abstract cache backend."""

    def get(self, key: str) -> Optional[Any]:
        raise NotImplementedError

    def set(self, key: str, value: Any, ttl: int = 300) -> None:
        raise NotImplementedError

    def delete(self, key: str) -> None:
        raise NotImplementedError

    def exists(self, key: str) -> bool:
        raise NotImplementedError

    def clear(self) -> None:
        raise NotImplementedError

    def get_stats(self) -> Dict:
        raise NotImplementedError


class MemoryCache(CacheBackend):
    """Thread-safe in-memory cache with TTL."""

    def __init__(self):
        self._data: Dict[str, Tuple[Any, float]] = {}
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key in self._data:
                value, expiry = self._data[key]
                if expiry > time.time():
                    self._hits += 1
                    return value
                else:
                    del self._data[key]
            self._misses += 1
            return None

    def set(self, key: str, value: Any, ttl: int = 300) -> None:
        with self._lock:
            self._data[key] = (value, time.time() + ttl)

    def delete(self, key: str) -> None:
        with self._lock:
            self._data.pop(key, None)

    def exists(self, key: str) -> bool:
        with self._lock:
            if key in self._data:
                return self._data[key][1] > time.time()
            return False

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    def get_stats(self) -> Dict:
        with self._lock:
            total = self._hits + self._misses
            return {
                "size": len(self._data),
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": self._hits / total if total > 0 else 0,
            }


class RedisCache(CacheBackend):
    """Redis-backed cache."""

    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0, password: Optional[str] = None):
        try:
            import redis
            self._client = redis.Redis(
                host=os.environ.get("REDIS_HOST", host),
                port=int(os.environ.get("REDIS_PORT", port)),
                db=db,
                password=password or os.environ.get("REDIS_PASSWORD"),
                decode_responses=False,
            )
            self._client.ping()
            logger.info("Connected to Redis cache")
        except ImportError:
            logger.warning("Redis not available, falling back to memory cache")
            self._client = None
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            self._client = None

    def get(self, key: str) -> Optional[Any]:
        if not self._client:
            return None
        try:
            data = self._client.get(key)
            if data:
                return pickle.loads(data)
            return None
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None

    def set(self, key: str, value: Any, ttl: int = 300) -> None:
        if not self._client:
            return
        try:
            self._client.setex(key, ttl, pickle.dumps(value))
        except Exception as e:
            logger.error(f"Redis set error: {e}")

    def delete(self, key: str) -> None:
        if self._client:
            try:
                self._client.delete(key)
            except Exception:
                pass

    def exists(self, key: str) -> bool:
        if not self._client:
            return False
        try:
            return bool(self._client.exists(key))
        except Exception:
            return False

    def clear(self) -> None:
        if self._client:
            try:
                self._client.flushdb()
            except Exception:
                pass

    def get_stats(self) -> Dict:
        if not self._client:
            return {"status": "disconnected"}
        try:
            info = self._client.info()
            return {
                "connected_clients": info.get("connected_clients", 0),
                "used_memory": info.get("used_memory_human", "N/A"),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "uptime_days": info.get("uptime_in_days", 0),
            }
        except Exception:
            return {"status": "error"}


class CacheManager:
    """Unified cache manager with automatic fallback."""

    def __init__(self, backend_type: str = "memory"):
        self.backend_type = backend_type
        self._backend: CacheBackend = self._create_backend(backend_type)

    def _create_backend(self, backend_type: str) -> CacheBackend:
        if backend_type == "redis":
            return RedisCache()
        return MemoryCache()

    def get(self, key: str, default: Any = None) -> Any:
        result = self._backend.get(self._normalize_key(key))
        return result if result is not None else default

    def set(self, key: str, value: Any, ttl: int = 300) -> None:
        self._backend.set(self._normalize_key(key), value, ttl)

    def delete(self, key: str) -> None:
        self._backend.delete(self._normalize_key(key))

    def exists(self, key: str) -> bool:
        return self._backend.exists(self._normalize_key(key))

    def clear(self) -> None:
        self._backend.clear()

    def get_or_set(self, key: str, fn: Callable, ttl: int = 300) -> Any:
        cached = self.get(key)
        if cached is not None:
            return cached
        value = fn()
        self.set(key, value, ttl)
        return value

    def _normalize_key(self, key: str) -> str:
        return f"argus:{key}"

    def get_stats(self) -> Dict:
        return {"backend": self.backend_type, **self._backend.get_stats()}


def cached(ttl: int = 300, prefix: str = ""):
    """Decorator to cache function results."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = getattr(wrapper, "_cache", None)
            if cache is None:
                cache = CacheManager()
                wrapper._cache = cache
            key = f"{prefix}:{func.__name__}:{str(args)}:{str(kwargs)}"
            return cache.get_or_set(key, lambda: func(*args, **kwargs), ttl)
        return wrapper
    return decorator
