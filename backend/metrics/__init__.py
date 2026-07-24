"""Metrics Collector — Prometheus, system monitoring, GPU/CPU/RAM tracking, and health checks."""

import os
import time
import psutil
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("argus.metrics")


@dataclass
class MetricPoint:
    name: str
    value: float
    labels: Dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class MetricsCollector:
    """Collects system and application metrics with Prometheus export support."""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self._metrics: Dict[str, List[MetricPoint]] = {}
        self._lock = threading.RLock()
        self._running = False
        self._collector_thread: Optional[threading.Thread] = None
        self._prometheus_registry = None
        self._gauges: Dict[str, Any] = {}
        self._callbacks: List[Callable] = []
        self._init_prometheus()

    def _init_prometheus(self) -> None:
        try:
            from prometheus_client import Counter, Gauge, Histogram, CollectorRegistry
            self._prometheus_registry = CollectorRegistry()
            self._gauges = {
                "cpu_usage": Gauge("argus_cpu_usage", "CPU usage percent", registry=self._prometheus_registry),
                "memory_usage": Gauge("argus_memory_usage", "Memory usage percent", registry=self._prometheus_registry),
                "gpu_usage": Gauge("argus_gpu_usage", "GPU usage percent", registry=self._prometheus_registry),
                "fps": Gauge("argus_fps", "Processing FPS", ["camera"], registry=self._prometheus_registry),
                "detections": Counter("argus_detections_total", "Total detections", ["camera", "object_type"], registry=self._prometheus_registry),
                "events": Counter("argus_events_total", "Total events", ["severity"], registry=self._prometheus_registry),
                "processing_time": Histogram("argus_processing_seconds", "Processing time", registry=self._prometheus_registry),
            }
            logger.info("Prometheus metrics initialized")
        except ImportError:
            logger.debug("prometheus_client not installed. Metrics export via /metrics endpoint disabled.")

    def record(self, name: str, value: float, labels: Optional[Dict] = None) -> None:
        with self._lock:
            if name not in self._metrics:
                self._metrics[name] = []
            self._metrics[name].append(MetricPoint(name=name, value=value, labels=labels or {}))
            if len(self._metrics[name]) > 10000:
                self._metrics[name] = self._metrics[name][-5000:]

        if name in self._gauges:
            try:
                if labels:
                    self._gauges[name].labels(**labels).set(value)
                else:
                    self._gauges[name].set(value)
            except Exception:
                pass

    def get_system_metrics(self) -> Dict[str, float]:
        return {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "cpu_count": psutil.cpu_count(),
            "memory_percent": psutil.virtual_memory().percent,
            "memory_available_gb": psutil.virtual_memory().available / (1024**3),
            "disk_percent": psutil.disk_usage("/").percent,
            "disk_free_gb": psutil.disk_usage("/").free / (1024**3),
            "network_bytes_sent": psutil.net_io_counters().bytes_sent,
            "network_bytes_recv": psutil.net_io_counters().bytes_recv,
            "uptime_seconds": time.time() - psutil.boot_time(),
        }

    def get_gpu_metrics(self) -> Dict[str, Any]:
        try:
            import pynvml
            pynvml.nvmlInit()
            device_count = pynvml.nvmlDeviceGetCount()
            gpus = []
            for i in range(device_count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
                gpus.append({
                    "index": i,
                    "name": pynvml.nvmlDeviceGetName(handle).decode(),
                    "gpu_util": util.gpu,
                    "memory_util": mem.used / mem.total * 100,
                    "memory_used_mb": mem.used / (1024**2),
                    "memory_total_mb": mem.total / (1024**2),
                    "temperature": pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU),
                })
            pynvml.nvmlShutdown()
            return {"gpus": gpus, "count": device_count}
        except ImportError:
            return {"gpus": [], "count": 0, "error": "pynvml not installed"}
        except Exception as e:
            return {"gpus": [], "count": 0, "error": str(e)}

    def get_pipeline_metrics(self) -> Dict[str, Any]:
        with self._lock:
            results = {}
            for name, points in self._metrics.items():
                if points:
                    values = [p.value for p in points]
                    results[name] = {
                        "current": values[-1],
                        "avg": sum(values) / len(values),
                        "min": min(values),
                        "max": max(values),
                        "count": len(values),
                    }
            return results

    def start_collecting(self, interval: float = 5.0) -> None:
        if self._running:
            return
        self._running = True
        self._collector_thread = threading.Thread(
            target=self._collect_loop, args=(interval,), daemon=True, name="metrics-collector"
        )
        self._collector_thread.start()
        logger.info(f"Metrics collection started (interval={interval}s)")

    def stop_collecting(self) -> None:
        self._running = False
        if self._collector_thread:
            self._collector_thread.join(timeout=5)

    def _collect_loop(self, interval: float) -> None:
        while self._running:
            try:
                sys_metrics = self.get_system_metrics()
                for k, v in sys_metrics.items():
                    self.record(f"system_{k}", v)
                gpu_metrics = self.get_gpu_metrics()
                for i, gpu in enumerate(gpu_metrics.get("gpus", [])):
                    self.record(f"gpu_{i}_util", gpu["gpu_util"], {"gpu": str(i)})
                    self.record(f"gpu_{i}_memory", gpu["memory_util"], {"gpu": str(i)})
                for cb in self._callbacks:
                    try:
                        cb()
                    except Exception:
                        pass
            except Exception as e:
                logger.error(f"Metrics collection error: {e}")
            time.sleep(interval)

    def on_collect(self, callback: Callable) -> None:
        self._callbacks.append(callback)

    def get_prometheus_output(self) -> Optional[str]:
        if self._prometheus_registry:
            try:
                from prometheus_client import generate_latest
                return generate_latest(self._prometheus_registry).decode()
            except Exception:
                return None
        return None

    def close(self) -> None:
        self.stop_collecting()
        self._metrics.clear()
        logger.info("MetricsCollector closed")
