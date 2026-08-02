"""Vision module - image processing, satellite imagery analysis, and computer vision pipeline."""

from __future__ import annotations

from typing import Any, Dict, Optional

import numpy as np

from .satellite_processor import SatelliteImageProcessor, SatelliteImage
from .object_detector import ObjectDetector, DetectionResult, DetectionBBox
from .terrain_vision import TerrainVisionAnalyzer, TerrainClassification
from .thermal_processor import ThermalImageProcessor, ThermalSignature


class VisionEngine:
    """Compatibility facade for the historical backend vision API.

    The original backend package expected a single VisionEngine object with
    initialize/close hooks. The modern codebase exposes specialized processors,
    so this wrapper keeps the public surface stable while delegating to the
    available components.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._initialized = False
        self.satellite = SatelliteImageProcessor()
        self.detector = ObjectDetector(
            confidence_threshold=float(self.config.get("confidence_threshold", 0.5))
        )
        self.terrain = TerrainVisionAnalyzer()
        self.thermal = ThermalImageProcessor(
            sensitivity=float(self.config.get("thermal_sensitivity", 0.5))
        )

    def initialize(self) -> None:
        self._initialized = True

    def close(self) -> None:
        self._initialized = False

    def analyze(self, image: np.ndarray) -> Dict[str, Any]:
        """Run the most appropriate available analysis path for an image."""
        if image.ndim == 2:
            thermal = self.thermal.analyze(image)
            terrain = self.terrain.analyze(image)
            return {
                "thermal": thermal,
                "terrain": terrain,
            }

        detections = self.detector.detect(image)
        terrain = self.terrain.analyze(image)
        return {
            "detections": detections,
            "terrain": terrain,
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "type": "VisionEngine",
            "initialized": self._initialized,
            "satellite": self.satellite.get_stats(),
            "detector": self.detector.get_stats(),
            "terrain": self.terrain.get_stats(),
            "thermal": self.thermal.get_stats(),
        }

__all__ = [
    "SatelliteImageProcessor",
    "SatelliteImage",
    "ObjectDetector",
    "DetectionResult",
    "DetectionBBox",
    "TerrainVisionAnalyzer",
    "TerrainClassification",
    "ThermalImageProcessor",
    "ThermalSignature",
    "VisionEngine",
]
