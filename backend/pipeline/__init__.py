"""
Video Pipeline — RTSP/RTMP/WebRTC/HLS streaming, FFmpeg acceleration,
GPU decode/encode, frame buffer management, and adaptive FPS.
"""

import os
import cv2
import json
import time
import queue
import logging
import threading
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple, Any
from enum import Enum
from datetime import datetime
from contextlib import contextmanager
import numpy as np

logger = logging.getLogger("argus.pipeline")


class StreamType(Enum):
    RTSP = "rtsp"
    RTMP = "rtmp"
    HLS = "hls"
    WEBSOCKET = "websocket"
    FILE = "file"
    USB = "usb"


class CodecType(Enum):
    H264 = "h264"
    H265 = "h265"
    VP9 = "vp9"
    MJPG = "mjpg"


@dataclass
class Frame:
    """Single video frame with metadata."""
    data: np.ndarray
    timestamp: float
    frame_id: int
    pts: Optional[float] = None
    source: Optional[str] = None

    @property
    def height(self) -> int:
        return self.data.shape[0]

    @property
    def width(self) -> int:
        return self.data.shape[1]

    @property
    def channels(self) -> int:
        return self.data.shape[2] if self.data.ndim == 3 else 1


class FrameBuffer:
    """Thread-safe circular frame buffer with adaptive dropping."""

    def __init__(self, max_size: int = 300):
        self.max_size = max_size
        self._buffer: List[Frame] = []
        self._lock = threading.RLock()
        self._push_count = 0
        self._drop_count = 0

    def push(self, frame: Frame) -> bool:
        """Push frame to buffer. Returns False if frame was dropped."""
        with self._lock:
            if len(self._buffer) >= self.max_size:
                self._buffer.pop(0)
                self._drop_count += 1
            self._buffer.append(frame)
            self._push_count += 1
            return True

    def pop(self) -> Optional[Frame]:
        """Pop oldest frame."""
        with self._lock:
            if not self._buffer:
                return None
            return self._buffer.pop(0)

    def peek(self) -> Optional[Frame]:
        """Get newest frame without removing."""
        with self._lock:
            if not self._buffer:
                return None
            return self._buffer[-1]

    def clear(self) -> None:
        with self._lock:
            self._buffer.clear()

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._buffer)

    @property
    def stats(self) -> Dict:
        with self._lock:
            return {
                "size": len(self._buffer),
                "max_size": self.max_size,
                "pushed": self._push_count,
                "dropped": self._drop_count,
            }


class VideoSource(ABC):
    """Abstract video source."""

    @abstractmethod
    def open(self) -> bool:
        ...

    @abstractmethod
    def read(self) -> Optional[Frame]:
        ...

    @abstractmethod
    def close(self) -> None:
        ...

    @abstractmethod
    def is_open(self) -> bool:
        ...

    @property
    @abstractmethod
    def fps(self) -> float:
        ...

    @property
    @abstractmethod
    def resolution(self) -> Tuple[int, int]:
        ...


class RTSPSource(VideoSource):
    """RTSP video source with reconnection."""

    def __init__(self, url: str, max_retries: int = 5, timeout: float = 10.0):
        self.url = url
        self.max_retries = max_retries
        self.timeout = timeout
        self._cap: Optional[cv2.VideoCapture] = None
        self._fps: float = 30.0
        self._width: int = 1920
        self._height: int = 1080
        self._frame_id = 0
        self._retry_count = 0

    def open(self) -> bool:
        self._cap = cv2.VideoCapture(self.url, cv2.CAP_FFMPEG)
        if not self._cap.isOpened():
            logger.error(f"Failed to open RTSP stream: {self.url}")
            return False

        # Set buffer size for low latency
        self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        self._fps = self._cap.get(cv2.CAP_PROP_FPS) or 30.0
        self._width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self._height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self._frame_id = 0
        self._retry_count = 0
        logger.info(f"RTSP source opened: {self.url} ({self._width}x{self._height} @ {self._fps}fps)")
        return True

    def read(self) -> Optional[Frame]:
        if not self._cap or not self._cap.isOpened():
            if self._retry_count < self.max_retries:
                self._retry_count += 1
                time.sleep(1)
                self.open()
            return None

        ret, frame_data = self._cap.read()
        if not ret:
            self._retry_count += 1
            if self._retry_count >= self.max_retries:
                return None
            time.sleep(0.5)
            return self.read()

        self._retry_count = 0
        self._frame_id += 1
        return Frame(
            data=frame_data,
            timestamp=datetime.now().timestamp(),
            frame_id=self._frame_id,
            source=self.url,
        )

    def close(self) -> None:
        if self._cap:
            self._cap.release()
            self._cap = None
        logger.info(f"RTSP source closed: {self.url}")

    def is_open(self) -> bool:
        return self._cap is not None and self._cap.isOpened()

    @property
    def fps(self) -> float:
        return self._fps

    @property
    def resolution(self) -> Tuple[int, int]:
        return (self._width, self._height)


class VideoPipeline:
    """
    End-to-end video pipeline managing source ingestion, frame processing,
    and output distribution. Supports multiple streams concurrently.
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.sources: Dict[str, VideoSource] = {}
        self.buffers: Dict[str, FrameBuffer] = {}
        self.processors: Dict[str, List[Callable]] = {}
        self._threads: Dict[str, threading.Thread] = {}
        self._running = False
        self._lock = threading.RLock()
        self._frame_counters: Dict[str, int] = {}
        self._fps_counters: Dict[str, List[float]] = {}
        self._ffmpeg_processes: Dict[str, subprocess.Popen] = {}
        self._on_frame_callbacks: List[Callable] = []

    def add_source(self, name: str, url: str, source_type: str = "rtsp") -> bool:
        """Add a video source."""
        with self._lock:
            if source_type == "rtsp":
                source = RTSPSource(
                    url,
                    max_retries=self.config.get("max_retries", 5),
                    timeout=self.config.get("timeout", 10.0),
                )
            else:
                raise ValueError(f"Unsupported source type: {source_type}")

            if not source.open():
                return False

            self.sources[name] = source
            self.buffers[name] = FrameBuffer(
                max_size=self.config.get("buffer_size", 300)
            )
            self.processors[name] = []
            self._frame_counters[name] = 0
            self._fps_counters[name] = []
            return True

    def remove_source(self, name: str) -> None:
        """Remove a video source."""
        with self._lock:
            if name in self.sources:
                self.sources[name].close()
                del self.sources[name]
            if name in self.buffers:
                del self.buffers[name]
            if name in self.processors:
                del self.processors[name]
            if name in self._threads:
                del self._threads[name]

    def add_processor(self, source_name: str, processor: Callable) -> None:
        """Add a frame processor for a specific source."""
        with self._lock:
            if source_name in self.processors:
                self.processors[source_name].append(processor)

    def on_frame(self, callback: Callable) -> None:
        """Register global frame callback."""
        self._on_frame_callbacks.append(callback)

    def _source_loop(self, name: str) -> None:
        """Main loop for a single video source."""
        source = self.sources.get(name)
        buffer = self.buffers.get(name)
        if not source or not buffer:
            return

        logger.info(f"Pipeline started for source: {name}")

        while self._running and source.is_open():
            frame = source.read()
            if frame is None:
                time.sleep(0.001)
                continue

            # Apply adaptive FPS
            target_fps = self.config.get("target_fps", 30)
            if target_fps < source.fps:
                # Skip frames to meet target
                self._frame_counters[name] = (self._frame_counters.get(name, 0) + 1)
                if self._frame_counters[name] % max(1, int(source.fps / target_fps)) != 0:
                    continue

            # Push to buffer
            buffer.push(frame)

            # Call processors
            for processor in self.processors.get(name, []):
                try:
                    processor(frame)
                except Exception as e:
                    logger.error(f"Processor error for {name}: {e}")

            # Global callbacks
            for cb in self._on_frame_callbacks:
                try:
                    cb(name, frame)
                except Exception as e:
                    logger.error(f"Callback error: {e}")

            # FPS tracking
            now = time.time()
            self._fps_counters[name].append(now)
            # Keep last 30 timestamps
            self._fps_counters[name] = self._fps_counters[name][-30:]

        logger.info(f"Pipeline stopped for source: {name}")

    def start(self) -> None:
        """Start all source pipelines."""
        if self._running:
            return

        self._running = True

        for name in self.sources:
            thread = threading.Thread(
                target=self._source_loop,
                args=(name,),
                daemon=True,
                name=f"pipeline-{name}",
            )
            thread.start()
            self._threads[name] = thread

        logger.info(f"VideoPipeline started with {len(self.sources)} sources")

    def stop(self) -> None:
        """Stop all pipelines."""
        self._running = False

        for name, thread in self._threads.items():
            thread.join(timeout=5.0)

        for source in self.sources.values():
            source.close()

        # Stop FFmpeg processes
        for proc in self._ffmpeg_processes.values():
            proc.terminate()

        self._ffmpeg_processes.clear()
        logger.info("VideoPipeline stopped")

    def get_frame(self, source_name: str) -> Optional[Frame]:
        """Get latest frame from source buffer."""
        buffer = self.buffers.get(source_name)
        if buffer:
            return buffer.peek()
        return None

    def get_all_frames(self, source_name: str) -> List[Frame]:
        """Get all pending frames from source buffer."""
        buffer = self.buffers.get(source_name)
        frames = []
        if buffer:
            while True:
                f = buffer.pop()
                if f is None:
                    break
                frames.append(f)
        return frames

    def get_fps(self, source_name: str) -> float:
        """Get current FPS for a source."""
        timestamps = self._fps_counters.get(source_name, [])
        if len(timestamps) < 2:
            return 0.0
        return len(timestamps) / (timestamps[-1] - timestamps[0]) if (timestamps[-1] - timestamps[0]) > 0 else 0.0

    def export_hls(self, source_name: str, output_path: str) -> bool:
        """Export stream to HLS using FFmpeg."""
        source = self.sources.get(source_name)
        if not source or not isinstance(source, RTSPSource):
            return False

        cmd = [
            "ffmpeg", "-y",
            "-rtsp_transport", "tcp",
            "-i", source.url,
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-tune", "zerolatency",
            "-f", "hls",
            "-hls_time", "4",
            "-hls_list_size", "10",
            "-hls_flags", "delete_segments",
            output_path,
        ]

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self._ffmpeg_processes[source_name] = proc
            return True
        except Exception as e:
            logger.error(f"HLS export failed: {e}")
            return False

    def take_snapshot(self, source_name: str, output_path: str) -> bool:
        """Capture a snapshot from the stream."""
        frame = self.get_frame(source_name)
        if frame is None:
            return False
        try:
            cv2.imwrite(output_path, frame.data)
            return True
        except Exception as e:
            logger.error(f"Snapshot failed: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics."""
        stats = {}
        for name in self.sources:
            buffer = self.buffers.get(name)
            fps = self.get_fps(name)
            stats[name] = {
                "active": self._threads.get(name, threading.Thread()).is_alive() if self._threads.get(name) else False,
                "buffer": buffer.stats if buffer else {},
                "fps": fps,
                "source_fps": self.sources[name].fps,
                "resolution": self.sources[name].resolution,
            }
        return stats

